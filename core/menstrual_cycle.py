from __future__ import annotations

import hashlib
import random
from datetime import date, timedelta
from typing import Dict, List, Optional

from core.condition_resolution import snapshot_of
from core.models import (
    ConditionState,
    GameState,
    MenstrualCycleState,
    MenstrualDailyEffectResult,
    MenstrualDailyState,
    MenstrualFlowLevel,
    MenstrualPhase,
    MenstrualSymptomLevel,
    MenstrualSymptomTendency,
)


# ---------------------------------------------------------------------------
# Menstrual Cycle / Daily Physiology Core (Step 14)
#
# 独立 Domain：使用 TimeState.current_date 作为唯一时钟；
# 日期是唯一权威时间（禁止第二套 cycle_day 计数）。
#
# 结构：
#   initialize_menstrual_cycle（新世界 bootstrap，需接 GameState）
#   advance_menstrual_cycle_to_date（narrow：只接 MenstrualCycleState/date/seed）
#   derive_menstrual_daily_state（纯函数，无副作用）
#   apply_daily_menstrual_physiology（每天一次，只改 Condition 四个字段）
#
# 不实现：疾病/诊断/妊娠/避孕/压力致紊乱/周期事件/UI/LLM。
# Condition 影响只通过 energy/muscle_fatigue/sleep_condition/stress；
# Skill/Evaluation/Relationship/Company 完全不被直接修改。
# ---------------------------------------------------------------------------


class MenstrualCycleError(ValueError):
    """生理周期 Domain 失败（重复初始化 / 非法日期 / 重复应用 / 非法状态）。"""


_BOOTSTRAP_NS = "menstrual-cycle-bootstrap:{rng_seed}"
_CYCLE_NS = "menstrual-cycle:{rng_seed}:{cycle_index}"
_DAILY_NS = "menstrual-daily:{rng_seed}:{cycle_index}:{cycle_day}"

_TENDENCY_MODIFIER = {
    MenstrualSymptomTendency.LOW: -1,
    MenstrualSymptomTendency.MEDIUM: 0,
    MenstrualSymptomTendency.HIGH: 1,
}

_SYMPTOM_EFFECTS: Dict[MenstrualSymptomLevel, Dict[str, float]] = {
    MenstrualSymptomLevel.NONE: {},
    MenstrualSymptomLevel.MILD: {"energy": -3.0, "muscle_fatigue": 2.0, "sleep_condition": -1.0, "stress": 1.0},
    MenstrualSymptomLevel.MODERATE: {"energy": -7.0, "muscle_fatigue": 5.0, "sleep_condition": -3.0, "stress": 2.0},
    MenstrualSymptomLevel.STRONG: {"energy": -12.0, "muscle_fatigue": 8.0, "sleep_condition": -5.0, "stress": 4.0},
}

_SYMPTOM_BASE = {1: 2, 2: 2, 3: 1}  # period_day >= 4 → 1；最后一天 → 0
_SYMPTOM_LEVELS = [
    MenstrualSymptomLevel.NONE, MenstrualSymptomLevel.MILD,
    MenstrualSymptomLevel.MODERATE, MenstrualSymptomLevel.STRONG,
]

_FLOW_POOLS: Dict[int, List[MenstrualFlowLevel]] = {
    1: [MenstrualFlowLevel.MODERATE, MenstrualFlowLevel.MODERATE, MenstrualFlowLevel.HEAVY],
    2: [MenstrualFlowLevel.MODERATE, MenstrualFlowLevel.HEAVY, MenstrualFlowLevel.HEAVY],
    3: [MenstrualFlowLevel.LIGHT, MenstrualFlowLevel.MODERATE, MenstrualFlowLevel.MODERATE],
    4: [MenstrualFlowLevel.LIGHT, MenstrualFlowLevel.LIGHT, MenstrualFlowLevel.MODERATE],
}


def _stable_rng(namespace: str) -> random.Random:
    digest = hashlib.sha256(namespace.encode("utf-8")).hexdigest()
    return random.Random(int(digest[:8], 16))


def _clamp(v: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(v)))


def _cycle_length(rng: random.Random, baseline: int) -> int:
    return max(21, min(35, baseline + rng.randint(-2, 2)))


def _period_length(rng: random.Random, baseline: int) -> int:
    return max(3, min(7, baseline + rng.randint(-1, 1)))


# ---------------------------------------------------------------------------
# 初始化（一次性 world bootstrap）
# ---------------------------------------------------------------------------


