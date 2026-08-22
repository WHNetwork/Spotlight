from core.event_definition import EventDefinition
from core.models import ConditionSignal as CS, FreeActionKind as FA
from core.events.common import (
    CONDITIONAL, D, I, L, MINOR, N, P, SCHEDULED, all_of, choice,
    company_slot, condition_effect, condition_range, free_action, free_slot,
    in_school, slot_index, slot_index_below, weekday,
)


WEEKDAY = weekday(0, 1, 2, 3, 4)
BREAK = free_action(FA.RECOVER, FA.PERSONAL)


SCHOOL_LIFE_EVENTS = (
    # 241 school_class_attendance_recorded
    EventDefinition(event_id="school_class_attendance_recorded", category=SCHEDULED, trigger_mode=D, tier=MINOR, interaction_mode=N, priority=20, eligibility=all_of(in_school, WEEKDAY, slot_index(0)), director_brief="The player's ordinary school attendance is recorded before trainee schedules."),
    # 242 school_assignment_deadline_pressure
    EventDefinition(event_id="school_assignment_deadline_pressure", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.15, priority=10, eligibility=all_of(in_school, WEEKDAY, condition_range("stress", 0, 94)), effects=(condition_effect(CS.STRESS_INCREASE),), director_brief="A normal assignment deadline introduced by the event overlaps with training."),
    # 243 school_class_notes_in_bag
    EventDefinition(event_id="school_class_notes_in_bag", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.16, priority=10, eligibility=all_of(in_school, slot_index(0), company_slot), director_brief="School notes introduced by the event remain in the player's bag."),
    # 244 school_group_project_update
    EventDefinition(event_id="school_group_project_update", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.12, priority=10, eligibility=all_of(in_school, free_slot), director_brief="A routine school group-project update arrives during the free slot."),
    # 245 school_quiz_talk_background
    EventDefinition(event_id="school_quiz_talk_background", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.13, priority=10, eligibility=all_of(in_school, WEEKDAY, slot_index(0)), director_brief="Event-local classmates discuss an upcoming quiz around the player."),
    # 246 school_commute_transfer_routine
    EventDefinition(event_id="school_commute_transfer_routine", category=SCHEDULED, trigger_mode=D, tier=MINOR, interaction_mode=N, priority=20, cooldown_days=2, eligibility=all_of(in_school, WEEKDAY, slot_index(0), company_slot), director_brief="The player makes the routine transition from school to the first company course."),
    # 247 school_late_bell_rush
    EventDefinition(event_id="school_late_bell_rush", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, cooldown_days=4, eligibility=all_of(in_school, WEEKDAY, slot_index(0), company_slot), director_brief="The school bell timing introduced by the event compresses departure."),
    # 248 school_uniform_change_logistics
    EventDefinition(event_id="school_uniform_change_logistics", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.12, priority=10, cooldown_days=5, eligibility=all_of(in_school, company_slot), director_brief="The player fits an ordinary clothing change into the company transition."),
    # 249 school_company_overlap_stress
    EventDefinition(event_id="school_company_overlap_stress", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.13, priority=10, cooldown_days=5, eligibility=all_of(in_school, WEEKDAY, condition_range("stress", 0, 94)), effects=(condition_effect(CS.STRESS_INCREASE),), director_brief="School and company tasks remain mentally present at the same time."),
    # 250 school_early_arrival_wait
    EventDefinition(event_id="school_early_arrival_wait", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, cooldown_days=3, eligibility=all_of(in_school, WEEKDAY, company_slot), director_brief="The event establishes an early arrival before the completed company course."),
    # 251 school_peer_asks_training_schedule
    EventDefinition(event_id="school_peer_asks_training_schedule", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.12, priority=10, cooldown_days=7, eligibility=all_of(in_school, WEEKDAY, slot_index(0)), director_brief="An unmodeled school peer asks a factual question about training."),
    # 252 school_lunch_homework_tradeoff_seen
    EventDefinition(event_id="school_lunch_homework_tradeoff_seen", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, cooldown_days=4, eligibility=all_of(in_school, BREAK), director_brief="Event-local classmates use part of a meal break for schoolwork."),
    # 253 school_break_homework_choice
    EventDefinition(event_id="school_break_homework_choice", category=CONDITIONAL, trigger_mode=L, tier=MINOR, interaction_mode=I, base_probability=.44, priority=20, cooldown_days=5, eligibility=all_of(in_school, BREAK), director_brief="The event introduces one small school task during the free slot.", choices=(choice("review_small_task", "处理一个小的学校任务", condition_effect(CS.STRESS_RELIEF)), choice("preserve_break", "把这段时间留给休息"))),
    # 254 school_peer_invitation_boundary
    EventDefinition(event_id="school_peer_invitation_boundary", category=CONDITIONAL, trigger_mode=L, tier=MINOR, interaction_mode=I, base_probability=.34, priority=20, cooldown_days=12, eligibility=all_of(in_school, WEEKDAY, slot_index_below(7)), director_brief="The event introduces a small school-peer invitation before the next canonical slot.", choices=(choice("join_briefly", "短暂参加一下", condition_effect(CS.MOOD_LIFT)), choice("decline_for_next_slot", "因为接下来的安排而婉拒", condition_effect(CS.STRESS_RELIEF)))),
    # 255 school_teacher_note_timing
    EventDefinition(event_id="school_teacher_note_timing", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=I, base_probability=.11, priority=20, cooldown_days=10, eligibility=all_of(in_school, free_slot), director_brief="An ordinary school notice is introduced by the event.", choices=(choice("acknowledge_school_note", "现在确认这条学校通知"), choice("review_after_company", "等公司安排结束后再看"))),
)
