from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from datetime import date
from typing import Dict, List, Optional, Set, Tuple

from core.event_definition import EventCandidate, EventDefinition, EventEvaluation
from core.event_models import EventSoftJudgment, EventTriggerDecision
from core.models import (
    CompanyCourse,
    CompanyState,
    ConditionState,
    EventCategory,
    EventDomainAction,
    EventInteractionMode,
    EventNPCBindingSource,
    EventTier,
    EventTriggerMode,
    FreeAction,
    GameState,
    NPCProfile,
    NPCRole,
    PlayerState,
    RelationshipActionTarget,
    RelationshipEventAction,
    RelationshipState,
    SkillsState,
    SlotKind,
    SlotResolutionResult,
    TraineeState,
)


# ---------------------------------------------------------------------------
# Hybrid Special Event Trigger Framework (Step 8A)
#
# 架构原则：
# - 事件只能来自预定义 EventDefinition（event_id 稳定、由 Python 引用）；
# - Python Hard Gate 决定“逻辑上可能发生吗”（window / once / cooldown /
#   daily budget / predicate），禁止把“刚好超过某个人工数值线”的软性成长
#   判断做成 rigid hard threshold —— 软性自然度交给 LLM_ASSISTED /
#   PROBABILISTIC scoring；
# - LLM（未来由 Application / LLM Layer 调用，本模块不调用任何模型）只能
#   提供 EventSoftJudgment（relevance / reason_tags / should_trigger_any），
#   不能创造 event_id，不能决定数值效果，不能绕过 once / cooldown / window /
#   budget / priority / base_probability；
# - 最终触发权始终属于 Python（Stable RNG + Priority + weighted selection）；
# - 允许“没有任何事件值得发生”（返回 None），绝不强制每天出事件；
# - 本模块不访问 SQLite / SaveStorage，历史由调用方以 EventHistorySnapshot 传入；
# - 本模块不修改 GameState / Skill / Condition / Relationship / Trait，
#   不调用 mark_completed，不实现任何 Event Resolution / PendingEvent / Choice。
# ---------------------------------------------------------------------------


# 每日 Special Event 预算：MAJOR ≤ 1 / natural day，MINOR ≤ 2 / natural day。
# 只硬限制 PROBABILISTIC 与 LLM_ASSISTED；DETERMINISTIC 不受预算阻挡。
DAILY_EVENT_BUDGET: Dict[EventTier, int] = {
    EventTier.MINOR: 2,
    EventTier.MAJOR: 1,
}


# ---------------------------------------------------------------------------
# SlotEventContext（transient，不进入 GameState / 数据库）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SlotEventContext:
    """post-slot 事件判断使用的上下文。

    当前日期 / trainee_day / player / skills / condition / trainee / company
    来自 post-slot GameState；而 slot_index / slot_kind / company_course /
    free_action 必须来自 SlotResolutionResult（mark_completed 后
    DayState.current_slot 已经指向下一格，禁止用它推导刚完成的 Slot）。
    """

    current_date: date
    trainee_day: int
    slot_index: int
    slot_kind: SlotKind
    company_course: Optional[CompanyCourse] = None
    free_action: Optional[FreeAction] = None
    player: Optional[PlayerState] = None
    skills: Optional[SkillsState] = None
    condition: Optional[ConditionState] = None
    trainee: Optional[TraineeState] = None
    company: Optional[CompanyState] = None
    npcs: Optional[Dict[str, NPCProfile]] = None
    relationships: Optional[Dict[str, RelationshipState]] = None
    context_npc_id: Optional[str] = None
    slot_result: Optional[SlotResolutionResult] = None


def build_slot_event_context(
    post_slot_state: GameState,
    slot_result: SlotResolutionResult,
) -> SlotEventContext:
    """从 post-slot GameState + SlotResolutionResult 构造 SlotEventContext。

    Slot identity 完全来自 slot_result，绝不从 post_slot_state.day.current_slot 推导。
    npcs / relationships 是 post-slot 后的当前关系事实
    （SOCIAL 更新后的 familiarity 可被 post-slot Event Trigger 读取）。
    """
    return SlotEventContext(
        current_date=post_slot_state.time.current_date,
        trainee_day=post_slot_state.time.trainee_day,
        slot_index=slot_result.slot_index,
        slot_kind=slot_result.slot_kind,
        company_course=slot_result.company_course,
        free_action=slot_result.free_action,
        player=post_slot_state.player,
        skills=post_slot_state.skills,
        condition=post_slot_state.condition,
        trainee=post_slot_state.trainee,
        company=post_slot_state.company,
        npcs=post_slot_state.npcs,
        relationships=post_slot_state.relationships,
        context_npc_id=slot_result.relationship_result.npc_id if slot_result.relationship_result is not None else None,
        slot_result=slot_result,
    )


