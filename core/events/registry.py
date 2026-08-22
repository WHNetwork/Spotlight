from types import MappingProxyType
from typing import Mapping, Sequence

from core.event_definition import EventDefinition
from core.events.acting_creation import ACTING_CREATION_EVENTS
from core.events.company_life import COMPANY_LIFE_EVENTS
from core.events.daily_life import DAILY_LIFE_EVENTS
from core.events.opportunities import SMALL_OPPORTUNITY_EVENTS
from core.events.physical_emotional import PHYSICAL_EMOTIONAL_EVENTS
from core.events.rare_events import RARE_EVENTS
from core.events.school_life import SCHOOL_LIFE_EVENTS
from core.events.teacher_staff import TEACHER_STAFF_EVENTS
from core.events.trainee_social import TRAINEE_SOCIAL_EVENTS
from core.events.training import TRAINING_EVENTS


EVENT_DEFINITIONS: tuple[EventDefinition, ...] = (
    *TRAINING_EVENTS,
    *TRAINEE_SOCIAL_EVENTS,
    *TEACHER_STAFF_EVENTS,
    *COMPANY_LIFE_EVENTS,
    *DAILY_LIFE_EVENTS,
    *PHYSICAL_EMOTIONAL_EVENTS,
    *SCHOOL_LIFE_EVENTS,
    *ACTING_CREATION_EVENTS,
    *SMALL_OPPORTUNITY_EVENTS,
    *RARE_EVENTS,
)


def build_event_definition_lookup(
    definitions: Sequence[EventDefinition],
) -> Mapping[str, EventDefinition]:
    """Build a strict transient event_id lookup for an explicit registry."""
    lookup: dict[str, EventDefinition] = {}
    for definition in definitions:
        if definition.event_id in lookup:
            raise ValueError(
                f"Duplicate EventDefinition event_id={definition.event_id}."
            )
        lookup[definition.event_id] = definition
    return MappingProxyType(lookup)


EVENT_DEFINITION_BY_ID: Mapping[str, EventDefinition] = (
    build_event_definition_lookup(EVENT_DEFINITIONS)
)


def get_event_definition(event_id: str) -> EventDefinition:
    """Return a production definition, failing loudly on registry/history drift."""
    definition = EVENT_DEFINITION_BY_ID.get(event_id)
    if definition is None:
        raise ValueError(
            f"Missing EventDefinition for persisted event_id={event_id}."
        )
    return definition
