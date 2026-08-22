# -*- coding: utf-8 -*-
"""
Interruptive Event Scene（LLM Layer 4）。

只生成 Choice 之前的 Event Setup Scene：
- 只处理已经存在的 PendingEventState（Event Lifecycle 已完成触发判定）；
- 绑定 event_instance_id，绝不 reroll / 不调用 Event Director；
- 不执行 Choice、不执行 Effects、不修改 GameState；
- 强制经过 Global Writing Constitution + Provider Adapter（generate_player_text）。
"""
from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from core.event_triggers import EventDefinition
from core.llm import BaseProvider
from core.condition_resolution import snapshot_of
from core.menstrual_cycle import derive_menstrual_daily_state
from core.models import (
    EventInteractionMode,
    GameState,
    SlotResolutionResult,
    SlotStatus,
)
from orchestration.daily_context import DailyMenstrualFacts, DailySlotFact, build_slot_fact
from orchestration.npc_writing_context import build_npc_writing_context
from orchestration.writing.prompt_builder import generate_player_text
from orchestration.writing_context_models import (
    NPCWritingContext,
    PlayerTextGenerationStatus,
    band_for,
)


# ---------------------------------------------------------------------------
# Transient DTOs（不持久化；不含隐藏/内部参数）
# ---------------------------------------------------------------------------


class EventSceneEventFact(BaseModel):
    event_id: str
    category: str
    brief: str


class EventSceneChoiceFact(BaseModel):
    choice_id: str
    brief: str


class EventSceneContext(BaseModel):
    event_instance_id: str
    event_id: str
    game_date: date
    trainee_day: int
    slot: DailySlotFact
    event: EventSceneEventFact
    choices: List[EventSceneChoiceFact]
    condition: Dict[str, str] = Field(default_factory=dict)
    menstrual: Optional[DailyMenstrualFacts] = None
    context_npc: Optional[NPCWritingContext] = None
    company: Dict[str, object] = Field(default_factory=dict)


class EventSceneGenerationResult(BaseModel):
    status: PlayerTextGenerationStatus
    text: Optional[str] = None
    provider_name: str
    error_message: Optional[str] = None


_CONDITION_FIELDS = (
    "energy", "voice_condition", "sleep_condition", "mood", "confidence",
    "muscle_fatigue", "injury_risk", "stress",
)


