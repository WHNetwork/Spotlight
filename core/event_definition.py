from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Optional, Tuple

from core.event_effects import validate_event_actions
from core.event_models import EventChoiceDefinition
from core.models import (
    EventCategory,
    EventDomainAction,
    EventInteractionMode,
    EventNPCBindingSource,
    EventTier,
    EventTriggerMode,
    NPCRole,
    RelationshipActionTarget,
    RelationshipEventAction,
)

if TYPE_CHECKING:
    from core.event_triggers import SlotEventContext


@dataclass(frozen=True)
class EventDefinition:
    """Static event content definition; never persisted into GameState or SQLite."""

    event_id: str
    category: EventCategory
    trigger_mode: EventTriggerMode
    tier: EventTier
    interaction_mode: EventInteractionMode
    priority: int = 0
    base_probability: float = 1.0
    selection_weight: float = 1.0
    once: bool = False
    cooldown_days: int = 0
    available_from_trainee_day: Optional[int] = None
    available_until_trainee_day: Optional[int] = None
    director_brief: str = ""
    context_npc_source: EventNPCBindingSource = EventNPCBindingSource.NONE
    context_npc_role: Optional[NPCRole] = None
    eligibility: Callable[["SlotEventContext"], bool] = lambda context: True
    choices: Tuple[EventChoiceDefinition, ...] = ()
    effects: Tuple[EventDomainAction, ...] = ()

    def validate(self) -> None:
        if not str(self.event_id or "").strip():
            raise ValueError("event_id must be a non-empty string.")
        if not (0.0 <= self.base_probability <= 1.0):
            raise ValueError(f"event {self.event_id}: base_probability must be in 0..1.")
        if self.selection_weight <= 0.0:
            raise ValueError(f"event {self.event_id}: selection_weight must be > 0.")
        if self.cooldown_days < 0:
            raise ValueError(f"event {self.event_id}: cooldown_days cannot be negative.")
        if self.eligibility is None:
            raise ValueError(f"event {self.event_id}: eligibility is required.")
        if self.context_npc_role is not None and not isinstance(
            self.context_npc_role, NPCRole
        ):
            raise ValueError(f"event {self.event_id}: context_npc_role must be NPCRole.")
        if self.context_npc_source == EventNPCBindingSource.NONE:
            if self.context_npc_role is not None:
                raise ValueError(f"event {self.event_id}: NONE binding cannot declare role.")
        elif self.context_npc_source == EventNPCBindingSource.ROSTER:
            if self.context_npc_role is None:
                raise ValueError(f"event {self.event_id}: ROSTER binding requires role.")
        elif self.context_npc_source != EventNPCBindingSource.SLOT_CONTEXT:
            raise ValueError(
                f"event {self.event_id}: unsupported NPC source {self.context_npc_source!r}."
            )

        all_actions = list(self.effects)
        for choice in self.choices:
            all_actions.extend(choice.effects)
        if any(
            isinstance(action, RelationshipEventAction)
            and action.target == RelationshipActionTarget.CONTEXT_NPC
            for action in all_actions
        ) and self.context_npc_source == EventNPCBindingSource.NONE:
            raise ValueError(f"event {self.event_id}: CONTEXT_NPC effects require binding.")

        choice_ids = [choice.choice_id for choice in self.choices]
        if len(set(choice_ids)) != len(choice_ids):
            raise ValueError(f"event {self.event_id}: choice_id values must be unique.")
        if self.interaction_mode == EventInteractionMode.NON_INTERRUPTIVE and self.choices:
            raise ValueError(f"NON_INTERRUPTIVE event {self.event_id} cannot have choices.")
        if self.interaction_mode == EventInteractionMode.INTERRUPTIVE and not self.choices:
            raise ValueError(f"INTERRUPTIVE event {self.event_id} requires choices.")
        if self.interaction_mode == EventInteractionMode.INTERRUPTIVE and self.effects:
            raise ValueError(f"INTERRUPTIVE event {self.event_id} cannot have top-level effects.")
        requires_brief = (
            self.trigger_mode == EventTriggerMode.LLM_ASSISTED
            or self.interaction_mode == EventInteractionMode.INTERRUPTIVE
        )
        if requires_brief and not str(self.director_brief or "").strip():
            raise ValueError(f"event {self.event_id}: director_brief is required.")
        for choice in self.choices:
            if not str(choice.choice_id or "").strip():
                raise ValueError(f"event {self.event_id}: choice_id cannot be empty.")
            if not str(choice.director_brief or "").strip():
                raise ValueError(f"event {self.event_id}: choice brief cannot be empty.")
        validate_event_actions(self.effects)
        for choice in self.choices:
            validate_event_actions(choice.effects)


@dataclass(frozen=True)
class EventCandidate:
    definition: EventDefinition
    context_npc_id: Optional[str] = None


@dataclass(frozen=True)
class EventEvaluation:
    eligible: Tuple[EventCandidate, ...]
    deterministic: Tuple[EventCandidate, ...]
    probabilistic: Tuple[EventCandidate, ...]
    llm_assisted: Tuple[EventCandidate, ...]
