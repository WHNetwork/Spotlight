from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional, Tuple

from pydantic import BaseModel, model_validator

from core.company_curriculum import build_day_with_courses
from core.condition_resolution import snapshot_of
from core.day_schedule import build_base_day
from core.evaluation import (
    MonthlyEvaluationResult,
    is_monthly_evaluation_eligible,
    resolve_monthly_evaluation,
)
from core.menstrual_cycle import (
    advance_menstrual_cycle_to_date,
    apply_daily_menstrual_physiology,
)
from core.models import (
    GameState,
    MenstrualDailyEffectResult,
    OvernightConditionResult,
    SkillFormSettlementResult,
    SkillId,
)


# ---------------------------------------------------------------------------
# Day Settlement (Step 11)
#
# 唯一执行时机：当前自然日 8 Slot 全部 COMPLETED、post-slot Event Phase 完成、
# 无 PendingEvent。
# 正式顺序：
#   optional Monthly Evaluation（月末 + Step 10 eligibility，必须在 Overnight 之前）
#   → Overnight Condition
#   → Skill Form Settlement（practiced_today 对比 settled_date）
#   → current_date + 1
#   → 生成新一天 DayState（复用 day_schedule / company_curriculum）
#   → DaySettlementResult
#
# 本模块不访问 SQLite、不调用 LLM、不触发 Event、不生成 Narrative；
# 不修改 Relationship / NPC / Skill value/xp/talent / training_level；
# 不做 Day-End Event Director（未来插入点见 docstring：Day complete + No Pending
# → optional Monthly Evaluation → 未来 Day-End Event Director → Day Settlement）。
# ---------------------------------------------------------------------------


class DaySettlementError(ValueError):
    """Day Settlement 失败。"""


# --- Overnight Condition 常量 ---

SLEEP_TARGET_BASE = 90.0
SLEEP_STRESS_PENALTY = 0.25
SLEEP_FATIGUE_PENALTY = 0.15
SLEEP_TARGET_MIN = 35.0
SLEEP_TARGET_MAX = 95.0
SLEEP_MEMORY_WEIGHT = 0.50
SLEEP_TARGET_WEIGHT = 0.50

# --- Skill Form 跨日常量 ---

FORM_DAILY_RETENTION = 0.96

# Form Settlement 固定顺序（不依赖 dict 插入顺序）。
_FORM_SETTLEMENT_ORDER: Tuple[SkillId, ...] = (
    SkillId.DANCE,
    SkillId.VOCAL,
    SkillId.RAP,
    SkillId.STAGE,
    SkillId.CAMERA,
    SkillId.LANGUAGE,
    SkillId.ACTING,
    SkillId.CREATION,
)


class DaySettlementResult(BaseModel):
    """一天机械结算的过程事实（transient，第一版不单独持久化）。"""

    settled_date: date
    next_date: date
    monthly_evaluation: Optional[MonthlyEvaluationResult] = None
    condition_result: OvernightConditionResult
    form_results: List[SkillFormSettlementResult]
    next_day_menstrual_effect: Optional[MenstrualDailyEffectResult] = None

    @model_validator(mode="after")
    def _validate_next_date(self) -> "DaySettlementResult":
        if self.next_date != self.settled_date + timedelta(days=1):
            raise ValueError("next_date 必须等于 settled_date + 1 natural day。")
        return self


