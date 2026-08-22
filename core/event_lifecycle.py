from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from core.event_effects import apply_event_actions
from core.event_models import EventSoftJudgment, EventTriggerDecision
from core.event_triggers import (
    EventDefinition,
    EventEvaluation,
    EventHistorySnapshot,
    SlotEventContext,
    build_slot_event_context,
    derive_event_instance_id,
    finalize_event_selection,
    prepare_event_evaluation,
)
from core.models import (
    EventInteractionMode,
    EventResult,
    EventTriggerMode,
    GameState,
    PendingEventState,
    SlotResolutionResult,
)


class EventLifecycleError(ValueError):
    """特殊事件生命周期失败。"""


@dataclass(frozen=True)
class PostSlotEventPreparation:
    """post-slot 事件阶段准备结果（transient，不持久化）。"""

    context: SlotEventContext
    evaluation: EventEvaluation
    requires_soft_judgment: bool


@dataclass(frozen=True)
class PostSlotEventOutcome:
    """post-slot 事件阶段结果（transient，不持久化）。

    无事件：三者全 None；
    NON_INTERRUPTIVE：decision + event_result，pending_event = None；
    INTERRUPTIVE：decision + pending_event，event_result = None。
    """

    decision: Optional[EventTriggerDecision] = None
    event_result: Optional[EventResult] = None
    pending_event: Optional[PendingEventState] = None


def prepare_post_slot_event_phase(
    post_slot_state: GameState,
    slot_result: SlotResolutionResult,
    definitions: Sequence[EventDefinition],
    history: EventHistorySnapshot,
) -> PostSlotEventPreparation:
    """post-slot 事件阶段准备（只读，不修改 GameState）。

    - 确认没有未处理的 PendingEvent；
    - Slot identity 完全来自 slot_result；
    - immediate definitions 过滤：LLM_ASSISTED + NON_INTERRUPTIVE 不参与
      post-slot 即时判断（留给未来 Day-End Event Director 批量判断）；
    - requires_soft_judgment = 存在 eligible 的 LLM_ASSISTED（INTERRUPTIVE）候选。
    """
    if post_slot_state.pending_event is not None:
        raise EventLifecycleError("存在尚未处理的 PendingEvent，不能开始新的 post-slot 事件阶段。")

    context = build_slot_event_context(post_slot_state, slot_result)
    immediate = [
        d
        for d in definitions
        if not (
            d.trigger_mode == EventTriggerMode.LLM_ASSISTED
            and d.interaction_mode == EventInteractionMode.NON_INTERRUPTIVE
        )
    ]
    evaluation = prepare_event_evaluation(immediate, context, history)
    return PostSlotEventPreparation(
        context=context,
        evaluation=evaluation,
        requires_soft_judgment=bool(evaluation.llm_assisted),
    )


def finalize_post_slot_event_phase(
    post_slot_state: GameState,
    preparation: PostSlotEventPreparation,
    definitions: Sequence[EventDefinition],
    soft_judgment: Optional[EventSoftJudgment] = None,
) -> Tuple[GameState, PostSlotEventOutcome]:
    """post-slot 事件阶段收尾：返回 deep-copy 后的新 State + Outcome。

    - requires_soft_judgment=True 且 soft_judgment 缺失时明确失败
      （不允许默认 relevance=0 / 跳过 / 低优先级 Python 事件抢跑）；
    - 无事件：返回与 post_slot_state 等价的 deep copy，Outcome 全 None；
    - NON_INTERRUPTIVE：直接构造 EventResult（choice_id=None），
      pending_event 保持 None；
    - INTERRUPTIVE：构造 PendingEventState 写入 working_state.pending_event，
      不生成 EventResult（事件尚未解决）。
    """
    if preparation.requires_soft_judgment and soft_judgment is None:
        raise EventLifecycleError("需要 EventSoftJudgment 但未提供（事件阶段尚未完整结束，不能持久化）。")

    working_state = post_slot_state.model_copy(deep=True)
    decision = finalize_event_selection(
        preparation.evaluation,
        preparation.context,
        working_state.meta.rng_seed,
        soft_judgment,
    )
    if decision is None:
        return working_state, PostSlotEventOutcome()

    definition = _find_definition(definitions, decision.event_id)
    instance_id = derive_event_instance_id(
        working_state.meta.rng_seed,
        decision.game_date,
        decision.slot_index,
        decision.event_id,
    )

    if decision.interaction_mode == EventInteractionMode.NON_INTERRUPTIVE:
        context_npc_id = preparation.context.context_npc_id
        working_state, applied_effects = apply_event_actions(
            working_state, definition.effects, decision.game_date, context_npc_id
        )
        event_result = _event_result_from_decision(
            decision, instance_id, choice_id=None,
            context_npc_id=context_npc_id, applied_effects=applied_effects,
        )
        return working_state, PostSlotEventOutcome(decision=decision, event_result=event_result, pending_event=None)

    pending = PendingEventState(
        event_instance_id=instance_id,
        event_id=decision.event_id,
        triggered_date=decision.game_date,
        trigger_slot_index=decision.slot_index,
        category=decision.category,
        trigger_mode=decision.trigger_mode,
        tier=decision.tier,
        interaction_mode=decision.interaction_mode,
        priority=decision.priority,
        base_probability=decision.base_probability,
        soft_relevance=decision.soft_relevance,
        effective_probability=decision.effective_probability,
        available_choice_ids=tuple(c.choice_id for c in definition.choices),
        context_npc_id=preparation.context.context_npc_id,
    )
    working_state.pending_event = pending
    return working_state, PostSlotEventOutcome(decision=decision, event_result=None, pending_event=pending)


