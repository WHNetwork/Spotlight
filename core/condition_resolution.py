from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from core.models import (
    CompanyCourse,
    ConditionResolutionResult,
    ConditionSignal,
    ConditionSignalResult,
    ConditionSnapshot,
    ConditionState,
    DayState,
    ExplorationDomain,
    FreeActionKind,
    PersonalActionType,
    SkillId,
    SlotKind,
)


# ---------------------------------------------------------------------------
# 纯数值公式
# ---------------------------------------------------------------------------


def _readiness_value(condition: ConditionState, components: Tuple[str, ...]) -> float:
    values: List[float] = []
    for item in components:
        if item.startswith("-"):
            values.append(100.0 - float(getattr(condition, item[1:])))
        else:
            values.append(float(getattr(condition, item)))
    return sum(values) / len(values)


_READINESS_SPEC: Dict[SkillId, Tuple[str, ...]] = {
    SkillId.DANCE: ("energy", "sleep_condition", "-muscle_fatigue", "-stress"),
    SkillId.VOCAL: ("energy", "sleep_condition", "voice_condition", "-stress"),
    SkillId.RAP: ("energy", "voice_condition", "-stress"),
    SkillId.STAGE: ("energy", "-muscle_fatigue", "mood", "confidence", "-stress"),
    SkillId.CAMERA: ("energy", "mood", "confidence", "-stress"),
    SkillId.LANGUAGE: ("energy", "sleep_condition", "-stress"),
    SkillId.ACTING: ("energy", "mood", "confidence", "-stress"),
    SkillId.CREATION: ("energy", "sleep_condition", "mood", "-stress"),
}


def skill_readiness(condition: ConditionState, skill_id: SkillId) -> float:
    """训练开始前该 Skill 的身体心理准备度（0–100）。

    相关 Condition 的简单平均，不做假精确加权。
    """
    spec = _READINESS_SPEC[skill_id]
    return max(0.0, min(100.0, _readiness_value(condition, spec)))


def condition_learning_multiplier(readiness: float) -> float:
    """准备度 → 学习效率倍率：0.75 + 0.0035 * readiness（0→0.75 … 100→1.10）。

    状态再差也不会让训练完全失效（>= 0.75），状态极好只提供克制优势（<= 1.10）。
    """
    r = max(0.0, min(100.0, float(readiness)))
    return 0.75 + 0.0035 * r


def company_training_load_multiplier(training_intensity: int) -> float:
    """公司训练强度 → 公司课程身体负荷倍率：0.70 + 0.006 * intensity。

    只影响公司课程的 body load（energy / muscle_fatigue / voice wear 等），
    禁止进入 Skill XP。
    """
    t = max(0, min(100, int(training_intensity)))
    return 0.70 + 0.006 * t


# ---------------------------------------------------------------------------
# 基础 Condition Impact（第一版正式基础值）
# ---------------------------------------------------------------------------


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


_SKILL_LOAD: Dict[SkillId, Dict[str, float]] = {
    SkillId.DANCE: {"energy": -12.0, "muscle_fatigue": 12.0, "injury_risk": 4.0},
    SkillId.VOCAL: {"energy": -7.0, "voice_condition": -10.0},
    SkillId.RAP: {"energy": -7.0, "voice_condition": -7.0, "muscle_fatigue": 1.0},
    SkillId.STAGE: {"energy": -10.0, "muscle_fatigue": 8.0, "injury_risk": 3.0},
    SkillId.CAMERA: {"energy": -4.0},
    SkillId.LANGUAGE: {"energy": -4.0},
    SkillId.ACTING: {"energy": -6.0},
    SkillId.CREATION: {"energy": -4.0},
}

# FITNESS：energy / muscle_fatigue 属训练负荷乘 M_intensity；injury_risk -4 为固定预防收益。
_FITNESS_LOAD = {"energy": -9.0, "muscle_fatigue": 6.0, "injury_risk": -4.0}

