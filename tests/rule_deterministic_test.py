from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.brand_contract_system import ensure_brand_contract_state, evaluate_brand_contract_system
from core.career_branch_system import ensure_career_branch_state, evaluate_career_branch_system
from core.company_system import ensure_company_profile, evaluate_company_system
from core.crisis import update_crises
from core.debut_system import (
    debut_readiness_score,
    evaluate_debut_system,
    hard_gate_passed,
    readiness_to_probability,
)
from core.ending_system import ensure_ending_state, evaluate_ending_system
from core.hierarchy_system import evaluate_hierarchy_system
from core.inner_life import evaluate_inner_life
from core.market_score_system import ensure_market_score_state, evaluate_market_score_system
from core.models import ActiveCrisis, GameState
from core.period_system import advance_period, evaluate_period_system
from core.progression_system import convert_growth_diff_to_progression
from core.relationship_system import evaluate_relationship_system, register_known_npc
from core.rules import apply_diff, base_diff_for_action, sanitize_suggested_diff, threshold_warnings
from core.safety_boundary import evaluate_safety_boundary
from core.schedule_system import evaluate_schedule_system
from core.school_family import evaluate_school_family
from core.skill_decay_system import ensure_skill_decay_state, evaluate_skill_decay_system
from core.social_context import evaluate_social_context
from core.systems import classify_turn, evaluate_all_systems
from core.time_system import advance_time, determine_turn_duration_days
from core.trainee_life_system import ensure_trainee_life_state, evaluate_trainee_life_system
from core.weekly_plan import compose_action_with_weekly_plan, normalize_weekly_plan_keys, weekly_plan_context, weekly_plan_options


def event_codes(events) -> set[str]:
    return {event.code for event in events}


def event_sources(events) -> set[str]:
    return {event.source_system for event in events}


def make_state(*, trainee: bool = True, age: int = 18) -> GameState:
    state = GameState()
    state.save_name = "deterministic-test"
    state.character = {
        "艺名": "测试角色",
        "年龄": age,
        "时间线": "练习生阶段" if trainee else "回归瓶颈期",
        "身份": "素人发掘练习生" if trainee else "已出道女团成员",
        "公司规模": "中型公司",
    }
    state.age_context["age"] = age
    state.age_context["is_minor"] = age < 18
    if trainee:
        state.current_stage = "练习生阶段"
        state.current_mainline = "初入公司"
        state.current_schedule = "月末考核准备"
    else:
        state.current_stage = "已出道爱豆阶段"
        state.current_mainline = "回归打歌期"
        state.current_schedule = "回归第一周打歌和彩排"
    ensure_trainee_life_state(state)
    ensure_market_score_state(state)
    ensure_brand_contract_state(state)
    ensure_career_branch_state(state)
    ensure_ending_state(state)
    return state


def make_idol_market_state() -> GameState:
    state = make_state(trainee=False, age=20)
    state.career.update({
        "舞蹈实力": 72,
        "声乐实力": 68,
        "RAP能力": 55,
        "舞台感染力": 76,
        "综艺感": 64,
        "语言能力": 62,
        "形象指数": 70,
        "演技潜力": 58,
        "创作能力": 50,
    })
    state.market.update({
        "话题度": 68,
        "品牌价值": 52,
        "韩国本土影响力": 48,
        "音源潜力": 64,
        "销量潜力": 70,
        "短视频传播力": 72,
    })
    state.fans.update({
        "个人粉丝数": 96000,
        "团体粉丝数": 420000,
        "团粉稳定度": 72,
        "唯粉规模": 32,
        "粉丝信任基础": 70,
        "站姐稳定度": 65,
        "路人好感": 62,
    })
    state.company.update({"资源池": 72, "资源倾斜度": 58, "主推指数": 54, "公司信任度": 65})
    state.comeback.update({"风格适配度": 72, "回归阶段": "打歌期"})
    return state


