from __future__ import annotations

from datetime import date
from typing import Optional

from core.condition_resolution import condition_learning_multiplier, skill_readiness
from core.models import (
    CompanyCourse,
    ConditionState,
    DayState,
    FreeActionKind,
    SkillId,
    SkillState,
    SkillTrainingResult,
    SkillsState,
    SlotKind,
    SlotStatus,
    TrainingSource,
)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

BASE_TRAINING_XP = 6.0
FORM_GAIN_BASE = 20.0

# 同一天同一 Skill 的重复训练倍率：第 1 次 … 第 6 次。
DAILY_REPETITION_MULTIPLIERS = (
    1.00,
    0.85,
    0.65,
    0.45,
    0.30,
    0.20,
)


# ---------------------------------------------------------------------------
# 纯数值公式
# ---------------------------------------------------------------------------


def xp_needed_for_next_level(skill_value: int) -> Optional[int]:
    """Skill 从 S 提升到 S+1 所需 XP。

    XP_need(S) = round(14 + 0.008 * S^2)
    value 0–99 返回所需 XP；value >= 100 已封顶，返回 None。
    """
    if skill_value >= 100:
        return None
    return round(14 + 0.008 * skill_value * skill_value)


def talent_learning_multiplier(talent: int) -> float:
    """隐藏天赋 → 学习效率倍率：0.75 + 0.005 * talent（talent 0→0.75 … 100→1.25）。

    只影响 XP 获取；不直接改 value / form，不决定技能上限。
    """
    t = max(0, min(100, int(talent)))
    return 0.75 + 0.005 * t


def company_learning_multiplier(resource_level: int) -> float:
    """公司资源 → 公司课程学习倍率：0.90 + 0.002 * resource（20→0.94 … 100→1.10）。

    只作用于 COMPANY 技能课程；输入限制 0–100。
    """
    r = max(0, min(100, int(resource_level)))
    return 0.90 + 0.002 * r


def repetition_multiplier(repetition_index: int) -> float:
    """当日同 Skill 第 N 次训练的递减倍率。

    第 1 次 1.00 … 第 6 次 0.20；第 7 次及以后统一保持 0.20（不归零、不崩溃）。
    """
    if repetition_index <= 0:
        repetition_index = 1
    if repetition_index >= len(DAILY_REPETITION_MULTIPLIERS):
        return DAILY_REPETITION_MULTIPLIERS[-1]
    return DAILY_REPETITION_MULTIPLIERS[repetition_index - 1]


# ---------------------------------------------------------------------------
# 公司课程 → Skill 映射
# ---------------------------------------------------------------------------


_COURSE_TO_SKILL = {
    CompanyCourse.DANCE: SkillId.DANCE,
    CompanyCourse.VOCAL: SkillId.VOCAL,
    CompanyCourse.RAP: SkillId.RAP,
    CompanyCourse.STAGE: SkillId.STAGE,
    CompanyCourse.CAMERA: SkillId.CAMERA,
    CompanyCourse.LANGUAGE: SkillId.LANGUAGE,
}


def skill_for_company_course(course: Optional[CompanyCourse]) -> Optional[SkillId]:
    """公司课程对应的正式 Skill；FITNESS（或 None）→ None，不产生 Skill XP。"""
    if course is None:
        return None
    return _COURSE_TO_SKILL.get(course)


# ---------------------------------------------------------------------------
# 当日重复训练计数（从 DayState 已完成的 Slot 历史推导，不新增持久字段）
# ---------------------------------------------------------------------------


def completed_training_count(day_state: DayState, skill_id: SkillId) -> int:
    """今天在指定 Skill 上已经完成过的训练次数（只统计 status == COMPLETED 的 Slot）。

    COMPANY：slot.company_course 映射到该 Skill 的已完成课程；
    FREE：free_action.kind == TRAIN 且 skill 相同的已完成 Slot。
    当前正在结算的 PENDING Slot 不计入，因此本次训练是 count + 1 次。
    """
    count = 0
    for slot in day_state.slots:
        if slot.status != SlotStatus.COMPLETED:
            continue
        if slot.kind == SlotKind.COMPANY:
            if skill_for_company_course(slot.company_course) == skill_id:
                count += 1
        elif slot.kind == SlotKind.FREE and slot.free_action is not None:
            action = slot.free_action
            if action.kind == FreeActionKind.TRAIN and action.skill == skill_id:
                count += 1
    return count


# ---------------------------------------------------------------------------
# 纯训练应用（不接触 DayState / Slot）
# ---------------------------------------------------------------------------


