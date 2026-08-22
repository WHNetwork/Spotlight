# -*- coding: utf-8 -*-
"""
Daily Writing Context（LLM Layer 2B）。

Daily Narrative 与 Diary 共用的唯一 canonical day fact package：
    completed-day Python facts → DailyWritingContext → 两类文本视图。

本模块：
- 不查 SQLite；
- 不修改任何 State（pure/read-only）；
- 显式 allow-list，绝不 dump GameState；
- 只暴露角色可感知的世界事实（无 talent / rng / 概率 / 公式）。
"""
from __future__ import annotations

from datetime import date
from typing import Dict, List, Mapping, Optional, Sequence

from pydantic import BaseModel, Field

from core.day_settlement import DaySettlementResult
from core.condition_resolution import snapshot_of
from core.event_definition import EventDefinition
from core.evaluation import MonthlyEvaluationResult
from core.menstrual_cycle import derive_menstrual_daily_state
from core.models import (
    AppliedConditionEffect,
    AppliedRelationshipEffect,
    ConditionSnapshot,
    EventInteractionMode,
    EventResult,
    GameState,
    SlotKind,
    SlotResolutionResult,
)
from orchestration.npc_writing_context import build_npc_writing_context
from orchestration.writing_context_models import (
    NPCWritingContext,
    band_for,
    exploration_stage_for,
)


# ---------------------------------------------------------------------------
# Transient DTOs（不持久化；不含隐藏/内部参数）
# ---------------------------------------------------------------------------


class DailySlotFact(BaseModel):
    slot_index: int
    slot_type: str
    course: Optional[str] = None
    free_action_type: Optional[str] = None
    free_action_detail: Optional[str] = None
    training_summary: Optional[dict] = None
    social_summary: Optional[dict] = None
    exploration_summary: Optional[dict] = None


class DailyEventFact(BaseModel):
    event_id: str
    event_brief: str
    category: str
    tier: str
    interaction_mode: str
    context_npc_id: Optional[str] = None
    choice_id: Optional[str] = None
    choice_brief: Optional[str] = None
    effect_summary: List[str] = Field(default_factory=list)


class DailyConditionFacts(BaseModel):
    day_start: Optional[Dict[str, str]] = None
    day_end: Dict[str, str]


class DailyMenstrualFacts(BaseModel):
    phase: str
    is_menstruating: bool
    period_day: Optional[int] = None
    flow_level: str
    symptom_level: str


class DailyEvaluationFacts(BaseModel):
    evaluation_date: date
    overall_score: float
    trainee_day: int


class DailyCompanyFacts(BaseModel):
    size: str
    training_style: Optional[str] = None
    management_style: Optional[str] = None
    training_intensity: int
    resource_level: int


class DailyWritingContext(BaseModel):
    """一天 canonical facts 的 allow-list（Daily Narrative 与 Diary 共用）。"""

    game_date: date
    trainee_day: int
    weekday: int
    education_status: str
    company: DailyCompanyFacts
    slots: List[DailySlotFact] = Field(default_factory=list)
    events: List[DailyEventFact] = Field(default_factory=list)
    condition: DailyConditionFacts
    menstrual: Optional[DailyMenstrualFacts] = None
    relationships_touched: List[NPCWritingContext] = Field(default_factory=list)
    monthly_evaluation: Optional[DailyEvaluationFacts] = None


# ---------------------------------------------------------------------------
# Context Builder（pure / read-only；不查 DB；不修改 State）
# ---------------------------------------------------------------------------

_CONDITION_FIELDS = (
    "energy", "voice_condition", "sleep_condition", "mood", "confidence",
    "muscle_fatigue", "injury_risk", "stress",
)


def _condition_band_map(snapshot: ConditionSnapshot | None) -> Optional[Dict[str, str]]:
    if snapshot is None:
        return None
    return {field: band_for(getattr(snapshot, field)) for field in _CONDITION_FIELDS}


def _skill_training_summary(slot_result: SlotResolutionResult) -> Optional[dict]:
    sr = slot_result.skill_result
    if sr is None:
        return None
    return {
        "skill": sr.skill.value,
        "value_band": band_for(sr.value_after),
        "did_value_improve": sr.value_after > sr.value_before,
        "form_band": band_for(sr.form_after),
        "did_form_improve": sr.form_after > sr.form_before,
    }


