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
from typing import Dict, Optional

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


class EventSceneContext(BaseModel):
    event_instance_id: str
    event_id: str
    game_date: date
    trainee_day: int
    slot: DailySlotFact
    event: EventSceneEventFact
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
把当前正在发生的一段特殊时刻写成玩家此刻立即阅读的即时场景正文。

1. 视角：第二人称有限视角（“你”）；只写角色能感知的世界。
2. 这是即时生活场景，不是一天总结、日记、报告或系统提示。
3. 必须停在“玩家需要做出决定的那个瞬间”就结束；禁止继续写主角答应/拒绝/
   离开/留下/道歉/反击等任何会对应选择的行为，禁止写选择后的后果。
4. 不得暗示哪个方向是更善良/更聪明/更成熟的“正确答案”；只呈现情境本身。
5. 不输出选择列表，不重新措辞选项，不写“你要怎么做？”——选项由界面展示。
6. 事件可能只是需要回应的一件小事；小事件就写小，不要人为戏剧化。
7. 不要透露任何机制后果（关系会怎样、对方会怎样、数值会怎样）。
8. 收尾自然即可（对方把东西递过来、老师看着你等你的回答、她说完后没有再继续），
   不要用“空气突然安静”“所有视线落在你身上”“现在决定权到了你手里”这类固定悬念模板。
9. 纯正文：无标题、无 Markdown、无列表、无内部术语。
10. 必要对白只用于呈现已经发生的情境，且受人物稳定性格与当前关系距离约束；
    不得通过对白新增秘密、承诺、历史、家庭、公司信息或稳定人格结论；
    不要为了“有人味”强行塞对白。
11. 生理期只有与当前场景真正相关时才自然表现。
12. 不创造不存在的人：Context 里没有的人物（“旁边的练习生”“某位老师”等）
    不得凭空出现。"""


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