class ActivityDiffRulesTest(unittest.TestCase):
    def test_base_activity_diff_is_deterministic(self) -> None:
        state = make_state()
        diff = base_diff_for_action("我高强度加练舞蹈、声乐，练完后开直播回复粉丝。", state)

        self.assertEqual(diff["职业属性.舞蹈实力"], 1)
        self.assertEqual(diff["职业属性.声乐实力"], 1)
        self.assertEqual(diff["身体状态.体力"], -13)
        self.assertEqual(diff["身体状态.肌肉疲劳"], 5)
        self.assertEqual(diff["身体状态.嗓音状态"], -4)
        self.assertEqual(diff["粉丝与舆论.粉丝信任基础"], 2)
        self.assertEqual(diff["市场.话题度"], 1)
        self.assertEqual(diff["风险.私生风险"], 1)

    def test_apply_diff_maps_categories_and_clamps_delta(self) -> None:
        state = make_state()
        state.body["体力"] = 50
        state.commercial["代言数量"] = 0
        applied = apply_diff(
            state,
            {"身体状态.体力": -30, "商业资源.代言数量": 3, "未知.变量": 99},
            max_abs_delta=8,
        )

        self.assertEqual(state.body["体力"], 42)
        self.assertEqual(state.commercial["代言数量"], 3)
        self.assertEqual(applied["身体状态.体力"], (50, 42))
        self.assertNotIn("未知.变量", applied)

    def test_model_suggested_producer_gain_is_gated(self) -> None:
        state = make_state()
        state.career["创作能力"] = 20
        blocked = sanitize_suggested_diff(state, {"职业属性.制作人能力": 5}, "我表达自己想参与制作")
        self.assertNotIn("职业属性.制作人能力", blocked)

        state.career["创作能力"] = 50
        allowed = sanitize_suggested_diff(state, {"职业属性.制作人能力": 1}, "作品被采纳并参与概念会议")
        self.assertEqual(allowed["职业属性.制作人能力"], 1)

    def test_threshold_warnings_are_state_driven(self) -> None:
        state = make_state()
        state.body["体力"] = 18
        state.body["睡眠质量"] = 30
        state.body["伤病风险"] = 80
        state.mind["精神压力"] = 92
        state.company["公司满意度"] = 30

        warnings = threshold_warnings(state)
        self.assertTrue(any("体力低于 20" in item for item in warnings))
        self.assertTrue(any("睡眠质量低于 40" in item for item in warnings))
        self.assertTrue(any("伤病风险高于 75" in item for item in warnings))
        self.assertTrue(any("精神压力高于 90" in item for item in warnings))
        self.assertTrue(any("公司满意度低于 35" in item for item in warnings))


