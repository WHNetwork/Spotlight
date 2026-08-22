from core.event_definition import EventDefinition
from core.models import CompanyCourse as CC, ConditionSignal as CS
from core.events.common import (
    CONDITIONAL, I, L, MINOR, N, OPPORTUNITY, P, ROSTER, SCHEDULED,
    STAFF, TEACHER, TRAINEE, all_of, choice, company_course,
    company_skill_course, company_slot, condition_effect, condition_range,
    current_course_skill_value_at_least, free_slot, roster_has,
    slot_index_below, teacher_matches_course,
)


COMPANY_OR_FREE = lambda context: company_slot(context) or free_slot(context)


TEACHER_STAFF_EVENTS = (
    # 126 teacher_feedback_single_correction
    EventDefinition(event_id="teacher_feedback_single_correction", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.20, priority=10, context_npc_source=ROSTER, context_npc_role=TEACHER, eligibility=all_of(company_slot, teacher_matches_course), director_brief="The selected teacher repeats one technical correction to the player."),
    # 127 teacher_feedback_specific_reassurance
    EventDefinition(event_id="teacher_feedback_specific_reassurance", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.16, priority=10, context_npc_source=ROSTER, context_npc_role=TEACHER, eligibility=all_of(company_slot, teacher_matches_course), effects=(condition_effect(CS.CONFIDENCE_GAIN),), director_brief="The selected teacher frames one correction as manageable with repetition."),
    # 128 teacher_feedback_group_pattern
    EventDefinition(event_id="teacher_feedback_group_pattern", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.20, priority=10, eligibility=all_of(company_skill_course, roster_has(TEACHER)), director_brief="The class instructor addresses a pattern several trainees share."),
    # 129 teacher_feedback_no_comment
    EventDefinition(event_id="teacher_feedback_no_comment", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.15, priority=10, eligibility=all_of(company_skill_course, roster_has(TEACHER)), director_brief="The class ends without individual feedback for the player."),
    # 130 teacher_feedback_brief_critique_stings
    EventDefinition(event_id="teacher_feedback_brief_critique_stings", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.13, priority=10, context_npc_source=ROSTER, context_npc_role=TEACHER, eligibility=all_of(company_slot, teacher_matches_course, condition_range("confidence", 0, 69)), effects=(condition_effect(CS.CONFIDENCE_HIT),), director_brief="A concise critique from the selected teacher lands sharply."),
    # 131 teacher_feedback_example_from_another
    EventDefinition(event_id="teacher_feedback_example_from_another", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.17, priority=10, eligibility=all_of(company_course(CC.DANCE, CC.STAGE, CC.CAMERA, CC.FITNESS), roster_has(TEACHER), roster_has(TRAINEE)), director_brief="Another trainee is asked to demonstrate the corrected movement or phrase."),
    # 132 teacher_feedback_question_deferred
    EventDefinition(event_id="teacher_feedback_question_deferred", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, context_npc_source=ROSTER, context_npc_role=TEACHER, eligibility=all_of(company_slot, teacher_matches_course), director_brief="The selected teacher asks the player to finish the run before the question."),
    # 133 teacher_feedback_written_note
    EventDefinition(event_id="teacher_feedback_written_note", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.12, priority=10, context_npc_source=ROSTER, context_npc_role=TEACHER, eligibility=all_of(company_slot, teacher_matches_course), director_brief="The selected teacher leaves one short cue for the player's next repetition."),
    # 134 teacher_feedback_progress_neutral
    EventDefinition(event_id="teacher_feedback_progress_neutral", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.10, priority=10, context_npc_source=ROSTER, context_npc_role=TEACHER, eligibility=all_of(company_slot, teacher_matches_course, current_course_skill_value_at_least(11)), director_brief="The selected teacher notes one basic issue occurring less often in this run."),
    # 135 teacher_instruction_demo_change
    EventDefinition(event_id="teacher_instruction_demo_change", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.18, priority=10, eligibility=all_of(company_skill_course, roster_has(TEACHER)), director_brief="The class instructor changes the order of demonstration and practice."),
    # 136 teacher_instruction_slower_breakdown
    EventDefinition(event_id="teacher_instruction_slower_breakdown", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.18, priority=10, context_npc_source=ROSTER, context_npc_role=TEACHER, eligibility=all_of(company_slot, teacher_matches_course), director_brief="The selected teacher breaks one section into smaller steps for the player."),
    # 137 teacher_instruction_fewer_words
    EventDefinition(event_id="teacher_instruction_fewer_words", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.15, priority=10, context_npc_source=ROSTER, context_npc_role=TEACHER, eligibility=all_of(company_course(CC.DANCE, CC.STAGE, CC.CAMERA, CC.FITNESS), teacher_matches_course), director_brief="The selected teacher demonstrates again with little verbal explanation."),
    # 138 teacher_instruction_tempo_relief
    EventDefinition(event_id="teacher_instruction_tempo_relief", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.16, priority=10, context_npc_source=ROSTER, context_npc_role=TEACHER, eligibility=all_of(company_course(CC.DANCE, CC.VOCAL, CC.RAP, CC.STAGE, CC.FITNESS), teacher_matches_course, condition_range("stress", 35)), effects=(condition_effect(CS.STRESS_RELIEF),), director_brief="The selected teacher reduces the tempo for the player's review run."),
    # 139 teacher_instruction_peer_observation
    EventDefinition(event_id="teacher_instruction_peer_observation", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.13, priority=10, eligibility=all_of(company_skill_course, roster_has(TEACHER), roster_has(TRAINEE)), director_brief="The class briefly observes another roster group's run before continuing."),
    # 140 teacher_instruction_question_round
    EventDefinition(event_id="teacher_instruction_question_round", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, context_npc_source=ROSTER, context_npc_role=TEACHER, eligibility=all_of(company_slot, teacher_matches_course), director_brief="The selected teacher gives the player room for one brief question."),
    # 141 teacher_instruction_example_swap
    EventDefinition(event_id="teacher_instruction_example_swap", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, cooldown_days=3, context_npc_source=ROSTER, context_npc_role=TEACHER, eligibility=all_of(company_slot, teacher_matches_course), director_brief="The selected teacher replaces an example that did not clarify the point."),
    # 142 teacher_discipline_start_line
    EventDefinition(event_id="teacher_discipline_start_line", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.15, priority=10, cooldown_days=5, context_npc_source=ROSTER, context_npc_role=TEACHER, eligibility=all_of(company_slot, teacher_matches_course), director_brief="The selected teacher restates the start-time rule to the player and nearby class."),
    # 143 staff_reminder_room_cleanup
    EventDefinition(event_id="staff_reminder_room_cleanup", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.18, priority=10, cooldown_days=4, eligibility=all_of(company_slot, roster_has(STAFF)), director_brief="A posted staff reminder asks trainees to reset the room after use."),
    # 144 teacher_reminder_phone_silence
    EventDefinition(event_id="teacher_reminder_phone_silence", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.13, priority=10, cooldown_days=7, context_npc_source=ROSTER, context_npc_role=TEACHER, eligibility=all_of(company_slot, teacher_matches_course), director_brief="The selected teacher reminds the player to keep the phone silent."),
    # 145 teacher_reminder_focus_pressure
    EventDefinition(event_id="teacher_reminder_focus_pressure", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, cooldown_days=5, context_npc_source=ROSTER, context_npc_role=TEACHER, eligibility=all_of(company_slot, teacher_matches_course, condition_range("stress", 0, 94)), effects=(condition_effect(CS.STRESS_INCREASE),), director_brief="A focus reminder from the selected teacher feels slightly tense."),
    # 146 staff_reminder_label_belongings
    EventDefinition(event_id="staff_reminder_label_belongings", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.11, priority=10, cooldown_days=10, context_npc_source=ROSTER, context_npc_role=STAFF, eligibility=COMPANY_OR_FREE, director_brief="The selected staff member reminds the player to label personal practice items."),
    # 147 teacher_reminder_water_break_end
    EventDefinition(event_id="teacher_reminder_water_break_end", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.16, priority=10, cooldown_days=4, context_npc_source=ROSTER, context_npc_role=TEACHER, eligibility=all_of(company_slot, teacher_matches_course), director_brief="The selected teacher calls the player back when the water break ends."),
    # 148 staff_reminder_hallway_clear
    EventDefinition(event_id="staff_reminder_hallway_clear", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, cooldown_days=6, context_npc_source=ROSTER, context_npc_role=STAFF, eligibility=COMPANY_OR_FREE, director_brief="The selected staff member asks the player to keep a hallway clear."),
    # 149 teacher_grouping_rotation
    EventDefinition(event_id="teacher_grouping_rotation", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.18, priority=10, cooldown_days=3, context_npc_source=ROSTER, context_npc_role=TEACHER, eligibility=all_of(company_skill_course, teacher_matches_course), director_brief="The selected teacher assigns the player to a temporary practice rotation."),
    # 150 teacher_grouping_size_change
    EventDefinition(event_id="teacher_grouping_size_change", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.17, priority=10, cooldown_days=4, context_npc_source=ROSTER, context_npc_role=TEACHER, eligibility=all_of(company_skill_course, teacher_matches_course), director_brief="The selected teacher adjusts the player's temporary practice group size."),
    # 151 staff_coordination_room_turnover
    EventDefinition(event_id="staff_coordination_room_turnover", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.16, priority=10, cooldown_days=4, eligibility=all_of(company_slot, roster_has(STAFF)), director_brief="A quick room turnover between users occurs after the slot."),
    # 152 teacher_grouping_observer_round
    EventDefinition(event_id="teacher_grouping_observer_round", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.15, priority=10, cooldown_days=3, context_npc_source=ROSTER, context_npc_role=TEACHER, eligibility=all_of(company_skill_course, teacher_matches_course), director_brief="The selected teacher assigns one observation round before the player's next run."),
    # 153 staff_coordination_delay_stress
    EventDefinition(event_id="staff_coordination_delay_stress", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.12, priority=10, cooldown_days=5, eligibility=all_of(slot_index_below(7), roster_has(STAFF), condition_range("stress", 0, 94)), effects=(condition_effect(CS.STRESS_INCREASE),), director_brief="A minor coordination delay compresses the transition to the next slot."),
    # 154 teacher_grouping_absence_fill
    EventDefinition(event_id="teacher_grouping_absence_fill", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.11, priority=10, cooldown_days=7, context_npc_source=ROSTER, context_npc_role=TEACHER, eligibility=all_of(company_skill_course, teacher_matches_course, roster_has(TRAINEE)), director_brief="The selected teacher adjusts positions because one roster trainee is absent from this run."),
    # 155 staff_admin_id_check
    EventDefinition(event_id="staff_admin_id_check", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.09, priority=10, cooldown_days=14, context_npc_source=ROSTER, context_npc_role=STAFF, eligibility=company_slot, director_brief="The selected staff member conducts a routine trainee ID check."),
    # 156 staff_admin_schedule_acknowledgment
    EventDefinition(event_id="staff_admin_schedule_acknowledgment", category=SCHEDULED, trigger_mode=L, tier=MINOR, interaction_mode=I, base_probability=.40, priority=20, cooldown_days=10, context_npc_source=ROSTER, context_npc_role=STAFF, eligibility=company_slot, director_brief="The selected staff member presents a minor schedule note for acknowledgment.", choices=(choice("acknowledge_immediately", "直接确认收到"), choice("read_before_acknowledging", "先看清内容再确认"))),
    # 157 teacher_optional_short_review
    EventDefinition(event_id="teacher_optional_short_review", category=OPPORTUNITY, trigger_mode=L, tier=MINOR, interaction_mode=I, base_probability=.40, priority=20, cooldown_days=7, context_npc_source=ROSTER, context_npc_role=TEACHER, eligibility=all_of(company_slot, teacher_matches_course), director_brief="The selected teacher offers the player one short review window.", choices=(choice("use_review_question", "趁现在问一个问题"), choice("leave_window_to_others", "把这次机会留给其他人"))),
    # 158 staff_equipment_return_timing
    EventDefinition(event_id="staff_equipment_return_timing", category=CONDITIONAL, trigger_mode=L, tier=MINOR, interaction_mode=I, base_probability=.38, priority=20, cooldown_days=8, context_npc_source=ROSTER, context_npc_role=STAFF, eligibility=company_course(CC.CAMERA, CC.STAGE, CC.FITNESS), director_brief="The selected staff member confirms return timing for equipment used in the scene.", choices=(choice("return_equipment_now", "现在就归还设备"), choice("keep_until_deadline", "按规定时间再归还"))),
    # 159 teacher_makeup_instruction_offer
    EventDefinition(event_id="teacher_makeup_instruction_offer", category=OPPORTUNITY, trigger_mode=L, tier=MINOR, interaction_mode=I, base_probability=.32, priority=20, cooldown_days=14, context_npc_source=ROSTER, context_npc_role=TEACHER, eligibility=all_of(company_slot, teacher_matches_course, condition_range("confidence", 0, 69)), director_brief="The selected teacher offers a brief follow-up explanation of the completed material.", choices=(choice("stay_for_explanation", "留下来听一下补充说明"), choice("use_notes_later", "之后自己看课堂笔记"))),
    # 160 staff_lost_item_handoff_choice
    EventDefinition(event_id="staff_lost_item_handoff_choice", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=I, base_probability=.13, priority=20, cooldown_days=10, context_npc_source=ROSTER, context_npc_role=STAFF, eligibility=COMPANY_OR_FREE, director_brief="A small found item appears in the scene and needs to be handed in.", choices=(choice("hand_to_staff", "直接交给这位工作人员"), choice("use_lost_item_point", "放到指定的失物招领处"))),
)