def initialize_menstrual_cycle(game_state: GameState) -> None:
    """新存档初始化：随机 baseline + 当前周期位置。

    - 前置：meta.rng_seed 已存在；game_state.menstrual_cycle 必须为 None
      （重复初始化抛 MenstrualCycleError）；
    - 以 first playable date = state.time.current_date 反推 cycle_start_date
      （cycle_start_date 允许早于 created_date，只是周期 anchor）；
    - 使用独立 bootstrap / cycle RNG namespace，不用全局 random。
    """
    if game_state.menstrual_cycle is not None:
        raise MenstrualCycleError("menstrual_cycle 已初始化，禁止重复初始化。")

    rng_seed = game_state.meta.rng_seed
    bootstrap = _stable_rng(_BOOTSTRAP_NS.format(rng_seed=rng_seed))
    baseline_cycle = bootstrap.randint(26, 32)
    baseline_period = bootstrap.randint(4, 6)
    tendency = list(MenstrualSymptomTendency)[bootstrap.randrange(3)]

    cycle_rng = _stable_rng(_CYCLE_NS.format(rng_seed=rng_seed, cycle_index=0))
    current_cycle_length = _cycle_length(cycle_rng, baseline_cycle)
    current_period_length = _period_length(cycle_rng, baseline_period)
    initial_cycle_day = cycle_rng.randint(1, current_cycle_length)

    first_playable = game_state.time.current_date
    cycle_start_date = first_playable - timedelta(days=initial_cycle_day - 1)

    game_state.menstrual_cycle = MenstrualCycleState(
        enabled=True,
        baseline_cycle_length=baseline_cycle,
        baseline_period_length=baseline_period,
        symptom_tendency=tendency,
        cycle_start_date=cycle_start_date,
        cycle_index=0,
        current_cycle_length=current_cycle_length,
        current_period_length=current_period_length,
        last_physiology_applied_date=None,
    )


# ---------------------------------------------------------------------------
# 周期推进（narrow domain）
# ---------------------------------------------------------------------------


def advance_menstrual_cycle_to_date(
    menstrual_state: MenstrualCycleState,
    target_date: date,
    rng_seed: int,
) -> None:
    """把 persistent cycle 推进到 target_date 所在周期。

    - 只接 MenstrualCycleState / target_date / rng_seed（不接 GameState）；
    - 结果只取决于原 anchor / target_date / rng_seed / cycle_index，
      与调用次数无关；
    - 一次跨多周期用 while 推进；
    - 结果只修改 cycle_start_date / cycle_index / current_cycle_length /
      current_period_length（last_physiology_applied_date 保留）。
    """
    if menstrual_state is None:
        raise MenstrualCycleError("menstrual_cycle 尚未初始化。")
    if target_date < menstrual_state.cycle_start_date:
        raise MenstrualCycleError(
            f"target_date（{target_date}）早于当前周期 anchor（{menstrual_state.cycle_start_date}）。"
        )
    while True:
        cycle_last_day = menstrual_state.cycle_start_date + timedelta(
            days=menstrual_state.current_cycle_length - 1
        )
        if target_date <= cycle_last_day:
            return
        menstrual_state.cycle_start_date = menstrual_state.cycle_start_date + timedelta(
            days=menstrual_state.current_cycle_length
        )
        menstrual_state.cycle_index += 1
        cycle_rng = _stable_rng(_CYCLE_NS.format(rng_seed=rng_seed, cycle_index=menstrual_state.cycle_index))
        menstrual_state.current_cycle_length = _cycle_length(cycle_rng, menstrual_state.baseline_cycle_length)
        menstrual_state.current_period_length = _period_length(cycle_rng, menstrual_state.baseline_period_length)


# ---------------------------------------------------------------------------
# Daily state 推导（纯函数，无副作用）
# ---------------------------------------------------------------------------