def apply_skill_training(
    skill_state: SkillState,
    skill_id: SkillId,
    source: TrainingSource,
    repetition_index: int,
    resource_level: Optional[int],
    condition_state: ConditionState,
    current_date: date,
) -> SkillTrainingResult:
    """应用一次技能训练：更新 XP / value / form / last_practiced_date。

    公式：
      自主训练 effective_xp = BASE_TRAINING_XP × talent × repetition × condition
      公司课程 effective_xp = BASE_TRAINING_XP × talent × repetition × resource × condition
      form_gain = FORM_GAIN_BASE × (1 - form / 100)，clamp 到 0–100

    因果顺序：condition_readiness / condition_multiplier 由训练开始前的
    ConditionState 计算（训练结束后的 Condition 变化由 condition_resolution 单独处理，
    不影响本节课 XP）。

    value 达到 100 后：不再升级，剩余 XP 归零；但 form 与
    last_practiced_date 仍正常更新（满级仍需保持状态）。

    本函数不修改 ConditionState，不调用 mark_completed。
    """
    if not skill_state.unlocked:
        raise ValueError(f"技能 {skill_id.value} 未解锁，不能训练。")
    if skill_state.value is None:
        raise ValueError(f"技能 {skill_id.value} 的 value 未初始化，不能训练。")
    if skill_state.form is None:
        raise ValueError(f"技能 {skill_id.value} 的 form 未初始化，不能训练。")

    talent_multiplier = talent_learning_multiplier(skill_state.talent)
    repetition_mult = repetition_multiplier(repetition_index)

    company_quality_multiplier = 1.0
    if source == TrainingSource.COMPANY:
        if resource_level is None:
            raise ValueError("COMPANY 训练必须提供 resource_level。")
        company_quality_multiplier = company_learning_multiplier(resource_level)

    readiness = skill_readiness(condition_state, skill_id)
    condition_multiplier = condition_learning_multiplier(readiness)

    effective_xp = (
        BASE_TRAINING_XP
        * talent_multiplier
        * repetition_mult
        * company_quality_multiplier
        * condition_multiplier
    )

    value_before = skill_state.value
    xp_before = skill_state.xp
    form_before = skill_state.form

    value_after = value_before
    xp_after = xp_before + effective_xp
    levels_gained = 0
    while value_after < 100:
        need = xp_needed_for_next_level(value_after)
        if need is None or xp_after < need:
            break
        xp_after -= need
        value_after += 1
        levels_gained += 1
    if value_after >= 100:
        xp_after = 0.0

    form_gain = FORM_GAIN_BASE * (1.0 - form_before / 100.0)
    form_after = min(100.0, form_before + form_gain)

    skill_state.value = value_after
    skill_state.xp = xp_after
    skill_state.form = form_after
    skill_state.last_practiced_date = current_date

    return SkillTrainingResult(
        skill=skill_id,
        source=source,
        base_xp=BASE_TRAINING_XP,
        talent_multiplier=talent_multiplier,
        repetition_index=repetition_index,
        repetition_multiplier=repetition_mult,
        company_quality_multiplier=company_quality_multiplier,
        condition_readiness=readiness,
        condition_multiplier=condition_multiplier,
        effective_xp=effective_xp,
        value_before=value_before,
        value_after=value_after,
        xp_before=xp_before,
        xp_after=xp_after,
        form_before=form_before,
        form_after=form_after,
        levels_gained=levels_gained,
    )


# ---------------------------------------------------------------------------
# Slot 绑定入口：只解析 DayState.current_slot
# ---------------------------------------------------------------------------


def _current_pending_slot(day_state: DayState):
    if not day_state.slots:
        raise ValueError("DayState 尚未初始化（slots 为空），无法结算训练。")
    if day_state.is_day_complete:
        raise ValueError("当天 8 个 Slot 已全部完成，无法结算训练。")
    current_index = day_state.current_slot
    if current_index is None:
        raise ValueError("当前没有可结算的 Slot。")
    slot = next((s for s in day_state.slots if s.index == current_index), None)
    if slot is None:
        raise ValueError(f"找不到当前 Slot（index={current_index}）。")
    return slot


def resolve_self_training(
    day_state: DayState,
    skills_state: SkillsState,
    condition_state: ConditionState,
    current_date: date,
) -> Optional[SkillTrainingResult]:
    """结算当前 PENDING FREE Slot 中的 TRAIN 行动。

    仅当当前 Slot 为 FREE、free_action.kind == TRAIN、status == PENDING 时生效；
    其他情况返回 None（不适用）。COMPANY 与 FREE TRAIN 共用同一 Skill
    当日重复计数。不调用 mark_completed()。

    架构边界：本函数是 Skill 领域组件，由 slot_resolution.resolve_current_slot()
    统一编排；正常游戏流程不应直接调用它来执行一个完整 Slot。
    """
    slot = _current_pending_slot(day_state)
    if slot.kind != SlotKind.FREE or slot.free_action is None:
        return None
    action = slot.free_action
    if action.kind != FreeActionKind.TRAIN or action.skill is None:
        return None
    skill_id = action.skill
    skill_state = getattr(skills_state, skill_id.value)
    repetition_index = completed_training_count(day_state, skill_id) + 1
    return apply_skill_training(
        skill_state=skill_state,
        skill_id=skill_id,
        source=TrainingSource.SELF_TRAINING,
        repetition_index=repetition_index,
        resource_level=None,
        condition_state=condition_state,
        current_date=current_date,
    )


def resolve_company_skill_training(
    day_state: DayState,
    skills_state: SkillsState,
    resource_level: int,
    condition_state: ConditionState,
    current_date: date,
) -> Optional[SkillTrainingResult]:
    """结算当前 PENDING COMPANY Slot 的技能课程。

    仅当当前 Slot 为 COMPANY、company_course 非空时生效；
    company_course == FITNESS（或无对应 Skill）时返回 None，本步骤不处理
    也不完成该 Slot。不调用 mark_completed()。

    架构边界：本函数是 Skill 领域组件，由 slot_resolution.resolve_current_slot()
    统一编排；正常游戏流程不应直接调用它来执行一个完整 Slot。
    """
    slot = _current_pending_slot(day_state)
    if slot.kind != SlotKind.COMPANY or slot.company_course is None:
        return None
    skill_id = skill_for_company_course(slot.company_course)
    if skill_id is None:
        return None
    skill_state = getattr(skills_state, skill_id.value)
    repetition_index = completed_training_count(day_state, skill_id) + 1
    return apply_skill_training(
        skill_state=skill_state,
        skill_id=skill_id,
        source=TrainingSource.COMPANY,
        repetition_index=repetition_index,
        resource_level=resource_level,
        condition_state=condition_state,
        current_date=current_date,
    )
