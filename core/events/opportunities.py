from core.event_definition import EventDefinition
from core.models import CompanyCourse as CC, ConditionSignal as CS, SkillId as SK
from core.events.common import (
    I, L, MINOR, N, OPPORTUNITY, P, ROSTER, STAFF, TEACHER, TRAINEE,
    all_of, choice, company_course, company_skill_course, company_slot,
    completed_slot_skill_result_is, condition_effect, roster_has,
    teacher_matches_course,
)


SMALL_OPPORTUNITY_EVENTS = (
    # 271 opportunity_observe_adjacent_class
    EventDefinition(event_id="opportunity_observe_adjacent_class", category=OPPORTUNITY, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.12, priority=20, once=True, eligibility=company_slot, director_brief="The event opens permission to observe part of an adjacent internal class."),
    # 272 opportunity_observe_equipment_setup
    EventDefinition(event_id="opportunity_observe_equipment_setup", category=OPPORTUNITY, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.12, priority=10, once=True, eligibility=company_course(CC.CAMERA, CC.STAGE), director_brief="Staff begin an ordinary internal recording setup as the event fact."),
    # 273 opportunity_observe_group_review
    EventDefinition(event_id="opportunity_observe_group_review", category=OPPORTUNITY, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.11, priority=10, eligibility=all_of(company_course(CC.CAMERA, CC.STAGE), roster_has(TRAINEE)), director_brief="Another roster group begins reviewing an internal practice take."),
    # 274 opportunity_observe_teacher_demo
    EventDefinition(event_id="opportunity_observe_teacher_demo", category=OPPORTUNITY, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.10, priority=10, cooldown_days=7, eligibility=all_of(company_skill_course, roster_has(TEACHER)), effects=(condition_effect(CS.CONFIDENCE_GAIN),), director_brief="An additional general demonstration after the completed course clarifies a point."),
    # 275 opportunity_demo_guide_track_help
    EventDefinition(event_id="opportunity_demo_guide_track_help", category=OPPORTUNITY, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.10, priority=10, context_npc_source=ROSTER, context_npc_role=STAFF, eligibility=company_course(CC.VOCAL, CC.RAP), director_brief="The selected staff member asks for help with a simple internal guide-track task."),
    # 276 opportunity_demo_page_turn
    EventDefinition(event_id="opportunity_demo_page_turn", category=OPPORTUNITY, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.09, priority=10, cooldown_days=10, context_npc_source=ROSTER, context_npc_role=STAFF, eligibility=company_course(CC.STAGE, CC.CAMERA), director_brief="The selected staff member asks the player to handle a cue reference."),
    # 277 opportunity_demo_reference_check
    EventDefinition(event_id="opportunity_demo_reference_check", category=OPPORTUNITY, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.08, priority=10, cooldown_days=12, context_npc_source=ROSTER, context_npc_role=STAFF, eligibility=company_course(CC.VOCAL, CC.RAP, CC.CAMERA, CC.STAGE), director_brief="The selected staff member asks the player to verify one reference label."),
    # 278 opportunity_demo_extra_guide_choice
    EventDefinition(event_id="opportunity_demo_extra_guide_choice", category=OPPORTUNITY, trigger_mode=L, tier=MINOR, interaction_mode=I, base_probability=.32, priority=20, cooldown_days=14, context_npc_source=ROSTER, context_npc_role=STAFF, eligibility=completed_slot_skill_result_is(SK.VOCAL, SK.RAP), director_brief="The selected staff member offers one simple internal guide take.", choices=(choice("attempt_guide_take", "试录这一遍导唱", condition_effect(CS.CONFIDENCE_GAIN)), choice("remain_support_role", "继续做辅助工作", condition_effect(CS.STRESS_RELIEF)))),
    # 279 opportunity_camera_slate_choice
    EventDefinition(event_id="opportunity_camera_slate_choice", category=OPPORTUNITY, trigger_mode=L, tier=MINOR, interaction_mode=I, base_probability=.36, priority=20, cooldown_days=12, context_npc_source=ROSTER, context_npc_role=STAFF, eligibility=company_course(CC.CAMERA), director_brief="The selected staff member offers two simple camera support tasks.", choices=(choice("read_practice_slate", "负责读练习场记板"), choice("check_floor_marks", "帮忙确认地面标记"))),
    # 280 opportunity_camera_intro_test
    EventDefinition(event_id="opportunity_camera_intro_test", category=OPPORTUNITY, trigger_mode=L, tier=MINOR, interaction_mode=I, base_probability=.30, priority=20, once=True, context_npc_source=ROSTER, context_npc_role=TRAINEE, eligibility=company_course(CC.CAMERA), director_brief="A brief internal introduction test includes the selected trainee.", choices=(choice("try_short_introduction", "试一次简短自我介绍", condition_effect(CS.CONFIDENCE_GAIN)), choice("observe_trainee_first", "先看看那位练习生怎么做", condition_effect(CS.STRESS_RELIEF)))),
    # 281 opportunity_camera_mark_test
    EventDefinition(event_id="opportunity_camera_mark_test", category=OPPORTUNITY, trigger_mode=L, tier=MINOR, interaction_mode=I, base_probability=.30, priority=20, once=True, context_npc_source=ROSTER, context_npc_role=STAFF, eligibility=company_course(CC.CAMERA), director_brief="The selected staff member needs a floor-mark test or framing check.", choices=(choice("test_floor_mark", "亲自试一次站位标记"), choice("observe_framing", "改为帮忙观察取景"))),
    # 282 opportunity_camera_playback_question
    EventDefinition(event_id="opportunity_camera_playback_question", category=OPPORTUNITY, trigger_mode=L, tier=MINOR, interaction_mode=I, base_probability=.30, priority=20, once=True, context_npc_source=ROSTER, context_npc_role=TEACHER, eligibility=all_of(company_course(CC.CAMERA), teacher_matches_course), director_brief="The selected camera teacher permits one question after the completed course.", choices=(choice("ask_technical_question", "问一个技术问题", condition_effect(CS.CONFIDENCE_GAIN)), choice("note_playback_later", "先记下来，之后再复盘", condition_effect(CS.STRESS_RELIEF)))),
    # 283 opportunity_feedback_observation_slot
    EventDefinition(event_id="opportunity_feedback_observation_slot", category=OPPORTUNITY, trigger_mode=L, tier=MINOR, interaction_mode=I, base_probability=.28, priority=20, once=True, context_npc_source=ROSTER, context_npc_role=TEACHER, eligibility=all_of(company_slot, teacher_matches_course), director_brief="The selected teacher offers one brief observation slot.", choices=(choice("use_observation_slot", "现在就用这次观察机会"), choice("leave_for_later_cycle", "把机会留到之后"))),
    # 284 opportunity_task_material_sort
    EventDefinition(event_id="opportunity_task_material_sort", category=OPPORTUNITY, trigger_mode=P, tier=MINOR, interaction_mode=I, base_probability=.10, priority=20, once=True, context_npc_source=ROSTER, context_npc_role=STAFF, eligibility=company_slot, director_brief="The selected staff member offers two ordinary support tasks.", choices=(choice("sort_practice_materials", "整理练习材料"), choice("check_room_list", "核对练习室安排表"))),
    # 285 opportunity_task_extra_room_hour
    EventDefinition(event_id="opportunity_task_extra_room_hour", category=OPPORTUNITY, trigger_mode=P, tier=MINOR, interaction_mode=I, base_probability=.09, priority=20, once=True, eligibility=company_slot, director_brief="A practice room becomes available as the event fact.", choices=(choice("use_extra_hour", "用这一个小时集中复习", condition_effect(CS.CONFIDENCE_GAIN)), choice("decline_extra_hour", "不加练，按原计划结束", condition_effect(CS.STRESS_RELIEF)))),
)