def derive_menstrual_daily_state(
    menstrual_state: MenstrualCycleState,
    target_date: date,
    rng_seed: int,
) -> MenstrualDailyState:
    """推导 target_date 的周期 daily state（不 mutation 任何状态）。

    前置：menstrual_state 必须已经指向 target_date 所在周期（先 advance）。
    相同输入调用任意次数结果一致。
    """
    if menstrual_state is None:
        raise MenstrualCycleError("menstrual_cycle 尚未初始化。")
    cycle_last_day = menstrual_state.cycle_start_date + timedelta(
        days=menstrual_state.current_cycle_length - 1
    )
    if not (menstrual_state.cycle_start_date <= target_date <= cycle_last_day):
        raise MenstrualCycleError(
            "target_date 不在当前周期内：请先 advance_menstrual_cycle_to_date（derive 不做跨周期推进）。"
        )

    cycle_day = (target_date - menstrual_state.cycle_start_date).days + 1
    cycle_length = menstrual_state.current_cycle_length
    period_length = menstrual_state.current_period_length
    is_menstruating = cycle_day <= period_length
    period_day = cycle_day if is_menstruating else None

    ovulation_day = max(period_length + 2, cycle_length - 14)
    if is_menstruating:
        phase = MenstrualPhase.MENSTRUAL
    elif cycle_day in (ovulation_day - 1, ovulation_day, ovulation_day + 1):
        phase = MenstrualPhase.OVULATORY
    elif cycle_day < ovulation_day - 1:
        phase = MenstrualPhase.FOLLICULAR
    else:
        phase = MenstrualPhase.LUTEAL

    days_until_next_period = cycle_length - cycle_day + 1
    is_premenstrual_window = (not is_menstruating) and days_until_next_period <= 3

    daily_rng = _stable_rng(_DAILY_NS.format(
        rng_seed=rng_seed, cycle_index=menstrual_state.cycle_index, cycle_day=cycle_day,
    ))

    flow_level = MenstrualFlowLevel.NONE
    symptom_level = MenstrualSymptomLevel.NONE
    if is_menstruating:
        is_last_day = cycle_day == period_length
        if is_last_day:
            flow_level = MenstrualFlowLevel.LIGHT
        else:
            pool = _FLOW_POOLS.get(cycle_day, _FLOW_POOLS[4])
            flow_level = pool[daily_rng.randrange(len(pool))]
        base = 0 if is_last_day else _SYMPTOM_BASE.get(cycle_day, 1)
        score = _clamp(base + _TENDENCY_MODIFIER[menstrual_state.symptom_tendency]
                       + daily_rng.choice([-1, 0, 0, 0, 1]), 0.0, 3.0)
        symptom_level = _SYMPTOM_LEVELS[int(score)]
    elif is_premenstrual_window:
        base = 1
        score = _clamp(base + _TENDENCY_MODIFIER[menstrual_state.symptom_tendency]
                       + daily_rng.choice([-1, 0, 0, 0, 1]), 0.0, 2.0)
        symptom_level = _SYMPTOM_LEVELS[int(score)]

    return MenstrualDailyState(
        game_date=target_date,
        cycle_index=menstrual_state.cycle_index,
        cycle_day=cycle_day,
        cycle_length=cycle_length,
        phase=phase,
        is_menstruating=is_menstruating,
        period_day=period_day,
        period_length=period_length,
        flow_level=flow_level,
        symptom_level=symptom_level,
        days_until_next_period=days_until_next_period,
        is_premenstrual_window=is_premenstrual_window,
    )


# ---------------------------------------------------------------------------
# 每日一次性 physiology application
# ---------------------------------------------------------------------------


def apply_daily_menstrual_physiology(
    menstrual_state: MenstrualCycleState,
    condition_state: ConditionState,
    target_date: date,
    rng_seed: int,
) -> MenstrualDailyEffectResult:
    """把 target_date 的生理影响一次性施加到 Condition（每天最多一次）。

    - last_physiology_applied_date == target_date → 抛错（禁止同日重复）；
    - last_physiology_applied_date > target_date → 抛错（日期倒退）；
    - 只修改 condition 的 energy / muscle_fatigue / sleep_condition / stress；
    - enabled=False → 返回 daily state 但 Condition 保持不变（不更新 last_applied）。
    """
    if menstrual_state is None:
        raise MenstrualCycleError("menstrual_cycle 尚未初始化。")

    if menstrual_state.last_physiology_applied_date is not None:
        if menstrual_state.last_physiology_applied_date == target_date:
            raise MenstrualCycleError(f"该日期（{target_date}）已经应用过每日生理影响，禁止同一天重复。")
        if menstrual_state.last_physiology_applied_date > target_date:
            raise MenstrualCycleError(f"日期倒退（{menstrual_state.last_physiology_applied_date} → {target_date}），拒绝应用。")

    daily = derive_menstrual_daily_state(menstrual_state, target_date, rng_seed)
    before = snapshot_of(condition_state)

    if menstrual_state.enabled:
        deltas = _SYMPTOM_EFFECTS.get(daily.symptom_level, {})
        for key, delta in deltas.items():
            setattr(condition_state, key, _clamp(getattr(condition_state, key) + delta))
        menstrual_state.last_physiology_applied_date = target_date

    return MenstrualDailyEffectResult(
        game_date=target_date,
        daily_state=daily,
        condition_before=before,
        condition_after=snapshot_of(condition_state),
    )