def build_event_scene_context(
    game_state: GameState,
    event_definition: EventDefinition,
    triggering_slot_result: SlotResolutionResult,
) -> EventSceneContext:
    """从已触发的 PendingEvent 构造 Event Scene Context（read-only）。

    验证：
    - pending_event 必须存在；
    - pending 机械元数据与 event_definition 全量一致（category/trigger_mode/tier/
      interaction_mode/available_choice_ids）；
    - interaction_mode 必须 INTERRUPTIVE；
    - pending.triggered_date == 当天日期、trigger_slot_index == 触发 Slot；
    - triggering_slot_result.completed=True，且与 state.day 对应 Slot 的
      kind/course/free_action 一致；
    - triggering_slot_result.condition_result.after == 当前 post-slot/pre-choice
      Condition 快照（INTERRUPTIVE 时 Choice Effect 尚未执行）。
    """
    pending = game_state.pending_event
    if pending is None:
        raise ValueError("game_state 没有 PendingEvent，不能构建 Event Scene。")
    if pending.event_id != event_definition.event_id:
        raise ValueError(
            f"pending.event_id（{pending.event_id}）与 event_definition.event_id（{event_definition.event_id}）不一致。"
        )
    if event_definition.interaction_mode != EventInteractionMode.INTERRUPTIVE:
        raise ValueError("Event Scene 只允许 INTERRUPTIVE Event。")

    definition_mismatches = []
    if pending.category != event_definition.category:
        definition_mismatches.append("category")
    if pending.trigger_mode != event_definition.trigger_mode:
        definition_mismatches.append("trigger_mode")
    if pending.tier != event_definition.tier:
        definition_mismatches.append("tier")
    if pending.interaction_mode != event_definition.interaction_mode:
        definition_mismatches.append("interaction_mode")
    expected_choices = tuple(c.choice_id for c in event_definition.choices)
    if pending.available_choice_ids != expected_choices:
        definition_mismatches.append("available_choice_ids")
    if definition_mismatches:
        raise ValueError(
            f"pending 与 event_definition 不一致（{', '.join(definition_mismatches)}）；"
            "禁止旧 PendingEvent 与已变化 Definition 拼接。"
        )

    game_date = game_state.time.current_date
    if pending.triggered_date != game_date:
        raise ValueError(
            f"pending.triggered_date（{pending.triggered_date}）与当天（{game_date}）不一致。"
        )
    if pending.trigger_slot_index != triggering_slot_result.slot_index:
        raise ValueError(
            f"pending.trigger_slot_index（{pending.trigger_slot_index}）与 triggering_slot_result"
            f"（{triggering_slot_result.slot_index}）不一致。"
        )
    if not triggering_slot_result.completed:
        raise ValueError("triggering_slot_result.completed 必须为 True。")

    state_slot = game_state.day.slots[pending.trigger_slot_index]
    if state_slot.status != SlotStatus.COMPLETED:
        raise ValueError(
            f"game_state.day.slots[{pending.trigger_slot_index}] 必须为 COMPLETED"
            f"（当前 {state_slot.status.value}；stale/corrupt state，不自动修复）。"
        )
    if triggering_slot_result.slot_kind != state_slot.kind:
        raise ValueError("triggering_slot_result 的 slot_kind 与 game_state.day 不一致。")
    if triggering_slot_result.slot_kind.value == "COMPANY" and triggering_slot_result.company_course != state_slot.company_course:
        raise ValueError("triggering_slot_result 的 company_course 与 game_state.day 不一致。")
    if triggering_slot_result.slot_kind.value == "FREE" and triggering_slot_result.free_action != state_slot.free_action:
        raise ValueError("triggering_slot_result 的 free_action 与 game_state.day 不一致。")

    current_condition = snapshot_of(game_state.condition)
    after_snapshot = triggering_slot_result.condition_result.after
    for field in ("energy", "voice_condition", "sleep_condition", "mood", "confidence",
                  "muscle_fatigue", "injury_risk", "stress"):
        if abs(getattr(after_snapshot, field) - getattr(current_condition, field)) > 1e-9:
            raise ValueError(
                f"triggering_slot_result.condition_result.after.{field} 与当前 post-slot Condition 不一致"
                "（传入了 stale SlotResult / State）。"
            )

    # 当前 Condition：post-slot、pre-choice 状态（band）
    after = triggering_slot_result.condition_result.after
    condition = {field: band_for(getattr(after, field)) for field in _CONDITION_FIELDS}

    menstrual = None
    if game_state.menstrual_cycle is not None and game_state.menstrual_cycle.enabled:
        daily = derive_menstrual_daily_state(game_state.menstrual_cycle, game_date, game_state.meta.rng_seed)
        menstrual = DailyMenstrualFacts(
            phase=daily.phase.value,
            is_menstruating=daily.is_menstruating,
            period_day=daily.period_day,
            flow_level=daily.flow_level.value,
            symptom_level=daily.symptom_level.value,
        )

    context_npc = None
    if pending.context_npc_id is not None:
        profile = game_state.npcs.get(pending.context_npc_id)
        relationship = game_state.relationships.get(pending.context_npc_id)
        if profile is None or relationship is None:
            raise ValueError(
                f"pending.context_npc_id={pending.context_npc_id} 的 NPCProfile/RelationshipState 缺失，明确失败。"
            )
        context_npc = build_npc_writing_context(profile, relationship)

    company = game_state.company
    return EventSceneContext(
        event_instance_id=pending.event_instance_id,
        event_id=pending.event_id,
        game_date=game_date,
        trainee_day=game_state.time.trainee_day,
        slot=build_slot_fact(triggering_slot_result),
        event=EventSceneEventFact(
            event_id=event_definition.event_id,
            category=event_definition.category.value,
            brief=event_definition.director_brief,
        ),
        choices=[
            EventSceneChoiceFact(
                choice_id=choice.choice_id,
                brief=choice.director_brief,
            )
            for choice in event_definition.choices
        ],
        condition=condition,
        menstrual=menstrual,
        context_npc=context_npc,
        company={
            "size": company.size.value,
            "training_style": company.training_style.value if company.training_style else None,
            "management_style": company.management_style.value if company.management_style else None,
            "training_intensity": company.training_intensity,
        },
    )