_REST_DELTAS = {
    "energy": 30.0,
    "voice_condition": 8.0,
    "sleep_condition": 6.0,
    "muscle_fatigue": -10.0,
    "injury_risk": -3.0,
    "stress": -4.0,
}

_RECOVER_DELTAS = {
    "energy": 18.0,
    "voice_condition": 5.0,
    "sleep_condition": 2.0,
    "muscle_fatigue": -6.0,
    "injury_risk": -2.0,
    "stress": -5.0,
}


def skill_training_condition_deltas(skill_id: SkillId, load_multiplier: float) -> Dict[str, float]:
    """技能训练基础负荷（负荷项 × load_multiplier）。"""
    base = _SKILL_LOAD[skill_id]
    return {key: value * load_multiplier for key, value in base.items()}


def fitness_condition_deltas(load_multiplier: float) -> Dict[str, float]:
    """FITNESS 公司课程：energy / muscle_fatigue × intensity，injury_risk 固定 -4。"""
    return {
        "energy": _FITNESS_LOAD["energy"] * load_multiplier,
        "muscle_fatigue": _FITNESS_LOAD["muscle_fatigue"] * load_multiplier,
        "injury_risk": _FITNESS_LOAD["injury_risk"],
    }


def apply_condition_deltas(condition: ConditionState, deltas: Dict[str, float]) -> None:
    """把即时变化应用到 ConditionState 并统一 clamp 到 0–100。"""
    for key, delta in deltas.items():
        setattr(condition, key, _clamp(getattr(condition, key) + delta))


def snapshot_of(condition: ConditionState) -> ConditionSnapshot:
    return ConditionSnapshot(
        energy=condition.energy,
        voice_condition=condition.voice_condition,
        sleep_condition=condition.sleep_condition,
        mood=condition.mood,
        confidence=condition.confidence,
        muscle_fatigue=condition.muscle_fatigue,
        injury_risk=condition.injury_risk,
        stress=condition.stress,
    )


# ---------------------------------------------------------------------------
# Event ConditionSignal（Step 15：只作用于心理 Condition，narrow domain）
# ---------------------------------------------------------------------------


def resolve_condition_signal(
    condition_state: ConditionState,
    signal: ConditionSignal,
) -> ConditionSignalResult:
    """结算一个心理 Condition Signal（事件 Effects 专用）。

    - 不接 GameState；只修改 mood / confidence / stress；
    - 使用 before snapshot，一次写回；
    - 一个 Signal 只表达一个领域事实（不交叉修改）。
    """
    before = snapshot_of(condition_state)
    mood = condition_state.mood
    confidence = condition_state.confidence
    stress = condition_state.stress

    if signal == ConditionSignal.MOOD_LIFT:
        mood = _clamp(mood + 10.0 * (1.0 - mood / 100.0))
    elif signal == ConditionSignal.MOOD_HIT:
        mood = _clamp(mood * 0.90)
    elif signal == ConditionSignal.CONFIDENCE_GAIN:
        confidence = _clamp(confidence + 10.0 * (1.0 - confidence / 100.0))
    elif signal == ConditionSignal.CONFIDENCE_HIT:
        confidence = _clamp(confidence * 0.90)
    elif signal == ConditionSignal.STRESS_INCREASE:
        stress = _clamp(stress + 12.0 * (1.0 - stress / 100.0))
    elif signal == ConditionSignal.STRESS_RELIEF:
        stress = _clamp(stress * 0.85)

    condition_state.mood = mood
    condition_state.confidence = confidence
    condition_state.stress = stress

    return ConditionSignalResult(
        signal=signal,
        condition_before=before,
        condition_after=snapshot_of(condition_state),
    )


# ---------------------------------------------------------------------------
# Slot 绑定入口：只解析 DayState.current_slot（status == PENDING）
# ---------------------------------------------------------------------------


