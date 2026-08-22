from core.event_definition import EventDefinition
from core.models import ConditionSignal as CS, FreeActionKind as FA, RelationshipSignal as RS
from core.events.common import (
    CONDITIONAL, I, L, MINOR, N, P, RELATIONSHIP, ROSTER, SLOT, TRAINEE,
    all_of, bound_relationship, choice, company_slot, completed_slot_has_skill_result,
    condition_any, condition_effect, condition_range, free_action,
    relationship_effect, slot_index, slot_index_at_least,
    unlocked_skill_count_at_least,
)


BREAK = free_action(FA.RECOVER, FA.PERSONAL)


PHYSICAL_EMOTIONAL_EVENTS = (
    # 221 state_tired_start_acknowledged
    EventDefinition(event_id="state_tired_start_acknowledged", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.20, priority=10, eligibility=all_of(slot_index(0), condition_any(condition_range("energy", 0, 34), condition_range("sleep_condition", 0, 34))), effects=(condition_effect(CS.STRESS_RELIEF),), director_brief="The player recognizes that today's start feels tired and adjusts expectations."),
    # 222 state_not_enough_sleep_irritation
    EventDefinition(event_id="state_not_enough_sleep_irritation", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.16, priority=10, eligibility=all_of(condition_range("sleep_condition", 0, 34), condition_range("mood", 1)), effects=(condition_effect(CS.MOOD_HIT),), director_brief="Limited sleep makes a small inconvenience feel more irritating."),
    # 223 state_muscle_soreness_caution
    EventDefinition(event_id="state_muscle_soreness_caution", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.17, priority=10, eligibility=all_of(condition_range("muscle_fatigue", 50), completed_slot_has_skill_result), effects=(condition_effect(CS.STRESS_RELIEF),), director_brief="Ordinary post-practice soreness leads the player to move deliberately."),
    # 224 state_energy_good_momentum
    EventDefinition(event_id="state_energy_good_momentum", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.17, priority=10, eligibility=condition_range("energy", 70), effects=(condition_effect(CS.MOOD_LIFT),), director_brief="The player notices that today's energy is supporting an easy rhythm."),
    # 225 state_late_day_heaviness
    EventDefinition(event_id="state_late_day_heaviness", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.18, priority=10, eligibility=all_of(slot_index(6, 7), condition_range("energy", 0, 49)), effects=(condition_effect(CS.STRESS_INCREASE),), director_brief="Late in the day, ordinary heaviness becomes harder to ignore."),
    # 226 state_pressure_named
    EventDefinition(event_id="state_pressure_named", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.18, priority=10, eligibility=condition_range("stress", 50), effects=(condition_effect(CS.STRESS_RELIEF),), director_brief="The player identifies the immediate source of ordinary pressure."),
    # 227 state_minor_bad_mood_passes
    EventDefinition(event_id="state_minor_bad_mood_passes", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.15, priority=10, eligibility=all_of(condition_range("mood", 0, 49), condition_range("stress", 0, 94)), effects=(condition_effect(CS.MOOD_LIFT),), director_brief="A minor bad mood loosens after the schedule changes pace."),
    # 228 state_busy_room_stress
    EventDefinition(event_id="state_busy_room_stress", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, eligibility=all_of(company_slot, condition_range("stress", 35)), effects=(condition_effect(CS.STRESS_INCREASE),), director_brief="Busy surroundings introduced by the event amplify existing pressure."),
    # 229 state_smooth_sequence_confidence
    EventDefinition(event_id="state_smooth_sequence_confidence", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.13, priority=10, eligibility=all_of(slot_index_at_least(1), condition_range("confidence", 0, 69)), effects=(condition_effect(CS.CONFIDENCE_GAIN),), director_brief="The current task and immediately preceding routine feel steady."),
    # 230 state_small_error_lingers
    EventDefinition(event_id="state_small_error_lingers", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, eligibility=all_of(completed_slot_has_skill_result, condition_range("confidence", 1)), effects=(condition_effect(CS.CONFIDENCE_HIT),), director_brief="A small practice error introduced by the event lingers mentally."),
    # 231 state_trainee_notices_tension
    EventDefinition(event_id="state_trainee_notices_tension", category=RELATIONSHIP, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.16, priority=10, context_npc_source=ROSTER, context_npc_role=TRAINEE, eligibility=all_of(condition_range("stress", 70), bound_relationship(familiarity_min=6)), effects=(relationship_effect(RS.RELIABILITY_CONFIRMED),), director_brief="The selected trainee notices tension and keeps the interaction straightforward."),
    # 232 state_focus_returns
    EventDefinition(event_id="state_focus_returns", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.18, priority=10, eligibility=all_of(slot_index_at_least(1), condition_range("stress", 0, 94)), director_brief="After a slow stretch introduced by the event, the player finds workable focus."),
    # 233 state_trainee_shared_focus
    EventDefinition(event_id="state_trainee_shared_focus", category=RELATIONSHIP, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.15, priority=10, context_npc_source=SLOT, context_npc_role=TRAINEE, eligibility=all_of(free_action(FA.SOCIAL), bound_relationship(tension_max=69)), effects=(relationship_effect(RS.SHARED_POSITIVE_EXPERIENCE),), director_brief="Quiet company with the selected SOCIAL trainee feels settled."),
    # 234 state_flow_interrupted_by_transition
    EventDefinition(event_id="state_flow_interrupted_by_transition", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, eligibility=all_of(slot_index_at_least(1), company_slot, condition_any(condition_range("mood", 70), condition_range("confidence", 70))), director_brief="A room transition introduced by the event interrupts a productive rhythm."),
    # 235 state_focus_scattered_notes
    EventDefinition(event_id="state_focus_scattered_notes", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.13, priority=10, eligibility=all_of(slot_index_at_least(3), unlocked_skill_count_at_least(2)), director_brief="Notes from several topics introduced by the event become hard to organize."),
    # 236 state_trainee_focus_boundary
    EventDefinition(event_id="state_trainee_focus_boundary", category=RELATIONSHIP, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, cooldown_days=5, context_npc_source=SLOT, context_npc_role=TRAINEE, eligibility=all_of(free_action(FA.SOCIAL), condition_any(condition_range("stress", 50), condition_range("mood", 0, 34))), effects=(relationship_effect(RS.RELIABILITY_CONFIRMED),), director_brief="The player asks the selected SOCIAL trainee for a quieter few minutes."),
    # 237 state_recovery_feels_adequate
    EventDefinition(event_id="state_recovery_feels_adequate", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.15, priority=10, cooldown_days=3, eligibility=all_of(slot_index_at_least(4), condition_range("energy", 35, 69), condition_range("sleep_condition", 35, 69), condition_range("muscle_fatigue", 30, 69)), director_brief="The player notices ordinary recovery between blocks."),
    # 238 state_recovery_break_structure
    EventDefinition(event_id="state_recovery_break_structure", category=CONDITIONAL, trigger_mode=L, tier=MINOR, interaction_mode=I, base_probability=.46, priority=20, cooldown_days=5, eligibility=all_of(free_action(FA.RECOVER), condition_range("stress", 35)), director_brief="The completed recovery slot leaves a choice of quiet or light movement.", choices=(choice("sit_quietly", "安静坐一会儿", condition_effect(CS.STRESS_RELIEF)), choice("take_low_key_walk", "出去慢慢走一小圈", condition_effect(CS.MOOD_LIFT)))),
    # 239 state_pressure_share_or_hold
    EventDefinition(event_id="state_pressure_share_or_hold", category=CONDITIONAL, trigger_mode=L, tier=MINOR, interaction_mode=I, base_probability=.38, priority=20, cooldown_days=8, eligibility=all_of(BREAK, condition_range("stress", 50)), director_brief="The event presents one ordinary pressure to name or keep private.", choices=(choice("name_practical_concern", "把具体担心的事说出来", condition_effect(CS.STRESS_RELIEF)), choice("keep_concern_private", "先放在心里，继续做事"))),
    # 240 state_good_day_pace_choice
    EventDefinition(event_id="state_good_day_pace_choice", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=I, base_probability=.14, priority=20, cooldown_days=6, eligibility=all_of(BREAK, condition_range("mood", 70), condition_range("energy", 70)), director_brief="The free slot occurs during a smooth day.", choices=(choice("use_momentum", "趁状态好集中复习一会儿", condition_effect(CS.CONFIDENCE_GAIN)), choice("preserve_easy_pace", "保持现在轻松的节奏", condition_effect(CS.STRESS_RELIEF)))),
)