EVENT_SCENE_TASK_INSTRUCTIONS: str = """【Event Scene 任务】
把 FACT DATA 中已经触发的 Event 写成玩家此刻立即阅读的短场景，并严格停在选择前。
这是事实呈现任务，不是剧情扩写任务。

1. 使用第二人称有限视角（“你”），只写角色当下能感知的内容。event.brief 是已经发生的
   factual setup；不得增加新的评价、训练结果、背景、安排、邀请或后续事件。
2. choices 列出全部正式分叉。每个 choices[*].brief 都是不可改写的行为语义：场景必须让
   每个正式选择仍然真实可行；不得合并、删减、增加选择，不得把一个动作偷换成另一个动作。
3. 例如正式分叉是“再完整做一遍 / 写下纠正要点”，场景必须同时保留“继续完整练习”和
   “停止完整练习、整理要点”两种可能；绝不能改成“最后一遍 / 算了”。
4. 不必让 NPC 念出菜单，也不输出选项列表或 choice_id。自然形成现实分叉后就停住；
   不写“你要怎么做”，不暗示哪项更善良、成熟、努力或正确。
5. 最后一个时刻必须仍在 decision boundary：禁止替玩家答应、拒绝、留下、离开、道歉、
   反击或采取任何对应 Choice 的动作；禁止写 Choice effects、关系变化和任何后果。
6. 对白只可承载 event.brief、正式分叉或无后续义务的短寒暄。FACT DATA 没有老师/NPC 评价，
   对白与旁白都不得创造评价；不得借 Character Guidance 推断对方特别关注玩家。
7. Context 没有的人物不得成为场景参与者。普通背景人声可以存在，但不能替其创造身份、
   行为、对白或与玩家的互动。
8. 小事写小，事实少就写短。收尾可以是对方等一句回应、物件仍放在面前、剩余时间摆在那里；
   不用“空气突然安静”“所有目光聚过来”“决定权到了你手里”等悬念模板。
9. 生理期仅在与此刻确实相关时生活化表现。纯正文，无标题、Markdown、列表或内部术语。"""


def generate_event_scene(
    context: EventSceneContext,
    provider_name: str,
    provider: Optional[BaseProvider] = None,
) -> EventSceneGenerationResult:
    """生成 Event Setup Scene（一次调用，无 retry / fallback / 润色）。"""
    try:
        text = generate_player_text(
            provider_name=provider_name,
            task_name="event_scene",
            task_instructions=EVENT_SCENE_TASK_INSTRUCTIONS,
            fact_context=context.model_dump(mode="json"),
            provider=provider,
            json_mode=False,
        )
    except Exception as exc:
        return EventSceneGenerationResult(
            status=PlayerTextGenerationStatus.PROVIDER_ERROR,
            provider_name=provider_name,
            error_message=f"{type(exc).__name__}: {exc}",
        )

    if not isinstance(text, str) or not text.strip():
        return EventSceneGenerationResult(
            status=PlayerTextGenerationStatus.INVALID_OUTPUT,
            provider_name=provider_name,
            error_message="模型返回空内容。",
        )
    return EventSceneGenerationResult(
        status=PlayerTextGenerationStatus.SUCCESS,
        text=text,
        provider_name=provider_name,
    )