class TimeSlotAndScheduleRulesTest(unittest.TestCase):
    def test_trainee_weekly_plan_ui_contract_is_four_fixed_three_optional(self) -> None:
        state = make_state(trainee=True)
        context = weekly_plan_context(state)
        options = weekly_plan_options(state)
        selected = normalize_weekly_plan_keys(
            state,
            ["dance_extra", "vocal_extra", "creative_demo", "company_observe"],
        )
        action = compose_action_with_weekly_plan("我按本周计划推进。", state, selected)
        events, diff = evaluate_trainee_life_system(state, action)

        self.assertEqual(context["weekly_slots_total"], 7)
        self.assertEqual(context["mandatory_slots"], 4)
        self.assertEqual(context["free_slots"], 3)
        self.assertEqual(selected, ["dance_extra", "vocal_extra", "creative_demo"])
        self.assertTrue(any(option.key == "dance_extra" for option in options))
        self.assertIn("【本周安排】", action)
        self.assertIn("自选3/3格", action)
        self.assertNotIn("trainee_week_overbooked", event_codes(events))
        self.assertEqual(diff, {})

    def test_trainee_weekly_plan_plus_extra_action_can_overbook(self) -> None:
        state = make_state(trainee=True)
        selected = ["dance_extra", "vocal_extra", "creative_demo"]
        action = compose_action_with_weekly_plan("白天还要学校考试。", state, selected)
        events, diff = evaluate_trainee_life_system(state, action)

        self.assertIn("trainee_week_overbooked", event_codes(events))
        self.assertEqual(state.trainee_life["last_slot_usage"]["学校"], 1)
        self.assertEqual(diff["身体状态.体力"], -4)

    def test_idol_weekly_plan_ui_contract_is_two_fixed_five_optional(self) -> None:
        state = make_state(trainee=False)
        context = weekly_plan_context(state)
        selected = normalize_weekly_plan_keys(
            state,
            ["comeback_stage", "brand_magazine", "fan_work", "creative_work", "recovery", "maintenance_training"],
        )
        action = compose_action_with_weekly_plan("我按出道后的本周安排推进。", state, selected)
        events, diff = evaluate_trainee_life_system(state, action)

        self.assertEqual(context["weekly_slots_total"], 7)
        self.assertEqual(context["mandatory_slots"], 2)
        self.assertEqual(context["free_slots"], 5)
        self.assertEqual(selected, ["comeback_stage", "brand_magazine", "fan_work", "creative_work", "recovery"])
        self.assertIn("自选5/5格", action)
        self.assertNotIn("idol_week_overbooked", event_codes(events))
        self.assertEqual(diff, {})

    def test_trainee_slots_are_four_fixed_three_optional_and_overbook_costs_values(self) -> None:
        state = make_state(trainee=True)
        events, diff = evaluate_trainee_life_system(
            state,
            "白天学校考试，晚上高强度加练舞蹈声乐，还写demo、社交、观察公司。",
        )

        self.assertEqual(state.trainee_life["weekly_slots_total"], 7)
        self.assertEqual(state.trainee_life["mandatory_slots"], 4)
        self.assertEqual(state.trainee_life["free_slots"], 3)
        self.assertEqual(state.trainee_life["slot_stage"], "trainee")
        self.assertIn("trainee_week_overbooked", event_codes(events))
        self.assertEqual(diff["身体状态.体力"], -4)
        self.assertEqual(diff["身体状态.睡眠质量"], -3)
        self.assertEqual(diff["身体状态.伤病风险"], 2)
        self.assertEqual(diff["心理状态.精神压力"], 2)

    def test_idol_slots_are_two_fixed_five_optional_and_overbook_costs_values(self) -> None:
        state = make_state(trainee=False)
        events, diff = evaluate_trainee_life_system(
            state,
            "这一周打歌彩排、拍品牌广告和杂志封面、直播营业、录音创作、维持训练、治疗休息。",
        )

        self.assertEqual(state.trainee_life["weekly_slots_total"], 7)
        self.assertEqual(state.trainee_life["mandatory_slots"], 2)
        self.assertEqual(state.trainee_life["free_slots"], 5)
        self.assertEqual(state.trainee_life["slot_stage"], "idol")
        self.assertIn("idol_week_overbooked", event_codes(events))
        self.assertEqual(diff["身体状态.体力"], -4)
        self.assertEqual(diff["身体状态.睡眠质量"], -2)
        self.assertEqual(diff["心理状态.职业倦怠"], 3)
        self.assertEqual(diff["风险.私生风险"], 1)

    def test_schedule_mode_enters_and_exits_stage_modes(self) -> None:
        state = make_state(trainee=False)
        state.schedule_profile["stage_mode"] = "trainee"
        state.current_mainline = "团体活动空窗期"
        state.current_schedule = "个人资源和维持训练"

        events, _ = evaluate_schedule_system(state, "出道后空窗期，我安排个人资源会议、维持训练和休息。")

        self.assertEqual(state.schedule_profile["stage_mode"], "idol_offseason")
        self.assertIn("schedule_mode_changed", event_codes(events))

    def test_turn_routing_is_rule_based(self) -> None:
        trainee = make_state(trainee=True)
        idol = make_state(trainee=False)

        self.assertEqual(classify_turn("我想正式solo出个人专辑", trainee).turn_kind, "focus")
        self.assertEqual(classify_turn("我想正式solo出个人专辑", idol).turn_kind, "mainline")
        self.assertEqual(classify_turn("热搜造谣后我回应澄清", idol).turn_kind, "crisis")
        self.assertEqual(classify_turn("我整理宿舍然后休息", idol).turn_kind, "ordinary")

    def test_time_advance_can_enter_monthly_evaluation(self) -> None:
        state = make_state(trainee=True)
        state.time["next_evaluation_days"] = 3
        route = classify_turn("周总结：练习月末考核曲", state)

        events, diff, days = advance_time(state, route, "周总结：练习月末考核曲")

        self.assertEqual(days, 7)
        self.assertEqual(state.time["days_elapsed"], 7)
        self.assertIn("time_monthly_evaluation_due", event_codes(events))
        self.assertEqual(diff["公司与合约.危机关注度"], 1)

    def test_weekly_plan_keeps_focus_turn_at_one_week(self) -> None:
        state = make_state(trainee=True)
        selected = ["dance_extra", "vocal_extra", "creative_demo"]
        action = compose_action_with_weekly_plan("我准备demo和月末考核重点展示。", state, selected)
        route = classify_turn(action, state)

        self.assertEqual(route.turn_kind, "focus")
        self.assertEqual(determine_turn_duration_days(route, action), 7)

        events, _, days = advance_time(state, route, action)
        self.assertEqual(days, 7)
        self.assertEqual(state.time["turn_duration_days"], 7)
        self.assertEqual(state.time["days_elapsed"], 7)
        self.assertIn("time_advanced", event_codes(events))