# ---------------------------------------------------------------------------
# EventHistorySnapshot（transient：历史由调用方从持久化层整理后传入）
# ---------------------------------------------------------------------------


@dataclass
class EventHistorySnapshot:
    """事件历史的派生快照。

    本模块不直接访问 SQLite；调用方（Persistence / Event History 层）
    负责从 event_history 表整理出该快照传入。
    """

    occurred_event_ids: Set[str] = field(default_factory=set)
    event_counts: Dict[str, int] = field(default_factory=dict)
    last_event_dates: Dict[str, date] = field(default_factory=dict)
    minor_count_today: int = 0
    major_count_today: int = 0

    def has_event(self, event_id: str) -> bool:
        return event_id in self.occurred_event_ids

    def count_event(self, event_id: str) -> int:
        return self.event_counts.get(event_id, 0)

    def last_event_date(self, event_id: str) -> Optional[date]:
        return self.last_event_dates.get(event_id)


# ---------------------------------------------------------------------------
# Stable Event RNG / Instance ID（基于 world rng_seed，不写入、不修改 rng_seed）
# ---------------------------------------------------------------------------


def _stable_draw(
    rng_seed: int,
    game_date: date,
    slot_index: int,
    event_id: str,
    purpose: str = "trigger",
) -> float:
    """从世界根 seed 派生 [0,1) 稳定随机数。

    namespace：event-trigger:{rng_seed}:{date}:{slot_index}:{event_id}:{purpose}
    同一存档 / 同一天 / 同一 Slot / 同一候选事件在未提交情况下重复评估结果一致。
    """
    namespace = f"event-trigger:{rng_seed}:{game_date.isoformat()}:{slot_index}:{event_id}:{purpose}"
    digest = hashlib.sha256(namespace.encode("utf-8")).hexdigest()
    return (int(digest[:8], 16) % 1_000_000) / 1_000_000.0


