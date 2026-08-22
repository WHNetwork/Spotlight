from core.event_definition import EventDefinition
from core.models import ConditionSignal as CS, FreeActionKind as FA, RelationshipSignal as RS
from core.events.common import (
    CONDITIONAL, I, L, MINOR, N, P, RELATIONSHIP, ROSTER, SCHEDULED,
    TRAINEE, all_of, choice, condition_effect, condition_range, free_action,
    free_slot, relationship_effect, roster_has, slot_index, slot_index_below,
)


BREAK = free_action(FA.RECOVER, FA.PERSONAL)
PERSONAL_OR_LAST = lambda context: free_action(FA.PERSONAL)(context) or context.slot_index == 7


DAILY_LIFE_EVENTS = (
    # 191 daily_dorm_morning_alarm
    EventDefinition(event_id="daily_dorm_morning_alarm", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.16, priority=10, eligibility=slot_index(0), director_brief="The day began with an ordinary alarm and a quick departure routine."),
    # 192 daily_dorm_bedside_clutter
    EventDefinition(event_id="daily_dorm_bedside_clutter", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.16, priority=10, eligibility=all_of(slot_index(0), condition_range("mood", 0, 69)), effects=(condition_effect(CS.MOOD_HIT),), director_brief="A small patch of bedside clutter was irritating when noticed."),
    # 193 daily_dorm_laundry_timing
    EventDefinition(event_id="daily_dorm_laundry_timing", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.15, priority=10, eligibility=PERSONAL_OR_LAST, director_brief="Laundry timing has to be fitted around the canonical day schedule."),
    # 194 daily_dorm_shared_sink_wait
    EventDefinition(event_id="daily_dorm_shared_sink_wait", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.16, priority=10, eligibility=slot_index(0), director_brief="A brief wait formed at a shared sink before departure."),
    # 195 daily_dorm_bag_repack
    EventDefinition(event_id="daily_dorm_bag_repack", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.18, priority=10, eligibility=slot_index(0, 7), director_brief="The player repacks a practice bag introduced by the event."),
    # 196 daily_dorm_quiet_return
    EventDefinition(event_id="daily_dorm_quiet_return", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.13, priority=10, eligibility=slot_index(7), director_brief="A late return to the dorm is handled quietly."),
    # 197 daily_dorm_shared_cleanup
    EventDefinition(event_id="daily_dorm_shared_cleanup", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, eligibility=PERSONAL_OR_LAST, director_brief="A small shared area is tidied enough for the next morning."),
    # 198 daily_meal_regular_queue
    EventDefinition(event_id="daily_meal_regular_queue", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.18, priority=10, eligibility=BREAK, director_brief="A food queue encountered during the free slot moves slowly."),
    # 199 daily_meal_warm_food_lift
    EventDefinition(event_id="daily_meal_warm_food_lift", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.15, priority=10, eligibility=all_of(BREAK, condition_range("mood", 0, 69)), effects=(condition_effect(CS.MOOD_LIFT),), director_brief="An ordinary warm meal in the scene feels especially welcome."),
    # 200 daily_meal_menu_repeat
    EventDefinition(event_id="daily_meal_menu_repeat", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, eligibility=BREAK, director_brief="A familiar cafeteria option appears again during the free slot."),
    # 201 daily_meal_trainee_table_overlap
    EventDefinition(event_id="daily_meal_trainee_table_overlap", category=RELATIONSHIP, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.18, priority=10, context_npc_source=ROSTER, context_npc_role=TRAINEE, eligibility=BREAK, effects=(relationship_effect(RS.CASUAL_CONTACT),), director_brief="The selected trainee and player end up at the same meal table."),
    # 202 daily_drink_trainee_queue_turn
    EventDefinition(event_id="daily_drink_trainee_queue_turn", category=RELATIONSHIP, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.16, priority=10, context_npc_source=ROSTER, context_npc_role=TRAINEE, eligibility=BREAK, effects=(relationship_effect(RS.CASUAL_CONTACT),), director_brief="The selected trainee and player take turns at a crowded drink station."),
    # 203 daily_meal_trainee_tray_help
    EventDefinition(event_id="daily_meal_trainee_tray_help", category=RELATIONSHIP, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, context_npc_source=ROSTER, context_npc_role=TRAINEE, eligibility=BREAK, effects=(relationship_effect(RS.SHARED_POSITIVE_EXPERIENCE),), director_brief="The selected trainee makes enough tray space for the player."),
    # 204 daily_commute_departure_overlap
    EventDefinition(event_id="daily_commute_departure_overlap", category=RELATIONSHIP, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.18, priority=10, context_npc_source=ROSTER, context_npc_role=TRAINEE, eligibility=slot_index(7), effects=(relationship_effect(RS.CASUAL_CONTACT),), director_brief="The selected trainee and player leave along the same first part of the route."),
    # 205 daily_commute_weather_wait_together
    EventDefinition(event_id="daily_commute_weather_wait_together", category=RELATIONSHIP, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, context_npc_source=ROSTER, context_npc_role=TRAINEE, eligibility=slot_index(0, 7), effects=(relationship_effect(RS.SHARED_POSITIVE_EXPERIENCE),), director_brief="Light rain introduced by the event keeps the selected trainee and player waiting."),
    # 206 daily_commute_rush_pressure
    EventDefinition(event_id="daily_commute_rush_pressure", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.13, priority=10, eligibility=all_of(slot_index(0, 7), condition_range("stress", 0, 94)), effects=(condition_effect(CS.STRESS_INCREASE),), director_brief="A crowded transition introduced by the event feels rushed."),
    # 207 daily_commute_early_platform
    EventDefinition(event_id="daily_commute_early_platform", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.12, priority=10, eligibility=slot_index(0), director_brief="The player arrived slightly early and waited before entering."),
    # 208 daily_commute_light_rain_adjustment
    EventDefinition(event_id="daily_commute_light_rain_adjustment", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.13, priority=10, eligibility=slot_index(0, 7), director_brief="Light rain introduced by the event changes the walking pace."),
    # 209 daily_commute_missed_elevator
    EventDefinition(event_id="daily_commute_missed_elevator", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.15, priority=10, eligibility=slot_index(0, 7), director_brief="The elevator doors close just before the player reaches them."),
    # 210 daily_rest_area_unusually_quiet
    EventDefinition(event_id="daily_rest_area_unusually_quiet", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.16, priority=10, eligibility=free_slot, director_brief="A rest area introduced by the event is unusually quiet."),
    # 211 daily_rest_phone_family_message
    EventDefinition(event_id="daily_rest_phone_family_message", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, cooldown_days=5, eligibility=free_slot, director_brief="An ordinary family message arrives during the free slot."),
    # 212 daily_rest_group_chat_scroll
    EventDefinition(event_id="daily_rest_group_chat_scroll", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.18, priority=10, cooldown_days=3, eligibility=free_slot, director_brief="A group chat contains routine logistical updates during the free slot."),
    # 213 daily_rest_short_silence_relief
    EventDefinition(event_id="daily_rest_short_silence_relief", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.16, priority=10, cooldown_days=3, eligibility=all_of(BREAK, condition_range("stress", 35)), effects=(condition_effect(CS.STRESS_RELIEF),), director_brief="The player gets one uninterrupted quiet minute during the free slot."),
    # 214 daily_rest_unanswered_message
    EventDefinition(event_id="daily_rest_unanswered_message", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.12, priority=10, cooldown_days=4, eligibility=all_of(free_slot, slot_index_below(7)), director_brief="A non-urgent message remains unanswered when the next slot begins."),
    # 215 daily_rest_people_watching
    EventDefinition(event_id="daily_rest_people_watching", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.15, priority=10, cooldown_days=3, eligibility=all_of(BREAK, roster_has(TRAINEE)), director_brief="Roster trainees come and go through a rest area introduced by the event."),
    # 216 daily_errand_lost_small_item_choice
    EventDefinition(event_id="daily_errand_lost_small_item_choice", category=CONDITIONAL, trigger_mode=L, tier=MINOR, interaction_mode=I, base_probability=.38, priority=20, cooldown_days=10, eligibility=BREAK, director_brief="A small everyday item introduced by the event is temporarily missing.", choices=(choice("search_once_more", "再找一次"), choice("look_later", "先继续做事，之后再找"))),
    # 217 daily_errand_vending_choice
    EventDefinition(event_id="daily_errand_vending_choice", category=CONDITIONAL, trigger_mode=L, tier=MINOR, interaction_mode=I, base_probability=.46, priority=20, cooldown_days=5, eligibility=BREAK, director_brief="The free slot allows one small drink errand.", choices=(choice("get_drink", "去买点喝的", condition_effect(CS.MOOD_LIFT)), choice("keep_break_unstructured", "什么都不安排，随便休息", condition_effect(CS.STRESS_RELIEF)))),
    # 218 daily_errand_message_now_or_later
    EventDefinition(event_id="daily_errand_message_now_or_later", category=CONDITIONAL, trigger_mode=L, tier=MINOR, interaction_mode=I, base_probability=.44, priority=20, cooldown_days=6, eligibility=all_of(free_slot, slot_index_below(7)), director_brief="A non-urgent message introduced by the event can be answered now or later.", choices=(choice("reply_now", "现在简单回复一下"), choice("reply_after_schedule", "等今天的安排结束后再回复"))),
    # 219 daily_errand_queue_or_skip
    EventDefinition(event_id="daily_errand_queue_or_skip", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=I, base_probability=.16, priority=20, cooldown_days=4, eligibility=BREAK, director_brief="A short queue forms as the event begins.", choices=(choice("wait_in_queue", "排一会儿队", condition_effect(CS.MOOD_LIFT)), choice("skip_queue", "不排了，留点安静时间", condition_effect(CS.STRESS_RELIEF)))),
    # 220 daily_errand_return_for_item
    EventDefinition(event_id="daily_errand_return_for_item", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=I, base_probability=.12, priority=20, cooldown_days=7, eligibility=all_of(free_slot, slot_index_below(7)), director_brief="A small forgotten practice item is introduced by the event.", choices=(choice("go_back_now", "现在回去拿"), choice("use_substitute", "先找个能替代的东西用"))),
)