def _social_summary(slot_result: SlotResolutionResult) -> Optional[dict]:
    rr = slot_result.relationship_result
    if rr is None:
        return None
    return {
        "npc_id": rr.npc_id,
        "familiarity_band": band_for(rr.familiarity_after),
    }


def _exploration_summary(slot_result: SlotResolutionResult) -> Optional[dict]:
    er = slot_result.exploration_result
    if er is None:
        return None
    return {
        "skill": er.skill.value,
        "stage": exploration_stage_for(er.progress_after, er.unlocked_now),
        "unlocked_now": er.unlocked_now,
    }


def build_slot_fact(slot_result: SlotResolutionResult) -> DailySlotFact:
    fact = DailySlotFact(
        slot_index=slot_result.slot_index,
        slot_type=slot_result.slot_kind.value,
    )
    if slot_result.slot_kind == SlotKind.COMPANY:
        fact.course = slot_result.company_course.value if slot_result.company_course else None
    elif slot_result.slot_kind == SlotKind.FREE and slot_result.free_action is not None:
        fa = slot_result.free_action
        fact.free_action_type = fa.kind.value
        if fa.kind.value == "TRAIN" and fa.skill is not None:
            fact.free_action_detail = f"train:{fa.skill.value}"
        elif fa.kind.value == "SOCIAL":
            fact.free_action_detail = f"social:{fa.target_npc_id}"
        elif fa.kind.value == "EXPLORE" and fa.exploration_domain is not None:
            fact.free_action_detail = f"explore:{fa.exploration_domain.value}"
        elif fa.kind.value == "PERSONAL" and fa.personal_type is not None:
            fact.free_action_detail = f"personal:{fa.personal_type.value}"
    fact.training_summary = _skill_training_summary(slot_result)
    fact.social_summary = _social_summary(slot_result)
    fact.exploration_summary = _exploration_summary(slot_result)
    return fact


def _effect_semantic_summary(event_result: EventResult) -> List[str]:
    """把 applied_effects 转成叙事语义（绝不发送 before/after 数值）。"""
    out: List[str] = []
    for effect in event_result.applied_effects:
        if isinstance(effect, AppliedRelationshipEffect):
            out.append(f"relationship signal {effect.result.signal.value} with NPC {effect.result.npc_id}")
        elif isinstance(effect, AppliedConditionEffect):
            out.append(f"condition signal {effect.result.signal.value}")
    return out


def _build_event_fact(
    event_result: EventResult,
    event_definition_by_id: Mapping[str, EventDefinition],
) -> DailyEventFact:
    definition = event_definition_by_id.get(event_result.event_id)
    if definition is None:
        raise ValueError(
            f"event_results references missing EventDefinition "
            f"event_id={event_result.event_id}."
        )
    event_brief = str(definition.director_brief or "").strip()
    if not event_brief:
        raise ValueError(
            f"EventDefinition {definition.event_id} has no factual director_brief."
        )

    choice_brief: Optional[str] = None
    if (
        definition.interaction_mode == EventInteractionMode.INTERRUPTIVE
        and event_result.choice_id is None
    ):
        raise ValueError(
            f"Resolved INTERRUPTIVE EventResult {definition.event_id} is missing choice_id."
        )
    if event_result.choice_id is not None:
        matching_choices = [
            choice
            for choice in definition.choices
            if choice.choice_id == event_result.choice_id
        ]
        if len(matching_choices) != 1:
            raise ValueError(
                f"EventResult choice_id={event_result.choice_id} must match exactly one "
                f"choice in EventDefinition {definition.event_id}; "
                f"matched {len(matching_choices)}."
            )
        choice_brief = str(matching_choices[0].director_brief or "").strip()
        if not choice_brief:
            raise ValueError(
                f"EventDefinition {definition.event_id} choice_id={event_result.choice_id} "
                "has no factual director_brief."
            )

    return DailyEventFact(
        event_id=event_result.event_id,
        event_brief=event_brief,
        category=event_result.category.value,
        tier=event_result.tier.value,
        interaction_mode=event_result.interaction_mode.value,
        context_npc_id=event_result.context_npc_id,
        choice_id=event_result.choice_id,
        choice_brief=choice_brief,
        effect_summary=_effect_semantic_summary(event_result),
    )


