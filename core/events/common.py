from __future__ import annotations

import calendar
from datetime import timedelta
from typing import Callable, Optional, Tuple

from core.event_models import EventChoiceDefinition
from core.models import (
    CompanyCourse,
    ConditionEventAction,
    ConditionSignal,
    EducationStatus,
    EventCategory,
    EventInteractionMode,
    EventNPCBindingSource,
    EventTier,
    EventTriggerMode,
    ExplorationDomain,
    FreeActionKind,
    NPCRole,
    RelationshipActionTarget,
    RelationshipEventAction,
    RelationshipSignal,
    SkillId,
    SlotKind,
)

# Compact aliases mirror the reviewed catalog notation while remaining typed enums.
D = EventTriggerMode.DETERMINISTIC
P = EventTriggerMode.PROBABILISTIC
L = EventTriggerMode.LLM_ASSISTED
N = EventInteractionMode.NON_INTERRUPTIVE
I = EventInteractionMode.INTERRUPTIVE
MINOR = EventTier.MINOR
MAJOR = EventTier.MAJOR
SCHEDULED = EventCategory.SCHEDULED
CONDITIONAL = EventCategory.CONDITIONAL
OPPORTUNITY = EventCategory.OPPORTUNITY
RELATIONSHIP = EventCategory.RELATIONSHIP
CHAIN = EventCategory.CHAIN
NONE = EventNPCBindingSource.NONE
SLOT = EventNPCBindingSource.SLOT_CONTEXT
ROSTER = EventNPCBindingSource.ROSTER
TRAINEE = NPCRole.TRAINEE
TEACHER = NPCRole.TEACHER
STAFF = NPCRole.STAFF

Eligibility = Callable[[object], bool]


def all_of(*predicates: Eligibility) -> Eligibility:
    return lambda context: all(predicate(context) for predicate in predicates)


def any_of(*predicates: Eligibility) -> Eligibility:
    return lambda context: any(predicate(context) for predicate in predicates)


def company_slot(context: object) -> bool:
    return context.slot_kind == SlotKind.COMPANY


def free_slot(context: object) -> bool:
    return context.slot_kind == SlotKind.FREE


def school_slot(context: object) -> bool:
    return context.slot_kind == SlotKind.SCHOOL


def company_course(*courses: CompanyCourse) -> Eligibility:
    allowed = frozenset(courses)
    return lambda context: company_slot(context) and context.company_course in allowed


def company_skill_course(context: object) -> bool:
    return company_course(
        CompanyCourse.DANCE,
        CompanyCourse.VOCAL,
        CompanyCourse.RAP,
        CompanyCourse.STAGE,
        CompanyCourse.CAMERA,
        CompanyCourse.LANGUAGE,
    )(context)


def free_action(*kinds: FreeActionKind) -> Eligibility:
    allowed = frozenset(kinds)
    return lambda context: (
        free_slot(context)
        and context.free_action is not None
        and context.free_action.kind in allowed
    )


def free_train(*skills: SkillId) -> Eligibility:
    allowed = frozenset(skills)
    return lambda context: (
        free_action(FreeActionKind.TRAIN)(context)
        and context.free_action.skill in allowed
    )


def free_explore(domain: ExplorationDomain) -> Eligibility:
    return lambda context: (
        free_action(FreeActionKind.EXPLORE)(context)
        and context.free_action.exploration_domain == domain
    )


def slot_index(*indices: int) -> Eligibility:
    allowed = frozenset(indices)
    return lambda context: context.slot_index in allowed


def slot_index_at_least(minimum: int) -> Eligibility:
    return lambda context: context.slot_index >= minimum


def slot_index_below(maximum: int) -> Eligibility:
    return lambda context: context.slot_index < maximum


def weekday(*days: int) -> Eligibility:
    allowed = frozenset(days)
    return lambda context: context.current_date.weekday() in allowed


def in_school(context: object) -> bool:
    return (
        context.player is not None
        and context.player.education_status == EducationStatus.ENROLLED
    )


def trainee_day_at_least(minimum: int) -> Eligibility:
    return lambda context: context.trainee_day >= minimum


def month_end_within(days: int) -> Eligibility:
    def predicate(context: object) -> bool:
        last_day = calendar.monthrange(
            context.current_date.year, context.current_date.month
        )[1]
        return 0 <= last_day - context.current_date.day <= days

    return predicate


def month_end_exactly(days: int) -> Eligibility:
    def predicate(context: object) -> bool:
        last_day = calendar.monthrange(
            context.current_date.year, context.current_date.month
        )[1]
        return last_day - context.current_date.day == days

    return predicate


