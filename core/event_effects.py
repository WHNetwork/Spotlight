from __future__ import annotations

from datetime import date
from typing import List, Sequence, Tuple

from core.condition_resolution import resolve_condition_signal
from core.models import (
    AppliedConditionEffect,
    AppliedRelationshipEffect,
    ConditionEventAction,
    ConditionSignal,
    EventAppliedEffect,
    EventEffectKind,
    GameState,
    RelationshipActionTarget,
    RelationshipEventAction,
)
from core.relationships import resolve_relationship_signal


# ---------------------------------------------------------------------------
# Event Effects / Domain Actions (Step 15)
#
# 唯一 Event → Domain 的 orchestration bridge：
#   EventDefinition.effects / EventChoiceDefinition.effects
#     ↓
#   apply_event_actions（deep-copy working state）
#     ↓
#   Relationship / Condition Domain Resolver
#     ↓
#   AppliedRelationshipEffect / AppliedConditionEffect
#
# 本模块不包含 Relationship / Condition 数学，不包含 trigger 概率，
# 不调用 LLM / Narrative / Storage；不创建 PendingEvent。
# ---------------------------------------------------------------------------


class EventEffectError(ValueError):
    """Event Effect 执行失败（非法定义 / context NPC 缺失 / 冲突 / resolver 失败）。"""


# Condition 同一维度互斥组：同一 effect list 内每组最多出现一个。
_CONDITION_DIMENSION_GROUPS = (
    (ConditionSignal.MOOD_LIFT, ConditionSignal.MOOD_HIT),
    (ConditionSignal.CONFIDENCE_GAIN, ConditionSignal.CONFIDENCE_HIT),
    (ConditionSignal.STRESS_INCREASE, ConditionSignal.STRESS_RELIEF),
)


def validate_event_actions(actions: Sequence) -> None:
    """定义期 / 运行期防御验证：
    - 禁止 exact duplicate action；
    - 禁止 Condition 同一维度正负同时出现；
    - typed model 自身验证（discriminator / target-npc_id 组合）已在构造时完成。
    """
    seen: list = []
    for action in actions:
        if action in seen:
            raise EventEffectError(f"exact duplicate action 不允许出现两次：{action}")
        seen.append(action)

    cond_signals = [a.signal for a in actions if isinstance(a, ConditionEventAction)]
    for group in _CONDITION_DIMENSION_GROUPS:
        present = [s for s in group if s in cond_signals]
        if len(present) > 1:
            raise EventEffectError(f"Condition 同一维度冲突（同一事件最多操作一次）：{present}")


def _resolve_npc_id(
    action: RelationshipEventAction,
    game_state: GameState,
    context_npc_id: str | None,
) -> str:
    if action.target == RelationshipActionTarget.CONTEXT_NPC:
        if not context_npc_id:
            raise EventEffectError(
                f"action 要求 CONTEXT_NPC（signal={action.signal.value}），但当前没有 context NPC，明确失败。"
            )
        return context_npc_id
    if not action.npc_id:
        raise EventEffectError("EXPLICIT_NPC action 缺少 npc_id（模型级验证应已拦截）。")
    return action.npc_id


def apply_event_actions(
    game_state: GameState,
    actions: Sequence,
    event_date: date,
    context_npc_id: str | None,
) -> Tuple[GameState, List[EventAppliedEffect]]:
    """按定义顺序执行 Event Domain Actions（deep-copy，绝不半修改输入 State）。

    全部成功 → 返回新 State + applied effects；
    任一失败 → 抛 EventEffectError，原输入 GameState 保持完全不变。
    """
    validate_event_actions(actions)
    working_state = game_state.model_copy(deep=True)
    applied: List[EventAppliedEffect] = []
    resolved_targets: set = set()

    for action in actions:
        if isinstance(action, ConditionEventAction):
            result = resolve_condition_signal(working_state.condition, action.signal)
            applied.append(AppliedConditionEffect(kind=EventEffectKind.CONDITION, result=result))
        elif isinstance(action, RelationshipEventAction):
            npc_id = _resolve_npc_id(action, working_state, context_npc_id)
            key = (npc_id, action.signal)
            if key in resolved_targets:
                raise EventEffectError(
                    f"resolved duplicate：同一 NPC（{npc_id}）同一 Signal（{action.signal.value}）出现两次。"
                )
            resolved_targets.add(key)
            result = resolve_relationship_signal(
                working_state.npcs,
                working_state.relationships,
                npc_id,
                event_date,
                action.signal,
            )
            applied.append(AppliedRelationshipEffect(kind=EventEffectKind.RELATIONSHIP, result=result))
        else:
            raise EventEffectError(f"不支持的 Event Domain Action：{type(action).__name__}")

    return working_state, applied
