from core.event_definition import EventDefinition
from core.models import CompanyCourse as CC, ConditionSignal as CS, FreeActionKind as FA, RelationshipSignal as RS
from core.events.common import (
    CONDITIONAL, D, I, L, MINOR, N, OPPORTUNITY, P, RELATIONSHIP,
    ROSTER, SCHEDULED, SLOT, STAFF, TRAINEE, all_of, bound_relationship,
    choice, company_course, company_slot, condition_effect, condition_range,
    free_action, month_end_exactly, month_end_within, relationship_effect,
    roster_has, slot_index, slot_index_below,
)


COMPANY_LIFE_EVENTS = (
    # 161 company_room_assignment_posted
    EventDefinition(event_id="company_room_assignment_posted", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.18, priority=10, eligibility=company_slot, director_brief="A practice-room assignment notice is posted after the slot."),
    # 162 company_room_crowding_pressure
    EventDefinition(event_id="company_room_crowding_pressure", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.18, priority=10, eligibility=all_of(company_slot, condition_range("stress", 0, 94)), effects=(condition_effect(CS.STRESS_INCREASE),), director_brief="The assigned room feels crowded during turnover."),
    # 163 company_room_quiet_corner
    EventDefinition(event_id="company_room_quiet_corner", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.15, priority=10, eligibility=company_slot, director_brief="A quiet corner remains available for a short review."),
    # 164 company_room_previous_group_lingers
    EventDefinition(event_id="company_room_previous_group_lingers", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, eligibility=company_slot, director_brief="A previous roster group takes a little longer to clear the room."),
    # 165 company_room_mirror_section_closed
    EventDefinition(event_id="company_room_mirror_section_closed", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.12, priority=10, eligibility=company_course(CC.DANCE, CC.STAGE), director_brief="One section of mirror space is temporarily unavailable."),
    # 166 company_room_airing_break
    EventDefinition(event_id="company_room_airing_break", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, eligibility=company_slot, director_brief="The room is briefly aired before the next group enters."),
    # 167 company_room_shared_booking
    EventDefinition(event_id="company_room_shared_booking", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.11, priority=10, eligibility=all_of(company_slot, roster_has(TRAINEE)), director_brief="Two ordinary practice uses share the same booking window."),
    # 168 company_schedule_minor_shift
    EventDefinition(event_id="company_schedule_minor_shift", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, eligibility=slot_index_below(7), director_brief="The next company schedule item shifts by a small amount."),
    # 169 company_schedule_shift_relief
    EventDefinition(event_id="company_schedule_shift_relief", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.13, priority=10, eligibility=all_of(slot_index_below(7), condition_range("stress", 35)), effects=(condition_effect(CS.STRESS_RELIEF),), director_brief="A small schedule delay leaves a less rushed transition."),
    # 170 company_assembly_wait
    EventDefinition(event_id="company_assembly_wait", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.16, priority=10, eligibility=all_of(company_slot, roster_has(TRAINEE)), director_brief="Trainees wait briefly for an assembly introduced by the event."),
    # 171 company_schedule_compare_with_trainee
    EventDefinition(event_id="company_schedule_compare_with_trainee", category=RELATIONSHIP, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.17, priority=10, context_npc_source=SLOT, context_npc_role=TRAINEE, eligibility=all_of(free_action(FA.SOCIAL), slot_index_below(7)), effects=(relationship_effect(RS.CASUAL_CONTACT),), director_brief="The player and selected SOCIAL trainee compare the next canonical slot."),
    # 172 company_assembly_seat_saved
    EventDefinition(event_id="company_assembly_seat_saved", category=RELATIONSHIP, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, context_npc_source=ROSTER, context_npc_role=TRAINEE, eligibility=all_of(company_slot, bound_relationship(familiarity_min=6)), effects=(relationship_effect(RS.RELIABILITY_CONFIRMED),), director_brief="The selected trainee keeps an ordinary nearby seat available."),
    # 173 company_schedule_empty_gap
    EventDefinition(event_id="company_schedule_empty_gap", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.15, priority=10, eligibility=slot_index_below(7), director_brief="A short gap appears before the next canonical slot."),
    # 174 company_assembly_roll_call
    EventDefinition(event_id="company_assembly_roll_call", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.13, priority=10, eligibility=all_of(company_slot, roster_has(TRAINEE)), director_brief="A routine roll call introduced by the event takes time."),
    # 175 company_notice_board_refresh
    EventDefinition(event_id="company_notice_board_refresh", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.12, priority=10, eligibility=company_slot, director_brief="Several ordinary notices are replaced on the company board."),
    # 176 company_notice_deadline_pressure
    EventDefinition(event_id="company_notice_deadline_pressure", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.13, priority=10, cooldown_days=5, eligibility=all_of(month_end_within(7), condition_range("stress", 0, 94)), effects=(condition_effect(CS.STRESS_INCREASE),), director_brief="A routine month-end administrative deadline feels close."),
    # 177 company_rule_food_area
    EventDefinition(event_id="company_rule_food_area", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.10, priority=10, cooldown_days=10, eligibility=company_slot, director_brief="A notice restates where food may be consumed."),
    # 178 company_notice_contact_update
    EventDefinition(event_id="company_notice_contact_update", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.08, priority=10, cooldown_days=14, eligibility=all_of(company_slot, roster_has(STAFF)), director_brief="An internal contact list is updated for routine coordination."),
    # 179 company_rule_recording_limit
    EventDefinition(event_id="company_rule_recording_limit", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.09, priority=10, cooldown_days=12, eligibility=company_course(CC.CAMERA, CC.STAGE), director_brief="A notice repeats limits on casual recording in practice areas."),
    # 180 company_notice_read_by_group
    EventDefinition(event_id="company_notice_read_by_group", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.15, priority=10, cooldown_days=5, eligibility=all_of(company_slot, roster_has(TRAINEE)), director_brief="Several roster trainees pause at a notice introduced by the event."),
    # 181 company_equipment_inventory_check
    EventDefinition(event_id="company_equipment_inventory_check", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.10, priority=10, cooldown_days=7, eligibility=all_of(company_course(CC.CAMERA, CC.STAGE, CC.FITNESS), roster_has(STAFF)), director_brief="Staff check ordinary shared practice equipment after the slot."),
    # 182 company_equipment_battery_queue
    EventDefinition(event_id="company_equipment_battery_queue", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.12, priority=10, cooldown_days=5, eligibility=company_course(CC.CAMERA), director_brief="A brief queue forms for charged practice-device batteries."),
    # 183 company_wardrobe_basic_check_stress
    EventDefinition(event_id="company_wardrobe_basic_check_stress", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.11, priority=10, cooldown_days=8, eligibility=all_of(company_course(CC.STAGE, CC.CAMERA), condition_range("stress", 0, 94)), effects=(condition_effect(CS.STRESS_INCREASE),), director_brief="A basic practice-clothing check requires a small adjustment."),
    # 184 company_equipment_cable_replaced
    EventDefinition(event_id="company_equipment_cable_replaced", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.08, priority=10, cooldown_days=12, eligibility=all_of(company_course(CC.VOCAL, CC.RAP, CC.CAMERA, CC.STAGE), roster_has(STAFF)), director_brief="Staff replace a worn practice-room cable after the slot."),
    # 185 company_wardrobe_label_sort
    EventDefinition(event_id="company_wardrobe_label_sort", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.09, priority=10, cooldown_days=10, eligibility=all_of(company_course(CC.STAGE, CC.CAMERA), roster_has(STAFF)), director_brief="Basic internal-use garments present in the scene are re-sorted by label."),
    # 186 company_evaluation_calendar_visible
    EventDefinition(event_id="company_evaluation_calendar_visible", category=SCHEDULED, trigger_mode=D, tier=MINOR, interaction_mode=N, priority=20, cooldown_days=7, eligibility=all_of(company_slot, slot_index(0), month_end_exactly(7)), director_brief="The approaching internal evaluation date becomes prominent on the schedule."),
    # 187 company_evaluation_room_use_choice
    EventDefinition(event_id="company_evaluation_room_use_choice", category=CONDITIONAL, trigger_mode=L, tier=MINOR, interaction_mode=I, base_probability=.40, priority=20, cooldown_days=7, eligibility=all_of(month_end_within(7), company_slot), director_brief="Evaluation preparation creates a one-off room choice.", choices=(choice("use_smaller_room", "先用较小的练习室"), choice("wait_preferred_room", "等更合适的练习室空出来"))),
    # 188 company_internal_record_observe_choice
    EventDefinition(event_id="company_internal_record_observe_choice", category=OPPORTUNITY, trigger_mode=L, tier=MINOR, interaction_mode=I, base_probability=.34, priority=20, cooldown_days=12, eligibility=company_course(CC.CAMERA, CC.STAGE), director_brief="A routine internal practice recording starts nearby as the event fact.", choices=(choice("watch_one_take", "安静看一遍录制"), choice("continue_schedule", "继续按原计划行动"))),
    # 189 company_month_end_plan_choice
    EventDefinition(event_id="company_month_end_plan_choice", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=I, base_probability=.14, priority=20, cooldown_days=5, eligibility=all_of(month_end_within(7), free_action(FA.RECOVER, FA.PERSONAL)), director_brief="The completed free slot contains a short unscheduled gap.", choices=(choice("decompress", "利用这段空档放松一下", condition_effect(CS.STRESS_RELIEF)), choice("outline_priority", "列出一个最需要练习的重点", condition_effect(CS.CONFIDENCE_GAIN)))),
    # 190 company_schedule_clarification_choice
    EventDefinition(event_id="company_schedule_clarification_choice", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=I, base_probability=.12, priority=20, cooldown_days=8, context_npc_source=ROSTER, context_npc_role=STAFF, eligibility=company_slot, director_brief="A minor internal notice introduced by the event is unclear.", choices=(choice("ask_staff_now", "现在就问工作人员"), choice("verify_next_update", "等下一次通知再确认"))),
)