def skill_unlocked(skill: SkillId) -> Eligibility:
    return lambda context: (
        context.skills is not None and getattr(context.skills, skill.value).unlocked
    )


def skill_locked(skill: SkillId) -> Eligibility:
    return lambda context: (
        context.skills is not None and not getattr(context.skills, skill.value).unlocked
    )


def any_skill_unlocked(*skills: SkillId) -> Eligibility:
    selected = skills or tuple(SkillId)
    return lambda context: any(
        getattr(context.skills, skill.value).unlocked for skill in selected
    ) if context.skills is not None else False


def unlocked_skill_count_at_least(minimum: int) -> Eligibility:
    return lambda context: (
        context.skills is not None
        and sum(getattr(context.skills, skill.value).unlocked for skill in SkillId)
        >= minimum
    )


def condition_range(field: str, minimum: float = 0.0, maximum: float = 100.0) -> Eligibility:
    return lambda context: (
        context.condition is not None
        and minimum <= getattr(context.condition, field) <= maximum
    )


def condition_any(*predicates: Eligibility) -> Eligibility:
    return any_of(*predicates)


def bound_relationship(
    *,
    familiarity_min: float = 0.0,
    familiarity_max: float = 100.0,
    closeness_min: float = 0.0,
    trust_min: float = 0.0,
    tension_min: float = 0.0,
    tension_max: float = 100.0,
    interacted: Optional[bool] = None,
    days_since_interaction_min: Optional[int] = None,
) -> Eligibility:
    def predicate(context: object) -> bool:
        if context.context_npc_id is None or context.relationships is None:
            return False
        relation = context.relationships.get(context.context_npc_id)
        if relation is None:
            return False
        if not familiarity_min <= relation.familiarity <= familiarity_max:
            return False
        if relation.closeness < closeness_min or relation.trust < trust_min:
            return False
        if not tension_min <= relation.tension <= tension_max:
            return False
        if interacted is not None:
            if interacted != (relation.last_interaction_date is not None):
                return False
        if days_since_interaction_min is not None:
            if relation.last_interaction_date is None:
                return False
            if context.current_date - relation.last_interaction_date < timedelta(
                days=days_since_interaction_min
            ):
                return False
        return True

    return predicate


def roster_has(role: NPCRole) -> Eligibility:
    return lambda context: (
        context.npcs is not None
        and any(profile.active and profile.role == role for profile in context.npcs.values())
    )


def teacher_matches_course(context: object) -> bool:
    if (
        context.context_npc_id is None
        or context.npcs is None
        or context.company_course is None
    ):
        return False
    profile = context.npcs.get(context.context_npc_id)
    return bool(
        profile is not None
        and profile.active
        and profile.role == NPCRole.TEACHER
        and profile.specialty == context.company_course
    )


def completed_slot_has_skill_result(context: object) -> bool:
    return context.slot_result is not None and context.slot_result.skill_result is not None


def completed_slot_skill_result_is(*skills: SkillId) -> Eligibility:
    allowed = frozenset(skills)
    return lambda context: (
        context.slot_result is not None
        and context.slot_result.skill_result is not None
        and context.slot_result.skill_result.skill in allowed
    )


_COURSE_SKILLS = {
    CompanyCourse.DANCE: SkillId.DANCE,
    CompanyCourse.VOCAL: SkillId.VOCAL,
    CompanyCourse.RAP: SkillId.RAP,
    CompanyCourse.STAGE: SkillId.STAGE,
    CompanyCourse.CAMERA: SkillId.CAMERA,
    CompanyCourse.LANGUAGE: SkillId.LANGUAGE,
}


def current_course_skill_value_at_least(minimum: int) -> Eligibility:
    def predicate(context: object) -> bool:
        skill = _COURSE_SKILLS.get(context.company_course)
        if skill is None or context.skills is None:
            return False
        state = getattr(context.skills, skill.value)
        return state.unlocked and state.value is not None and state.value >= minimum

    return predicate


def relationship_effect(signal: RelationshipSignal) -> RelationshipEventAction:
    return RelationshipEventAction(
        target=RelationshipActionTarget.CONTEXT_NPC,
        signal=signal,
    )


def condition_effect(signal: ConditionSignal) -> ConditionEventAction:
    return ConditionEventAction(signal=signal)


def choice(
    choice_id: str,
    brief: str,
    *effects: object,
) -> EventChoiceDefinition:
    return EventChoiceDefinition(
        choice_id=choice_id,
        director_brief=brief,
        effects=tuple(effects),
    )
