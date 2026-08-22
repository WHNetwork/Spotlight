from __future__ import annotations

from typing import Optional, Tuple

from core.condition_resolution import resolve_current_slot_condition
from core.models import (
    CompanyCourse,
    ConditionResolutionResult,
    FreeActionKind,
    GameState,
    RelationshipInteractionResult,
    SkillTrainingResult,
    SlotKind,
    SlotResolutionResult,
)
from core.relationships import resolve_social_interaction
from core.skill_training import (
    resolve_company_skill_training,
    resolve_self_training,
)


class SlotResolutionError(ValueError):
    """统一 Slot 结算失败。"""


def resolve_current_slot(game_state: GameState) -> Tuple[GameState, SlotResolutionResult]:
    """统一 Slot Resolver 唯一正式入口：只执行当前一个 PENDING Slot。

    流程：
    1. working_state = game_state 深拷贝（原 state 无论成功失败都不变）；
    2. 检查 day 已初始化（slots 非空）、当天尚未完成、当前 Slot 存在；
    3. 检查 Slot ready：
       - SCHOOL / REST：天然 ready；
       - COMPANY：必须已有 company_course；
       - FREE：必须已有 free_action；
    4. Skill Resolution（如该 Slot 存在 Skill Training）——使用训练开始前 Condition；
    5. Condition Resolution；
    6. Relationship Resolution（仅 FREE → SOCIAL：familiarity 增长，
       其他 Slot 为 None）；
    7. day.mark_completed(slot.index)；
    8. 构造 SlotResolutionResult（completed=True）；
    9. 返回 (working_state, result)。

    职责边界：
    - 只编排已存在的领域 Resolver（skill_training / condition_resolution），
      不重新实现任何数值公式；
    - 不调用 LLM；不推进日期；不自动执行后续 Slot；不做 Day Settlement；
    - 不访问数据库 / SaveStorage；
    - 失败时直接抛错（底层领域异常原样向上传播或抛 SlotResolutionError），
      原 state 因未被修改而自然安全；
    - SlotResolutionResult 中的 free_action 是执行时的独立深拷贝快照
      （slot.free_action.model_copy(deep=True)），与 working_state 不再共享引用；
    - 若 game_state.pending_event 非空则明确拒绝：存在尚未处理的特殊事件时
      不能进入下一 Slot。
    """
    if game_state.pending_event is not None:
        raise SlotResolutionError("存在尚未处理的特殊事件，不能进入下一 Slot。")

    working_state = game_state.model_copy(deep=True)

    day = working_state.day
    if not day.slots:
        raise SlotResolutionError("DayState 尚未初始化（slots 为空），无法结算当前 Slot。")
    if day.is_day_complete:
        raise SlotResolutionError("当天 8 个 Slot 已全部完成，无法结算。")
    current_index = day.current_slot
    if current_index is None:
        raise SlotResolutionError("当前没有可结算的 Slot。")
    slot = next((s for s in day.slots if s.index == current_index), None)
    if slot is None:
        raise SlotResolutionError(f"找不到当前 Slot（index={current_index}）。")

    _check_slot_ready(slot)

    skill_result: Optional[SkillTrainingResult] = None
    condition_result: ConditionResolutionResult
    relationship_result: Optional[RelationshipInteractionResult] = None

    if slot.kind == SlotKind.FREE:
        if slot.free_action is not None and slot.free_action.kind == FreeActionKind.TRAIN:
            skill_result = resolve_self_training(
                day,
                working_state.skills,
                working_state.condition,
                working_state.time.current_date,
            )
        condition_result = resolve_current_slot_condition(day, working_state.condition)
        if slot.free_action is not None and slot.free_action.kind == FreeActionKind.SOCIAL:
            if slot.free_action.target_npc_id is None:
                raise SlotResolutionError("SOCIAL 行动缺少 target_npc_id，无法结算关系互动。")
            relationship_result = resolve_social_interaction(
                working_state.npcs,
                working_state.relationships,
                slot.free_action.target_npc_id,
                working_state.time.current_date,
            )
    elif slot.kind == SlotKind.COMPANY:
        if slot.company_course != CompanyCourse.FITNESS:
            skill_result = resolve_company_skill_training(
                day,
                working_state.skills,
                working_state.company.resource_level,
                working_state.condition,
                working_state.time.current_date,
            )
        condition_result = resolve_current_slot_condition(
            day,
            working_state.condition,
            training_intensity=working_state.company.training_intensity,
        )
    else:
        condition_result = resolve_current_slot_condition(day, working_state.condition)

    day.mark_completed(slot.index)

    result = SlotResolutionResult(
        slot_index=slot.index,
        slot_kind=slot.kind,
        company_course=slot.company_course,
        free_action=slot.free_action.model_copy(deep=True) if slot.free_action is not None else None,
        skill_result=skill_result,
        condition_result=condition_result,
        relationship_result=relationship_result,
        completed=True,
    )
    return working_state, result


def _check_slot_ready(slot) -> None:
    if slot.kind == SlotKind.COMPANY and slot.company_course is None:
        raise SlotResolutionError("COMPANY Slot 尚未安排课程，不能结算。")
    if slot.kind == SlotKind.FREE and slot.free_action is None:
        raise SlotResolutionError("玩家尚未为当前 FREE Slot 选择 Action，不能结算。")