def _npc_writing_contexts(state: GameState, npc_ids: Sequence[str]) -> List[NPCWritingContext]:
    """只收集当天真正 touched 的 NPC（不发送整个 roster）；缺失即明确失败。"""
    out: List[NPCWritingContext] = []
    seen: set = set()
    for npc_id in npc_ids:
        if npc_id in seen:
            continue
        seen.add(npc_id)
        profile = state.npcs.get(npc_id)
        relationship = state.relationships.get(npc_id)
        if profile is None or relationship is None:
            raise ValueError(f"touched NPC 缺失 NPCProfile/RelationshipState：{npc_id}（canonical context 明确失败）。")
        out.append(build_npc_writing_context(profile, relationship))
    return out


def build_daily_writing_context(
    completed_day_state: GameState,
    slot_results: Sequence[SlotResolutionResult],
    event_results: Sequence[EventResult],
    settlement_result: DaySettlementResult,
    *,
    event_definition_by_id: Mapping[str, EventDefinition],
) -> DailyWritingContext:
    """从已完成一天构造 canonical DailyWritingContext。

    验证：
    - 当天 8 Slots 全部 COMPLETED 且 pending_event is None；
    - slot_results 恰好 8 条、index 集合严格 {0..7}、无重复、completed=True，
      且与 completed_day_state.day 对应 Slot 的 kind/course/free_action 完全一致
      （日期身份由调用方保证：slot_resolution_history(save_id, game_date) 查询或
      当日 Application in-memory collection；SlotResolutionResult 本身不携带日期）；
    - event_results 均属于同一天、event_instance_id 唯一；
    - 每条 event_result 必须能从显式传入的 Definition lookup 恢复 factual
      event brief；已解决的 INTERRUPTIVE event 还必须恢复唯一 choice brief；
    - settlement_result.settled_date 等于当天，且其 condition_result.before 等于
      completed_day_state.condition 快照（防止错传其他 GameState 的同日 settlement）。
    """
    state = completed_day_state
    game_date = state.time.current_date

    if not state.day.slots or any(s.status.value != "COMPLETED" for s in state.day.slots):
        raise ValueError("completed_day_state 必须当天 8 Slots 全部完成。")
    if len(state.day.slots) != 8:
        raise ValueError(f"completed_day_state 必须恰好 8 个 Slot（当前 {len(state.day.slots)}）。")
    if state.pending_event is not None:
        raise ValueError("completed_day_state 存在未处理 PendingEvent，不能构建当日写作上下文。")

    slot_list = list(slot_results)
    if len(slot_list) != 8:
        raise ValueError(f"slot_results 必须恰好 8 条（当前 {len(slot_list)}）。")
    seen_indexes = set()
    for slot_result in slot_list:
        if slot_result.slot_index in seen_indexes:
            raise ValueError(f"slot_results 存在重复 slot_index：{slot_result.slot_index}。")
        seen_indexes.add(slot_result.slot_index)
    if set(seen_indexes) != {0, 1, 2, 3, 4, 5, 6, 7}:
        raise ValueError(f"slot_results 的 slot_index 集合必须严格为 {{0..7}}（当前 {sorted(seen_indexes)}）。")
    for slot_result in slot_list:
        if not slot_result.completed:
            raise ValueError(f"slot_results[{slot_result.slot_index}].completed 必须为 True。")
        state_slot = state.day.slots[slot_result.slot_index]
        if slot_result.slot_kind != state_slot.kind:
            raise ValueError(
                f"slot_results[{slot_result.slot_index}] 的 kind（{slot_result.slot_kind}）与 day slot"
                f"（{state_slot.kind.value}）不一致。"
            )
        if slot_result.slot_kind.value == "COMPANY" and slot_result.company_course != state_slot.company_course:
            raise ValueError(f"slot_results[{slot_result.slot_index}] 的 company_course 与 day slot 不一致。")
        if slot_result.slot_kind.value == "FREE" and slot_result.free_action != state_slot.free_action:
            raise ValueError(f"slot_results[{slot_result.slot_index}] 的 free_action 与 day slot 不一致。")

    seen_instance_ids = set()
    for event_result in event_results:
        if event_result.game_date != game_date:
            raise ValueError(
                f"event_results 含其他日期的事件（{event_result.game_date} != {game_date}）。"
            )
        if event_result.event_instance_id in seen_instance_ids:
            raise ValueError(f"event_results 存在重复 event_instance_id：{event_result.event_instance_id}。")
        seen_instance_ids.add(event_result.event_instance_id)
        if event_result.context_npc_id is not None:
            if event_result.context_npc_id not in state.npcs or event_result.context_npc_id not in state.relationships:
                raise ValueError(
                    f"event_results 引用的 context NPC 缺失：{event_result.context_npc_id}。"
                )
        for effect in event_result.applied_effects:
            if isinstance(effect, AppliedRelationshipEffect):
                npc_id = effect.result.npc_id
                if npc_id not in state.npcs or npc_id not in state.relationships:
                    raise ValueError(f"event_results 引用的关系 NPC 缺失：{npc_id}。")
    if settlement_result.settled_date != game_date:
        raise ValueError(
            f"settlement_result.settled_date（{settlement_result.settled_date}）与当天（{game_date}）不一致。"
        )
    settled_condition = snapshot_of(state.condition)
    before_snapshot = settlement_result.condition_result.before
    for field in ("energy", "voice_condition", "sleep_condition", "mood", "confidence",
                  "muscle_fatigue", "injury_risk", "stress"):
        if abs(getattr(before_snapshot, field) - getattr(settled_condition, field)) > 1e-9:
            raise ValueError(
                f"settlement_result.condition_result.before.{field} 与 completed_day_state.condition 不一致"
                "（可能错传了另一个 GameState 的同日 settlement）。"
            )

    # day_start condition：当天第一个 Slot（index 0）结算前的快照
    day_start = None
    for slot_result in slot_list:
        if slot_result.slot_index == 0:
            day_start = _condition_band_map(slot_result.condition_result.before)
            break

    day_end = _condition_band_map(state.condition)

    menstrual = None
    if state.menstrual_cycle is not None and state.menstrual_cycle.enabled:
        daily = derive_menstrual_daily_state(state.menstrual_cycle, game_date, state.meta.rng_seed)
        menstrual = DailyMenstrualFacts(
            phase=daily.phase.value,
            is_menstruating=daily.is_menstruating,
            period_day=daily.period_day,
            flow_level=daily.flow_level.value,
            symptom_level=daily.symptom_level.value,
        )

    touched_ids: List[str] = []
    for slot_result in slot_list:
        if slot_result.relationship_result is not None:
            npc_id = slot_result.relationship_result.npc_id
            if npc_id not in touched_ids:
                touched_ids.append(npc_id)
    for event_result in event_results:
        if event_result.context_npc_id is not None:
            npc_id = event_result.context_npc_id
            if npc_id not in touched_ids:
                touched_ids.append(npc_id)
        for effect in event_result.applied_effects:
            if isinstance(effect, AppliedRelationshipEffect):
                npc_id = effect.result.npc_id
                if npc_id not in touched_ids:
                    touched_ids.append(npc_id)

    company = state.company
    evaluation = None
    if settlement_result.monthly_evaluation is not None:
        me: MonthlyEvaluationResult = settlement_result.monthly_evaluation
        evaluation = DailyEvaluationFacts(
            evaluation_date=me.evaluation_date,
            overall_score=me.overall_score,
            trainee_day=me.trainee_day,
        )

    return DailyWritingContext(
        game_date=game_date,
        trainee_day=state.time.trainee_day,
        weekday=state.time.weekday,
        education_status=state.player.education_status.value,
        company=DailyCompanyFacts(
            size=company.size.value,
            training_style=company.training_style.value if company.training_style else None,
            management_style=company.management_style.value if company.management_style else None,
            training_intensity=company.training_intensity,
            resource_level=company.resource_level,
        ),
        slots=[build_slot_fact(sr) for sr in sorted(slot_list, key=lambda s: s.slot_index)],
        events=[
            _build_event_fact(er, event_definition_by_id)
            for er in event_results
        ],
        condition=DailyConditionFacts(day_start=day_start, day_end=day_end or {}),
        menstrual=menstrual,
        relationships_touched=_npc_writing_contexts(state, touched_ids),
        monthly_evaluation=evaluation,
    )