def derive_event_instance_id(
    rng_seed: int,
    game_date: date,
    slot_index: int,
    event_id: str,
) -> str:
    """稳定事件实例 ID。

    namespace：event-instance:{rng_seed}:{date}:{slot_index}:{event_id}
    同一存档同一 Slot 同一事件在未提交情况下重新评估得到相同 instance id；
    不同日期 / Slot 的同一 event_id 得到不同 instance id。
    """
    namespace = f"event-instance:{rng_seed}:{game_date.isoformat()}:{slot_index}:{event_id}"
    return hashlib.sha256(namespace.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# 阶段一：Python Hard Gate
# ---------------------------------------------------------------------------


def _passes_hard_gate(
    definition: EventDefinition,
    context: SlotEventContext,
    history: EventHistorySnapshot,
) -> bool:
    """逻辑硬门：window / once / cooldown / predicate。

    不在这里做“Dance >= 60”式软性数值阈值——那是评分层的职责。
    """
    trainee_day = context.trainee_day
    if definition.available_from_trainee_day is not None and trainee_day < definition.available_from_trainee_day:
        return False
    if definition.available_until_trainee_day is not None and trainee_day > definition.available_until_trainee_day:
        return False

    if definition.once and history.has_event(definition.event_id):
        return False

    if definition.cooldown_days > 0:
        last = history.last_event_date(definition.event_id)
        if last is not None and (context.current_date - last).days < definition.cooldown_days:
            return False

    if not definition.eligibility(context):
        return False

    return True


def _stable_context_npc_index(
    rng_seed: int,
    context: SlotEventContext,
    event_id: str,
    candidate_count: int,
) -> int:
    namespace = (
        f"event-context-npc:{rng_seed}:{context.current_date.isoformat()}:"
        f"{context.slot_index}:{event_id}"
    )
    digest = hashlib.sha256(namespace.encode("utf-8")).hexdigest()
    return int(digest, 16) % candidate_count


def _prepare_bound_candidate(
    definition: EventDefinition,
    context: SlotEventContext,
    history: EventHistorySnapshot,
    rng_seed: int,
) -> Optional[EventCandidate]:
    """Bind an NPC before candidate preparation; never defer selection to LLM/finalize."""
    if definition.context_npc_source == EventNPCBindingSource.NONE:
        unbound_context = replace(context, context_npc_id=None)
        if not _passes_hard_gate(definition, unbound_context, history):
            return None
        return EventCandidate(definition=definition, context_npc_id=None)

    profiles = context.npcs or {}
    relationships = context.relationships or {}

    if definition.context_npc_source == EventNPCBindingSource.SLOT_CONTEXT:
        npc_id = context.context_npc_id
        if npc_id is None:
            return None
        profile = profiles.get(npc_id)
        if profile is None or not profile.active or npc_id not in relationships:
            return None
        if definition.context_npc_role is not None and profile.role != definition.context_npc_role:
            return None
        bound_context = replace(context, context_npc_id=npc_id)
        if not _passes_hard_gate(definition, bound_context, history):
            return None
        return EventCandidate(definition=definition, context_npc_id=npc_id)

    eligible_npc_ids: List[str] = []
    for npc_id, profile in sorted(profiles.items(), key=lambda item: item[0]):
        if not profile.active or profile.role != definition.context_npc_role:
            continue
        if npc_id not in relationships:
            continue
        candidate_context = replace(context, context_npc_id=npc_id)
        if _passes_hard_gate(definition, candidate_context, history):
            eligible_npc_ids.append(npc_id)

    if not eligible_npc_ids:
        return None
    selected_index = _stable_context_npc_index(
        rng_seed, context, definition.event_id, len(eligible_npc_ids)
    )
    return EventCandidate(
        definition=definition,
        context_npc_id=eligible_npc_ids[selected_index],
    )


def prepare_event_evaluation(
    definitions: List[EventDefinition],
    context: SlotEventContext,
    history: EventHistorySnapshot,
    rng_seed: int,
) -> EventEvaluation:
    """阶段一：Python Hard Gate + Daily Budget，得到 eligible 候选分组。

    Daily budget 只硬限制 PROBABILISTIC / LLM_ASSISTED；
    DETERMINISTIC 通过硬条件后不受随机事件预算阻挡。
    """
    eligible: List[EventCandidate] = []
    for definition in definitions:
        definition.validate()
        candidate = _prepare_bound_candidate(
            definition, context, history, rng_seed
        )
        if candidate is None:
            continue
        if definition.trigger_mode in (EventTriggerMode.PROBABILISTIC, EventTriggerMode.LLM_ASSISTED):
            budget = DAILY_EVENT_BUDGET.get(definition.tier, 0)
            today_count = history.minor_count_today if definition.tier == EventTier.MINOR else history.major_count_today
            if today_count >= budget:
                continue
        eligible.append(candidate)

    deterministic = tuple(
        c for c in eligible if c.definition.trigger_mode == EventTriggerMode.DETERMINISTIC
    )
    probabilistic = tuple(
        c for c in eligible if c.definition.trigger_mode == EventTriggerMode.PROBABILISTIC
    )
    llm_assisted = tuple(
        c for c in eligible if c.definition.trigger_mode == EventTriggerMode.LLM_ASSISTED
    )
    return EventEvaluation(
        eligible=tuple(eligible),
        deterministic=deterministic,
        probabilistic=probabilistic,
        llm_assisted=llm_assisted,
    )


# ---------------------------------------------------------------------------
# 阶段二：最终触发裁决
# ---------------------------------------------------------------------------


def _validate_soft_judgment(
    llm_candidates: Tuple[EventCandidate, ...],
    soft_judgment: EventSoftJudgment,
) -> None:
    """LLM 不能创造 Event ID；Core 同时防御语义非法 judgment（不信任 Orchestration）。

    - scores 只能包含 eligible LLM_ASSISTED 候选；
    - should_trigger_any=False → scores 必须为空；
    - should_trigger_any=True → 必须恰好一条 score（零或一个事件，禁止多选）；
    - relevance 0..1 由 Pydantic schema 保证。
    """
    allowed = {candidate.definition.event_id for candidate in llm_candidates}
    unknown = [s.event_id for s in soft_judgment.scores if s.event_id not in allowed]
    if unknown:
        raise ValueError(f"EventSoftJudgment 包含未知 event_id（不允许 LLM 创造事件）：{unknown}")
    if not soft_judgment.should_trigger_any:
        if soft_judgment.scores:
            raise ValueError("should_trigger_any=False 但 scores 非空（Core 拒绝语义非法 judgment）。")
        return
    if len(soft_judgment.scores) != 1:
        raise ValueError(
            f"should_trigger_any=True 必须恰好一个候选 score（当前 {len(soft_judgment.scores)}，禁止多事件）。"
        )


def _llm_effective_probability(base_probability: float, relevance: float) -> float:
    """P_effective = base × (0.25 + 0.75 × relevance)，clamp 0–1。

    relevance 永远不能把概率提高到 base_probability 以上。
    """
    p = base_probability * (0.25 + 0.75 * max(0.0, min(1.0, relevance)))
    return max(0.0, min(1.0, p))


def finalize_event_selection(
    evaluation: EventEvaluation,
    context: SlotEventContext,
    rng_seed: int,
    soft_judgment: Optional[EventSoftJudgment] = None,
) -> Optional[EventTriggerDecision]:
    """阶段二：决定最终是否触发（最多一个事件）。

    - DETERMINISTIC：通过硬门后直接成为触发候选（不乘随机概率）；
    - PROBABILISTIC：stable RNG draw < base_probability 才触发；
    - LLM_ASSISTED：soft_judgment 必须提供（否则明确失败）；先校验
      event_id 白名单，再按 should_trigger_any / score 处理：
      未出现在 scores 中的候选视为未推荐（过滤，不触发）；
      relevance 只参与 effective probability；
    - 最终：优先取 priority 最高者；同 priority 用 stable weighted selection。
    """
    if evaluation.llm_assisted and soft_judgment is None:
        raise ValueError("存在 LLM_ASSISTED 候选但未提供 EventSoftJudgment（两阶段评估必须先 prepare 再 finalize）。")
    if soft_judgment is not None:
        _validate_soft_judgment(evaluation.llm_assisted, soft_judgment)

    slot_index = context.slot_index
    game_date = context.current_date

    triggered: List[Tuple[EventCandidate, float, Optional[float]]] = []

    for candidate in evaluation.deterministic:
        triggered.append((candidate, 1.0, None))

    for candidate in evaluation.probabilistic:
        definition = candidate.definition
        draw = _stable_draw(rng_seed, game_date, slot_index, definition.event_id, "trigger")
        if draw < definition.base_probability:
            triggered.append((candidate, definition.base_probability, None))

    if evaluation.llm_assisted and soft_judgment is not None and soft_judgment.should_trigger_any:
        scores = {s.event_id: s for s in soft_judgment.scores}
        for candidate in evaluation.llm_assisted:
            definition = candidate.definition
            score = scores.get(definition.event_id)
            if score is None:
                continue  # 未推荐 → 不通过
            relevance = score.relevance
            effective = _llm_effective_probability(definition.base_probability, relevance)
            draw = _stable_draw(rng_seed, game_date, slot_index, definition.event_id, "trigger")
            if draw < effective:
                triggered.append((candidate, effective, relevance))

    if not triggered:
        return None

    max_priority = max(candidate.definition.priority for candidate, _, _ in triggered)
    top = [
        (candidate, probability, relevance)
        for candidate, probability, relevance in triggered
        if candidate.definition.priority == max_priority
    ]
    chosen = _weighted_pick(top, rng_seed, game_date, slot_index)
    if chosen is None:
        return None

    candidate, effective_probability, relevance = chosen
    definition = candidate.definition
    return EventTriggerDecision(
        event_id=definition.event_id,
        category=definition.category,
        trigger_mode=definition.trigger_mode,
        tier=definition.tier,
        interaction_mode=definition.interaction_mode,
        priority=definition.priority,
        base_probability=definition.base_probability,
        soft_relevance=relevance,
        effective_probability=effective_probability,
        triggered=True,
        slot_index=slot_index,
        game_date=game_date,
        context_npc_id=candidate.context_npc_id,
    )


def _weighted_pick(
    candidates: List[Tuple[EventCandidate, float, Optional[float]]],
    rng_seed: int,
    game_date: date,
    slot_index: int,
) -> Optional[Tuple[EventCandidate, float, Optional[float]]]:
    """同 priority 候选之间的稳定 weighted selection（selection_weight）。"""
    if not candidates:
        return None
    weights = [
        max(0.0, candidate.definition.selection_weight)
        for candidate, _, _ in candidates
    ]
    total = sum(weights)
    if total <= 0:
        return candidates[0]
    joined = ",".join(candidate.definition.event_id for candidate, _, _ in candidates)
    draw = _stable_draw(rng_seed, game_date, slot_index, joined, "weighted") * total
    acc = 0.0
    for candidate, weight in zip(candidates, weights):
        acc += weight
        if draw < acc:
            return candidate
    return candidates[-1]


# The canonical production tuple lives in core.events.registry.  Re-export it
# here to preserve the established public import path used by Application.
from core.events.registry import EVENT_DEFINITIONS