class StateEntryExitRulesTest(unittest.TestCase):
    def test_debut_hard_gate_blocks_low_ability(self) -> None:
        state = make_state(trainee=True)
        state.career.update({"舞蹈实力": 20, "声乐实力": 18, "舞台感染力": 16})

        passed, reasons = hard_gate_passed(state)
        events, _ = evaluate_debut_system(state, "我参加月末考核，想进入出道组候选。")

        self.assertFalse(passed)
        self.assertTrue(any("至少两项需要达到 35" in item for item in reasons))
        self.assertEqual(state.debut["status"], "not_ready")
        self.assertEqual(state.debut["probability"], 0)
        self.assertIn("debut_not_ready", event_codes(events))

    def test_debut_readiness_probability_and_window_entry_are_deterministic(self) -> None:
        state = make_state(trainee=True)
        state.career.update({"舞蹈实力": 58, "声乐实力": 55, "RAP能力": 44, "舞台感染力": 60, "形象指数": 52, "语言能力": 48})
        state.company.update({"公司信任度": 78, "资源池": 76, "出道窗口压力": 72, "资源倾斜度": 58})
        state.team["团队默契度"] = 72
        state.body.update({"体力": 78, "伤病风险": 18, "嗓音状态": 76})
        state.mind["精神压力"] = 42
        state.fans["个人粉丝数"] = 60000

        readiness = debut_readiness_score(state)
        probability = readiness_to_probability(readiness)
        events, diff = evaluate_debut_system(state, "季度评估后，公司会议讨论我是否进入出道组候选。")

        self.assertGreaterEqual(readiness, 50)
        self.assertGreater(probability, 0)
        self.assertIn(state.debut["status"], {"confirmed", "candidate_deferred"})
        self.assertEqual(state.debut["window_turns_left"], 8)
        self.assertEqual(state.debut["candidate_attempts"], 1)
        if state.debut["status"] == "confirmed":
            self.assertIn("debut_confirmed", event_codes(events))
            self.assertEqual(state.current_stage, "出道准备期")
            self.assertEqual(diff["公司与合约.主推指数"], 8)
        else:
            self.assertIn("debut_deferred", event_codes(events))
            self.assertEqual(diff["心理状态.精神压力"], 3)

    def test_debut_candidate_window_exits_by_countdown(self) -> None:
        state = make_state(trainee=True)
        state.debut["status"] = "candidate_deferred"
        state.debut["window_turns_left"] = 3

        events, diff = evaluate_debut_system(state, "我只整理反馈和休息。")

        self.assertEqual(events, [])
        self.assertEqual(diff, {})
        self.assertEqual(state.debut["window_turns_left"], 2)

    def test_active_crisis_blocks_debut_gate(self) -> None:
        state = make_state(trainee=True)
        state.career.update({"舞蹈实力": 45, "声乐实力": 42, "舞台感染力": 48})
        state.company["公司信任度"] = 66
        state.body["体力"] = 78
        state.body["伤病风险"] = 18
        state.mind["精神压力"] = 42
        state.active_crises.append(ActiveCrisis(crisis_id="pr", crisis_type="public_relations", title="舆论回应窗口", stage="response_window"))

        passed, reasons = hard_gate_passed(state)
        events, _ = evaluate_debut_system(state, "季度评估后，公司会议讨论我是否进入出道组候选。")

        self.assertFalse(passed)
        self.assertTrue(any("重大危机" in item for item in reasons))
        self.assertEqual(state.debut["status"], "not_ready")
        self.assertIn("debut_not_ready", event_codes(events))

    def test_crisis_can_open_close_convert_and_expire_status_effect(self) -> None:
        state = make_state(trainee=False)
        events, _ = evaluate_all_systems(state, "热搜造谣后我回应、澄清、声明。")
        crisis_events, _ = update_crises(state, "热搜造谣后我回应、澄清、声明。", events)

        self.assertTrue(any(c.crisis_type == "public_relations" for c in state.active_crises))
        self.assertEqual(crisis_events, [])

        state.active_crises = [ActiveCrisis(crisis_id="low", crisis_type="public_relations", title="旧视频热搜争议", stage="aftermath", heat=20, duration=2)]
        closed_events, _ = update_crises(state, "我保持低调，不再刺激舆论。", [])
        self.assertEqual(state.active_crises[0].stage, "closed")
        self.assertIn("crisis_closed_public_relations", event_codes(closed_events))

        state.active_crises = [ActiveCrisis(crisis_id="hot", crisis_type="public_relations", title="旧视频热搜争议", stage="response_window", heat=58, duration=4, failure_flag="舆论处理留下长期阴影")]
        converted_events, _ = update_crises(state, "我沉默、算了、装没事。", [])
        self.assertEqual(state.active_crises[0].stage, "converted")
        self.assertIn("crisis_converted_public_relations", event_codes(converted_events))
        self.assertIn("舆论处理留下长期阴影", state.flags)

        state.status_effects["强制休养"] = 1
        expired_events, _ = update_crises(state, "我休息。", [])
        self.assertNotIn("强制休养", state.status_effects)
        self.assertIn("status_effect_expired_强制休养", event_codes(expired_events))

    def test_ending_window_entry_or_resolution_is_status_driven(self) -> None:
        state = make_idol_market_state()
        state.turn = 156
        state.company["个人议价权"] = 88
        state.market["品牌价值"] = 88
        state.fans["个人粉丝数"] = 300000
        state.career["舞台感染力"] = 88

        events, _ = evaluate_ending_system(state, "续约期我考虑演员转型、solo和是否继续团体活动。")

        self.assertIn(state.ending["status"], {"ongoing", "resolved"})
        self.assertEqual(state.ending["window"], "open")
        self.assertGreaterEqual(len(state.ending["candidate_endings"]), 1)
        self.assertTrue({"ending_window_open", "ending_resolved"}.intersection(event_codes(events)))