def is_day_settlement_eligible(game_state: GameState) -> bool:
    """Day Settlement 资格：当天 8 Slot 全部完成 且 无 PendingEvent。

    不要求自然月末（普通日也必须结算）；不要求月评资格
    （月末 trainee_day < 14 仍须进入下一天，只是跳过正式月评）。
    """
    return game_state.day.is_day_complete and game_state.pending_event is None


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def resolve_day_settlement(game_state: GameState) -> Tuple[GameState, DaySettlementResult]:
    """执行一次 Day Settlement（只推进一个自然日）。

    - deep-copy 输入，原 GameState 完全不被修改；
    - 不访问 SQLite、不调用 LLM、不触发 Event；
    - 不 eligible 时抛 DaySettlementError（不返回 None、不自动处理 PendingEvent）；
    - 月末且满足月评资格时，在 Overnight 之前执行 Monthly Evaluation，
      其 latest_evaluation_* 更新保留到 next-day state。
    """
    if not is_day_settlement_eligible(game_state):
        raise DaySettlementError(
            "当前不满足 Day Settlement 条件（需要当天 8 Slot 全部完成且无 PendingEvent）。"
        )

    working_state = game_state.model_copy(deep=True)
    settled_date = working_state.time.current_date

    # ① optional Monthly Evaluation（Overnight 之前）
    monthly_evaluation: Optional[MonthlyEvaluationResult] = None
    if working_state.time.is_month_end and is_monthly_evaluation_eligible(working_state):
        working_state, monthly_evaluation = resolve_monthly_evaluation(working_state)

    # ② Overnight Condition（所有输入取自 condition_before 快照，避免顺序污染）
    condition = working_state.condition
    before = snapshot_of(condition)

    sleep_target = (
        SLEEP_TARGET_BASE
        - SLEEP_STRESS_PENALTY * before.stress
        - SLEEP_FATIGUE_PENALTY * before.muscle_fatigue
    )
    sleep_target = max(SLEEP_TARGET_MIN, min(SLEEP_TARGET_MAX, sleep_target))
    sleep_after = (
        SLEEP_MEMORY_WEIGHT * before.sleep_condition
        + SLEEP_TARGET_WEIGHT * sleep_target
    )
    sleep_after = _clamp(sleep_after)

    fatigue_recovery_fraction = 0.35 + 0.003 * sleep_after
    fatigue_after = _clamp(before.muscle_fatigue * (1.0 - fatigue_recovery_fraction))

    voice_recovery_fraction = 0.20 + 0.003 * sleep_after
    voice_after = _clamp(before.voice_condition + (100.0 - before.voice_condition) * voice_recovery_fraction)

    stress_retention = 0.92 - 0.0015 * sleep_after
    stress_after = _clamp(before.stress * stress_retention)

    energy_after = _clamp(45.0 + 0.55 * sleep_after - 0.10 * fatigue_after)

    risk_retention = 0.75 + 0.0025 * before.muscle_fatigue
    risk_after = _clamp(before.injury_risk * risk_retention)

    condition.energy = energy_after
    condition.sleep_condition = sleep_after
    condition.muscle_fatigue = fatigue_after
    condition.voice_condition = voice_after
    condition.stress = stress_after
    condition.injury_risk = risk_after
    # mood / confidence / active_conditions 保持不变

    condition_result = OvernightConditionResult(
        before=before,
        after=snapshot_of(condition),
        sleep_target=sleep_target,
    )

    # ③ Skill Form Settlement
    form_results: List[SkillFormSettlementResult] = []
    for skill_id in _FORM_SETTLEMENT_ORDER:
        skill = getattr(working_state.skills, skill_id.value)
        if not skill.unlocked:
            if skill.form is not None:
                raise DaySettlementError(f"locked skill {skill_id.value} 的 form 必须为 None。")
            form_results.append(
                SkillFormSettlementResult(
                    skill=skill_id,
                    unlocked=False,
                    practiced_today=False,
                    form_before=None,
                    form_after=None,
                )
            )
            continue
        if skill.form is None:
            raise DaySettlementError(f"unlocked skill {skill_id.value} 的 form 未初始化。")
        form_before = skill.form
        practiced_today = skill.last_practiced_date == settled_date
        if practiced_today:
            form_after = form_before
        else:
            form_after = _clamp(form_before * FORM_DAILY_RETENTION)
        skill.form = form_after
        form_results.append(
            SkillFormSettlementResult(
                skill=skill_id,
                unlocked=True,
                practiced_today=practiced_today,
                form_before=form_before,
                form_after=form_after,
            )
        )

    # ④ Calendar Advance（+1 natural day）
    next_date = settled_date + timedelta(days=1)

    # ⑤ Next-day Menstrual Daily Physiology（Overnight 之后、日期推进之前：
    #    先睡眠恢复，再叠加第二天的当天基础负担）
    next_day_menstrual_effect = None
    if working_state.menstrual_cycle is not None:
        advance_menstrual_cycle_to_date(
            working_state.menstrual_cycle, next_date, working_state.meta.rng_seed
        )
        next_day_menstrual_effect = apply_daily_menstrual_physiology(
            working_state.menstrual_cycle,
            working_state.condition,
            next_date,
            working_state.meta.rng_seed,
        )

    working_state.time.current_date = next_date

    # ⑥ 新一天 DayState（复用现有 schedule + curriculum 规则）
    education_status = working_state.player.education_status
    new_day = build_base_day(working_state.time, education_status)
    new_day = build_day_with_courses(
        new_day,
        working_state.company,
        education_status,
        working_state.meta.rng_seed,
        working_state.time.current_date,
    )
    working_state.day = new_day

    result = DaySettlementResult(
        settled_date=settled_date,
        next_date=next_date,
        monthly_evaluation=monthly_evaluation,
        condition_result=condition_result,
        form_results=form_results,
        next_day_menstrual_effect=next_day_menstrual_effect,
    )
    return working_state, result