def resolve_pending_event_choice(
    game_state: GameState,
    definitions: Sequence[EventDefinition],
    choice_id: str,
) -> Tuple[GameState, EventResult]:
    """玩家对 PendingEvent 做出 Choice。

    - deep-copy 输入，原 GameState 不被修改；
    - 无 pending_event 时明确失败；
    - 从正式 definitions 按 event_id 查找定义（找不到失败）；
    - 定义必须仍为 INTERRUPTIVE；
    - choice_id 必须同时存在于 pending.available_choice_ids 与 definition.choices；
    - 执行 selected Choice.effects（apply_event_actions 在带 pending 的 working copy 上
      执行，全部成功后才清除 pending_event；失败时 pending 仍保留）；
    - 成功后生成 EventResult（记录 choice_id / context_npc_id / applied_effects）。
    """
    if game_state.pending_event is None:
        raise EventLifecycleError("没有待处理事件，不能解析 Choice。")
    working_state = game_state.model_copy(deep=True)
    pending = working_state.pending_event

    definition = _find_definition(definitions, pending.event_id)
    if definition.interaction_mode != EventInteractionMode.INTERRUPTIVE:
        raise EventLifecycleError(f"事件 {pending.event_id} 不是 INTERRUPTIVE，不能走 Choice 流程。")
    if choice_id not in pending.available_choice_ids:
        raise EventLifecycleError(f"Choice '{choice_id}' 不在 PendingEvent 的可用选项中。")
    choice_def = next((c for c in definition.choices if c.choice_id == choice_id), None)
    if choice_def is None:
        raise EventLifecycleError(f"Choice '{choice_id}' 不在事件定义 {pending.event_id} 的 choices 中。")

    working_state, applied_effects = apply_event_actions(
        working_state, choice_def.effects, pending.triggered_date, pending.context_npc_id
    )
    working_state.pending_event = None
    event_result = _event_result_from_pending(pending, choice_id, applied_effects)
    return working_state, event_result


def _find_definition(definitions: Sequence[EventDefinition], event_id: str) -> EventDefinition:
    for definition in definitions:
        if definition.event_id == event_id:
            return definition
    raise EventLifecycleError(
        f"找不到事件定义：{event_id}（PendingEvent 只保存 event_id，定义必须来自正式 registry）。"
    )


def _event_result_from_decision(
    decision: EventTriggerDecision,
    instance_id: str,
    choice_id: Optional[str],
    context_npc_id: Optional[str] = None,
    applied_effects: Optional[List] = None,
) -> EventResult:
    return EventResult(
        event_instance_id=instance_id,
        event_id=decision.event_id,
        game_date=decision.game_date,
        trigger_slot_index=decision.slot_index,
        category=decision.category,
        trigger_mode=decision.trigger_mode,
        tier=decision.tier,
        interaction_mode=decision.interaction_mode,
        priority=decision.priority,
        base_probability=decision.base_probability,
        soft_relevance=decision.soft_relevance,
        effective_probability=decision.effective_probability,
        choice_id=choice_id,
        context_npc_id=context_npc_id,
        applied_effects=list(applied_effects or []),
    )


def _event_result_from_pending(
    pending: PendingEventState,
    choice_id: str,
    applied_effects: Optional[List] = None,
) -> EventResult:
    return EventResult(
        event_instance_id=pending.event_instance_id,
        event_id=pending.event_id,
        game_date=pending.triggered_date,
        trigger_slot_index=pending.trigger_slot_index,
        category=pending.category,
        trigger_mode=pending.trigger_mode,
        tier=pending.tier,
        interaction_mode=pending.interaction_mode,
        priority=pending.priority,
        base_probability=pending.base_probability,
        soft_relevance=pending.soft_relevance,
        effective_probability=pending.effective_probability,
        choice_id=choice_id,
        context_npc_id=pending.context_npc_id,
        applied_effects=list(applied_effects or []),
    )