class StateAffectsValueRulesTest(unittest.TestCase):
    def test_health_state_affects_values(self) -> None:
        state = make_state()
        state.body["体力"] = 30
        state.body["伤病风险"] = 82
        state.body["肌肉疲劳"] = 86
        state.body["嗓音状态"] = 40
        state.mind["精神压力"] = 80

        events, diff = evaluate_all_systems(state, "我继续高强度加练。")

        self.assertIn("health_low_stamina", event_codes(events))
        self.assertIn("health_injury_warning", event_codes(events))
        self.assertIn("health_voice_warning", event_codes(events))
        self.assertIn("mind_high_pressure", event_codes(events))
        self.assertEqual(diff["心理状态.精神压力"], 5)
        self.assertEqual(diff["身体状态.免疫状态"], -3)
        self.assertEqual(diff["风险.伤病爆发风险"], 3)
        self.assertEqual(diff["职业属性.声乐实力"], -1)
        self.assertEqual(diff["心理状态.心情"], -3)
        self.assertEqual(diff["心理状态.职业倦怠"], 3)

    def test_period_phase_affects_body_and_risk_values(self) -> None:
        state = make_state()
        state.period.update({"enabled": True, "mode": "极致", "cycle_day": 26, "irregularity_risk": 45})
        advance_period(state, days=3)

        events, diff = evaluate_period_system(state, "我穿浅色评估服装继续高强度练舞，隐瞒不说。")

        self.assertEqual(state.period["phase"], "生理期前段")
        self.assertIn("period_day1_2", event_codes(events))
        self.assertIn("period_high_intensity_risk", event_codes(events))
        self.assertIn("period_clothing_anxiety", event_codes(events))
        self.assertLess(diff["身体状态.体力"], 0)
        self.assertGreater(diff["身体状态.伤病风险"], 0)
        self.assertGreater(diff["身体状态.伤病风险"], 0)

    def test_relationship_state_affects_relation_and_global_values(self) -> None:
        state = make_state()
        register_known_npc(state, "李娜英", "同期练习生", 18)

        events, diff = evaluate_relationship_system(state, "我陪李娜英一起练习，递热水并谈心。")

        self.assertIn("rel_friendship_signal", event_codes(events))
        self.assertGreater(state.relationships["李娜英"]["friendship"], 20)
        self.assertGreater(state.relationships["李娜英"]["trust"], 20)
        self.assertEqual(diff["团队关系.真实关系温度"], 4)
        self.assertEqual(diff["心理状态.孤独感"], -4)

    def test_staff_boundary_state_affects_risk_values(self) -> None:
        state = make_state(trainee=False, age=20)
        register_known_npc(state, "金PD", "PD/制作人", 38)

        events, diff = evaluate_relationship_system(state, "我对金PD产生心动，想在制作会议后试探他的反应。")

        self.assertIn("rel_high_power_crush_boundary", event_codes(events))
        self.assertGreater(state.relationships["金PD"]["relationship_risk"], 0)
        self.assertEqual(diff["风险.公关危机风险"], 4)
        self.assertEqual(diff["心理状态.精神压力"], 4)
        self.assertEqual(diff["公司与合约.危机关注度"], 4)

    def test_market_state_computes_scores_and_outputs_value_effects(self) -> None:
        state = make_idol_market_state()
        events, diff = evaluate_market_score_system(state, "回归打歌第一周，我看音源、销量、MV、直拍和一位候补数据。")

        self.assertIn("market_score", event_sources(events))
        self.assertGreater(state.market_scores["音源成绩"], 0)
        self.assertGreater(state.market_scores["专辑销量指数"], 0)
        self.assertGreater(state.market_scores["音乐节目分数"], 0)
        self.assertGreaterEqual(state.market_scores["年度奖项积分"], 1)
        self.assertTrue(diff)

    def test_company_size_and_style_affect_values(self) -> None:
        state = make_state()
        state.company.update({"公司规模": "小型公司", "公司风格": "舞台型", "资源池": 24, "出道窗口压力": 74})

        events, diff = evaluate_company_system(state, "我在月末考核前找经纪人讨论资源和公司出道窗口压力。")

        self.assertIn("company_low_resource_pressure", event_codes(events))
        self.assertIn("company_style_bias", event_codes(events))
        self.assertEqual(diff["团队关系.队内竞争度"], 5)
        self.assertEqual(diff["心理状态.精神压力"], 2)
        self.assertEqual(diff["公司与合约.公司满意度"], -1)
        self.assertEqual(diff["职业属性.舞蹈实力"], 1)
        self.assertEqual(diff["身体状态.肌肉疲劳"], 1)


