from core.event_definition import EventDefinition
from core.models import CompanyCourse as CC, ConditionSignal as CS
from core.events.common import (
    CONDITIONAL, I, L, MAJOR, MINOR, N, OPPORTUNITY, P, ROSTER,
    SCHEDULED, STAFF, TEACHER, TRAINEE, all_of, bound_relationship,
    choice, company_course, company_skill_course, company_slot,
    completed_slot_has_skill_result, condition_any, condition_effect,
    condition_range, current_course_skill_value_at_least, month_end_within,
    roster_has, slot_index, teacher_matches_course, trainee_day_at_least,
)


RARE_EVENTS = (
    # 286 rare_showcase_room_layout
    EventDefinition(event_id="rare_showcase_room_layout", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.06, priority=30, cooldown_days=21, eligibility=all_of(company_course(CC.STAGE), trainee_day_at_least(14)), director_brief="The event announces a small internal practice showcase and a different room layout."),
    # 287 rare_showcase_rehearsal_order
    EventDefinition(event_id="rare_showcase_rehearsal_order", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.10, priority=30, cooldown_days=14, eligibility=company_course(CC.STAGE), director_brief="A rehearsal order for a small internal showcase exercise is posted."),
    # 288 rare_showcase_other_group_run
    EventDefinition(event_id="rare_showcase_other_group_run", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.08, priority=30, eligibility=all_of(company_course(CC.STAGE), roster_has(TRAINEE)), director_brief="Another roster group completes a steady internal rehearsal run."),
    # 289 rare_showcase_empty_stage_nerves
    EventDefinition(event_id="rare_showcase_empty_stage_nerves", category=CONDITIONAL, trigger_mode=P, tier=MAJOR, interaction_mode=N, base_probability=.07, priority=50, cooldown_days=21, eligibility=all_of(company_course(CC.STAGE), condition_range("stress", 0, 94)), effects=(condition_effect(CS.STRESS_INCREASE),), director_brief="An internal empty-stage spacing check introduced by the event feels real."),
    # 290 rare_evaluation_late_practice_atmosphere
    EventDefinition(event_id="rare_evaluation_late_practice_atmosphere", category=CONDITIONAL, trigger_mode=P, tier=MAJOR, interaction_mode=N, base_probability=.08, priority=50, cooldown_days=14, eligibility=all_of(month_end_within(7), slot_index(7), roster_has(TRAINEE)), director_brief="More roster trainees remain in the building late before evaluation."),
    # 291 rare_evaluation_teacher_observation_day
    EventDefinition(event_id="rare_evaluation_teacher_observation_day", category=CONDITIONAL, trigger_mode=P, tier=MAJOR, interaction_mode=N, base_probability=.06, priority=50, cooldown_days=21, eligibility=all_of(month_end_within(7), roster_has(TEACHER), company_slot), director_brief="Roster teachers circulate through practice rooms more often than usual."),
    # 292 rare_evaluation_rest_or_review_choice
    EventDefinition(event_id="rare_evaluation_rest_or_review_choice", category=CONDITIONAL, trigger_mode=L, tier=MAJOR, interaction_mode=I, base_probability=.28, priority=50, cooldown_days=21, eligibility=all_of(month_end_within(3), condition_any(condition_range("stress", 50), condition_range("muscle_fatigue", 50))), director_brief="The event introduces a final short gap before an internal check.", choices=(choice("use_gap_to_settle", "利用空档让自己平静下来", condition_effect(CS.STRESS_RELIEF)), choice("review_prepared_section", "再过一遍准备好的部分", condition_effect(CS.CONFIDENCE_GAIN)))),
    # 293 rare_evaluation_feedback_window
    EventDefinition(event_id="rare_evaluation_feedback_window", category=OPPORTUNITY, trigger_mode=L, tier=MAJOR, interaction_mode=I, base_probability=.24, priority=50, once=True, context_npc_source=ROSTER, context_npc_role=TEACHER, eligibility=all_of(month_end_within(7), company_slot, teacher_matches_course), director_brief="The selected teacher opens a short feedback window.", choices=(choice("ask_concrete_question", "问一个具体的问题", condition_effect(CS.CONFIDENCE_GAIN)), choice("preserve_focus", "不再分心，按原计划继续", condition_effect(CS.STRESS_RELIEF)))),
    # 294 rare_group_task_role_preference
    EventDefinition(event_id="rare_group_task_role_preference", category=OPPORTUNITY, trigger_mode=L, tier=MAJOR, interaction_mode=I, base_probability=.26, priority=50, once=True, context_npc_source=ROSTER, context_npc_role=STAFF, eligibility=company_course(CC.STAGE, CC.CAMERA), director_brief="The selected staff member introduces a one-off internal group task and asks for preference.", choices=(choice("volunteer_visible_role", "主动选择更显眼的位置", condition_effect(CS.CONFIDENCE_GAIN)), choice("prefer_support_role", "选择更偏辅助的位置", condition_effect(CS.STRESS_RELIEF)))),
    # 295 rare_group_task_extra_rehearsal
    EventDefinition(event_id="rare_group_task_extra_rehearsal", category=OPPORTUNITY, trigger_mode=L, tier=MAJOR, interaction_mode=I, base_probability=.26, priority=50, once=True, context_npc_source=ROSTER, context_npc_role=TRAINEE, eligibility=all_of(company_course(CC.STAGE), bound_relationship(tension_max=69)), director_brief="For a one-off internal group exercise introduced by the event, the selected trainee proposes one extra run.", choices=(choice("join_extra_rehearsal", "参加这一次额外排练", condition_effect(CS.CONFIDENCE_GAIN)), choice("keep_schedule", "不加练，保持原定安排", condition_effect(CS.STRESS_RELIEF)))),
    # 296 rare_group_task_switch_position
    EventDefinition(event_id="rare_group_task_switch_position", category=OPPORTUNITY, trigger_mode=L, tier=MAJOR, interaction_mode=I, base_probability=.24, priority=50, once=True, context_npc_source=ROSTER, context_npc_role=STAFF, eligibility=all_of(company_skill_course, current_course_skill_value_at_least(0)), director_brief="In a temporary drill introduced by the event, the selected staff member says one position needs coverage.", choices=(choice("offer_to_cover", "主动顶上这个位置", condition_effect(CS.CONFIDENCE_GAIN)), choice("let_staff_reassign", "让工作人员重新安排", condition_effect(CS.STRESS_INCREASE)))),
    # 297 rare_group_task_review_clip
    EventDefinition(event_id="rare_group_task_review_clip", category=OPPORTUNITY, trigger_mode=L, tier=MAJOR, interaction_mode=I, base_probability=.26, priority=50, once=True, context_npc_source=ROSTER, context_npc_role=TRAINEE, eligibility=company_course(CC.CAMERA, CC.STAGE), director_brief="The event introduces a short internal practice clip, which the selected trainee reviews with the player.", choices=(choice("review_coordination", "先看整体配合", condition_effect(CS.STRESS_RELIEF)), choice("review_own_execution", "先看自己的完成情况", condition_effect(CS.CONFIDENCE_GAIN)))),
    # 298 rare_observation_internal_camera_run
    EventDefinition(event_id="rare_observation_internal_camera_run", category=OPPORTUNITY, trigger_mode=P, tier=MAJOR, interaction_mode=I, base_probability=.06, priority=50, once=True, context_npc_source=ROSTER, context_npc_role=STAFF, eligibility=company_course(CC.CAMERA, CC.STAGE), director_brief="The selected staff member introduces an internal camera run with one practice position.", choices=(choice("take_practice_position", "参加这一遍练习录制", condition_effect(CS.CONFIDENCE_GAIN)), choice("observe_this_run", "先在旁边观察这一遍", condition_effect(CS.STRESS_RELIEF)))),
    # 299 rare_observation_teacher_full_run
    EventDefinition(event_id="rare_observation_teacher_full_run", category=OPPORTUNITY, trigger_mode=P, tier=MAJOR, interaction_mode=I, base_probability=.06, priority=50, once=True, context_npc_source=ROSTER, context_npc_role=TEACHER, eligibility=all_of(company_skill_course, teacher_matches_course), director_brief="The selected teacher offers one observed full internal practice run.", choices=(choice("do_observed_run", "现在就完成这次完整展示", condition_effect(CS.CONFIDENCE_GAIN)), choice("use_later_review", "改到之后的常规反馈时间", condition_effect(CS.STRESS_RELIEF)))),
    # 300 rare_recording_internal_reference_take
    EventDefinition(event_id="rare_recording_internal_reference_take", category=OPPORTUNITY, trigger_mode=P, tier=MAJOR, interaction_mode=I, base_probability=.05, priority=50, once=True, context_npc_source=ROSTER, context_npc_role=STAFF, eligibility=completed_slot_has_skill_result, director_brief="The selected staff member introduces a non-commercial reference take.", choices=(choice("record_reference_take", "参加这次内部参考录制", condition_effect(CS.CONFIDENCE_GAIN)), choice("remain_backup", "先作为候补待命", condition_effect(CS.STRESS_RELIEF)))),
)