def _current_pending_slot(day_state: DayState):
    if not day_state.slots:
        raise ValueError("DayState 尚未初始化（slots 为空），无法结算 Condition。")
    if day_state.is_day_complete:
        raise ValueError("当天 8 个 Slot 已全部完成，无法结算 Condition。")
    current_index = day_state.current_slot
    if current_index is None:
        raise ValueError("当前没有可结算的 Slot。")
    slot = next((s for s in day_state.slots if s.index == current_index), None)
    if slot is None:
        raise ValueError(f"找不到当前 Slot（index={current_index}）。")
    return slot


def resolve_current_slot_condition(
    day_state: DayState,
    condition: ConditionState,
    training_intensity: Optional[int] = None,
) -> ConditionResolutionResult:
    """结算当前 PENDING Slot 的即时 Condition 变化。

    规则：
    - REST / SCHOOL：直接按 SlotKind 结算；
    - COMPANY：必须已有 company_course（None 时明确失败）；技能课程按基础负荷
      × M_intensity，FITNESS 按 FITNESS 方案（injury_risk 固定 -4）；
      COMPANY 必须提供 training_intensity；
    - FREE：必须已有 free_action（None 时明确失败）；TRAIN 按基础负荷 × 1.0，
      RECOVER / EXPLORE / PERSONAL(STUDY) 按各自基础值，
      SOCIAL 与 PERSONAL(FAMILY / LEISURE / OUTING) 第一版 Condition delta = 0。

    只修改 ConditionState；不调用 mark_completed()，不产生 Injury / ActiveCondition。

    架构边界：本函数是 Condition 领域组件，由 slot_resolution.resolve_current_slot()
    统一编排；正常游戏流程不应直接调用它来执行一个完整 Slot。
    """
    slot = _current_pending_slot(day_state)

    load_multiplier = 1.0
    deltas: Dict[str, float] = {}

    if slot.kind == SlotKind.REST:
        deltas = dict(_REST_DELTAS)
    elif slot.kind == SlotKind.SCHOOL:
        deltas = {"energy": -4.0}
    elif slot.kind == SlotKind.COMPANY:
        if slot.company_course is None:
            raise ValueError("当前 COMPANY Slot 没有 company_course，无法结算 Condition。")
        if training_intensity is None:
            raise ValueError("结算 COMPANY Slot Condition 必须提供 training_intensity。")
        load_multiplier = company_training_load_multiplier(training_intensity)
        skill_id = _skill_for_company_course(slot.company_course)
        if skill_id is None:
            deltas = fitness_condition_deltas(load_multiplier)
        else:
            deltas = skill_training_condition_deltas(skill_id, load_multiplier)
    elif slot.kind == SlotKind.FREE:
        if slot.free_action is None:
            raise ValueError("当前 FREE Slot 没有 free_action，无法结算 Condition（玩家必须先选择行动）。")
        action = slot.free_action
        if action.kind == FreeActionKind.TRAIN:
            if action.skill is None:
                raise ValueError("TRAIN 行动缺少 skill，无法结算 Condition。")
            deltas = skill_training_condition_deltas(action.skill, 1.0)
        elif action.kind == FreeActionKind.RECOVER:
            deltas = dict(_RECOVER_DELTAS)
        elif action.kind == FreeActionKind.EXPLORE:
            if action.exploration_domain is None:
                raise ValueError("EXPLORE 行动缺少 exploration_domain，无法结算 Condition。")
            deltas = {
                ExplorationDomain.ACTING: {"energy": -5.0},
                ExplorationDomain.CREATION: {"energy": -4.0},
            }[action.exploration_domain]
        elif action.kind == FreeActionKind.PERSONAL:
            if action.personal_type == PersonalActionType.STUDY:
                deltas = {"energy": -4.0}
            else:
                deltas = {}
        else:
            deltas = {}

    before = snapshot_of(condition)
    apply_condition_deltas(condition, deltas)
    after = snapshot_of(condition)

    return ConditionResolutionResult(
        slot_index=slot.index,
        before=before,
        after=after,
        training_load_multiplier=load_multiplier,
    )


def _skill_for_company_course(course: Optional[CompanyCourse]) -> Optional[SkillId]:
    from core.skill_training import skill_for_company_course

    return skill_for_company_course(course)