class CareerCommercialAndContextRulesTest(unittest.TestCase):
    def test_brand_safety_controls_brand_entry_or_observation(self) -> None:
        state = make_idol_market_state()
        state.market["品牌价值"] = 64
        state.fans["路人好感"] = 28
        state.risks.update({"公关危机风险": 78, "恋爱风险": 70, "霸凌排挤风险": 55})

        events, diff = evaluate_brand_contract_system(state, "我参加美妆代言和杂志封面的品牌会议。")

        self.assertIn("brand_safety_low", event_codes(events))
        self.assertLess(state.commercial["商业安全度"], 45)
        self.assertEqual(diff["市场.品牌价值"], -2)
        self.assertEqual(diff["公司与合约.危机关注度"], 2)

    def test_contract_bargaining_strength_controls_terms(self) -> None:
        strong = make_idol_market_state()
        strong.market["品牌价值"] = 88
        strong.company["主推指数"] = 82
        strong.fans["个人粉丝数"] = 300000

        strong_events, _ = evaluate_brand_contract_system(strong, "我进行续约谈判，要求solo权限、演员约权限、署名权和健康保障。")
        self.assertIn("contract_bargaining_strong", event_codes(strong_events))
        self.assertGreater(strong.contract_terms["solo权限"], 10)
        self.assertGreater(strong.contract_terms["健康保障"], 35)

        weak = make_idol_market_state()
        weak.market["品牌价值"] = 5
        weak.company["主推指数"] = 5
        weak.fans["个人粉丝数"] = 0
        weak.risks["公关危机风险"] = 80
        weak.body["伤病风险"] = 80

        weak_events, weak_diff = evaluate_brand_contract_system(weak, "我进行续约谈判，要求提高分成。")
        self.assertIn("contract_bargaining_weak", event_codes(weak_events))
        self.assertEqual(weak_diff["公司与合约.公司满意度"], -2)
        self.assertEqual(weak_diff["心理状态.精神压力"], 2)

    def test_career_branch_entries_are_status_driven(self) -> None:
        state = make_idol_market_state()
        state.career.update({"演技潜力": 70, "创作能力": 70, "制作人能力": 25})
        state.market["品牌价值"] = 78
        state.company["主推指数"] = 74
        state.fans["个人粉丝数"] = 200000

        events, diff = evaluate_career_branch_system(state, "公司讨论solo小分队、演员试镜和创作署名提案。")

        self.assertIn("career_branch_acting_test", event_codes(events))
        self.assertIn("career_branch_solo_unit_test", event_codes(events))
        self.assertIn("career_branch_creative_test", event_codes(events))
        self.assertIn("演员路线测试", state.career_branches["branch_opportunities"])
        self.assertTrue(diff)

    def test_school_family_social_hierarchy_and_safety_contexts_have_value_effects(self) -> None:
        state = make_state(age=16)
        state.school.update({"enrolled": True, "attendance_pressure": 74})
        state.family.update({"career_understanding": 28, "conflict_level": 78})
        school_events, school_diff = evaluate_school_family(state, "我熬夜加练后考试，请假并给妈妈打电话解释。")
        self.assertIn("school_family", event_sources(school_events))
        self.assertTrue(school_diff)

        state.social_context.update({"is_overseas": True, "language_barrier": 58, "visa_pressure": 65})
        social_events, social_diff = evaluate_social_context(state, "我听不懂韩语玩笑，又担心签证和采访。")
        self.assertIn("social_language_pressure", event_codes(social_events))
        self.assertIn("social_visa_pressure", event_codes(social_events))
        self.assertTrue(social_diff)

        hierarchy_events, hierarchy_diff = evaluate_hierarchy_system(state, "我在后台说错敬语，忘记向前辈问候。")
        self.assertIn("hierarchy_etiquette_mistake", event_codes(hierarchy_events))
        self.assertTrue(hierarchy_diff)

        safety_events, safety_diff = evaluate_safety_boundary(state, "宿舍楼下有陌生车偷拍和私生尾随。")
        self.assertIn("safety_stalking_signal", event_codes(safety_events))
        self.assertEqual(safety_diff["风险.私生风险"], 8)
        self.assertEqual(safety_diff["风险.行程泄露风险"], 5)

    def test_inner_life_progression_and_decay_are_deterministic(self) -> None:
        state = make_state()
        inner_events, inner_diff = evaluate_inner_life(state, "队友被老师夸，我站在镜子前想被看见，最后写进日记。")
        self.assertIn("inner_visible_desire", event_codes(inner_events))
        self.assertIn("inner_body_awareness", event_codes(inner_events))
        self.assertIn("inner_diary_outlet", event_codes(inner_events))
        self.assertTrue(inner_diff)

        diff = {"职业属性.舞蹈实力": 1}
        new_diff, progression_events, progression_diff = convert_growth_diff_to_progression(state, "我请老师一对一高强度练舞。", diff)
        self.assertNotIn("职业属性.舞蹈实力", new_diff)
        self.assertTrue(event_codes(progression_events).intersection({"progression_xp_gain", "progression_skill_level_up"}))
        self.assertIsInstance(progression_diff, dict)

        decay_state = make_idol_market_state()
        decay_state.turn = 13
        ensure_skill_decay_state(decay_state)
        for skill in decay_state.skill_last_practiced:
            decay_state.skill_last_practiced[skill] = 0
        decay_events, decay_diff = evaluate_skill_decay_system(decay_state, "我完全不训练，只休息。")
        self.assertIn("skill_proficiency_decay", event_codes(decay_events))
        self.assertIsInstance(decay_diff, dict)


if __name__ == "__main__":
    unittest.main(verbosity=2)
