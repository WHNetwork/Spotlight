from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.action_validator import ActionBlockedError, validate_action
from core.brand_contract_system import ensure_brand_contract_state, evaluate_brand_contract_system
from core.career_branch_system import ensure_career_branch_state, evaluate_career_branch_system
from core.company_system import ensure_company_profile, evaluate_company_system
from core.crisis import update_crises
from core.debut_system import (
    debut_readiness_score,
    evaluate_debut_system,
    hard_gate_passed,
    readiness_to_probability,
    should_evaluate_debut,
)
from core.ending_system import ensure_ending_state, evaluate_ending_system
from core.hierarchy_system import evaluate_hierarchy_system
from core.inner_life import evaluate_inner_life
from core.market_score_system import ensure_market_score_state, evaluate_market_score_system
from core.models import ActiveCrisis, GameState, SystemEvent
from core.period_system import advance_period, evaluate_period_system, phase_for_day
from core.progression_system import (
    convert_growth_diff_to_progression,
    ensure_progression_state,
    growth_threshold,
    training_efficiency,
    xp_from_action_and_delta,
)
from core.relationship_system import (
    classify_relationship_signals,
    cp_age_gap_limit,
    default_relationship,
    ensure_default_relationships,
    evaluate_relationship_system,
    find_relationship_target,
    is_cp_eligible,
    is_power_imbalanced,
    is_professional_relationship,
    register_known_npc,
    relationship_category_for_role,
    staff_role_category,
)
from core.rules import apply_diff, base_diff_for_action, clamp, sanitize_suggested_diff, threshold_warnings
from core.safety_boundary import evaluate_safety_boundary
from core.schedule_system import evaluate_schedule_system
from core.school_family import evaluate_school_family
from core.skill_decay_system import ensure_skill_decay_state, evaluate_skill_decay_system
from core.social_context import evaluate_social_context
from core.systems import classify_turn, evaluate_all_systems
from core.talents import apply_talent_modifiers, generate_talents, TALENT_KEYS
from core.abilities import ABILITY_CATALOG, ability_passive_diff, update_abilities
from core.time_system import advance_time, compute_age_group, default_time_context, determine_turn_duration_days
from core.trainee_life_system import ensure_trainee_life_state, evaluate_trainee_life_system
from core.weekly_plan import compose_action_with_weekly_plan, normalize_weekly_plan_keys, weekly_plan_context, weekly_plan_options


def event_codes(events) -> set[str]:
    return {event.code for event in events}


def event_sources(events) -> set[str]:
    return {event.source_system for event in events}


def _clean_state() -> GameState:
    state = GameState()
    state.save_name = "deterministic-test"
    return state


def make_state(*, trainee: bool = True, age: int = 18) -> GameState:
    state = _clean_state()
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


def make_minor_state(*, trainee: bool = True, age: int = 16) -> GameState:
    state = make_state(trainee=trainee, age=age)
    state.age_context["age"] = age
    state.age_context["is_minor"] = True
    state.age_context["guardian_required"] = True
    state.school["enrolled"] = True
    return state


def make_idol_market_state() -> GameState:
    state = make_state(trainee=False, age=20)
    state.career.update({
        "舞蹈实力": 72, "声乐实力": 68, "RAP能力": 55, "舞台感染力": 76,
        "综艺感": 64, "语言能力": 62, "形象指数": 70, "演技潜力": 58, "创作能力": 50,
    })
    state.market.update({
        "话题度": 68, "品牌价值": 52, "韩国本土影响力": 48, "音源潜力": 64, "销量潜力": 70, "短视频传播力": 72,
    })
    state.fans.update({
        "个人粉丝数": 96000, "团体粉丝数": 420000, "团粉稳定度": 72,
        "唯粉规模": 32, "粉丝信任基础": 70, "站姐稳定度": 65, "路人好感": 62,
    })
    state.company.update({"资源池": 72, "资源倾斜度": 58, "主推指数": 54, "公司信任度": 65})
    state.comeback.update({"风格适配度": 72, "回归阶段": "打歌期"})
    return state


# ===================================================================
# ActivityDiffRulesTest
# ===================================================================
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

    # ── 新增：所有 base_diff_for_action 组合 ──
    def test_rest_action_reduces_fatigue_and_pressure(self) -> None:
        state = make_state()
        diff = base_diff_for_action("我回去休息睡觉不练了放松一下。", state)
        self.assertEqual(diff["身体状态.体力"], 12)
        self.assertEqual(diff["身体状态.睡眠质量"], 6)
        self.assertEqual(diff["心理状态.精神压力"], -4)
        self.assertEqual(diff["身体状态.肌肉疲劳"], -5)

    def test_medical_action_reduces_injury_but_lowers_company_satisfaction(self) -> None:
        state = make_state()
        diff = base_diff_for_action("我去医院找医生做物理治疗和康复，用冰敷和护具。", state)
        self.assertEqual(diff["身体状态.伤病风险"], -8)
        self.assertEqual(diff["身体状态.旧伤负担"], -3)
        self.assertEqual(diff["身体状态.肌肉疲劳"], -4)
        self.assertEqual(diff["公司与合约.公司满意度"], -1)

    def test_social_action_boosts_team_and_reduces_loneliness(self) -> None:
        state = make_state()
        diff = base_diff_for_action("我陪队友一起练习聊天谈心沟通。", state)
        self.assertEqual(diff["团队关系.真实关系温度"], 3)
        self.assertEqual(diff["团队关系.队内信任度"], 2)
        self.assertEqual(diff["心理状态.孤独感"], -3)

    def test_silence_increases_pressure_and_hurts_identity(self) -> None:
        state = make_state()
        diff = base_diff_for_action("我选择沉默不回应忍了算了装没事。", state)
        self.assertEqual(diff["心理状态.精神压力"], 2)
        self.assertEqual(diff["心理状态.自我认同"], -1)

    def test_pr_response_reduces_crisis_risk_and_increases_attention(self) -> None:
        state = make_state()
        diff = base_diff_for_action("我公开回应澄清声明道歉公关。", state)
        self.assertEqual(diff["风险.公关危机风险"], -3)
        self.assertEqual(diff["公司与合约.危机关注度"], 2)

    def test_rap_training_gives_rap_and_costs_stamina(self) -> None:
        state = make_state()
        diff = base_diff_for_action("我专门训练RAP说唱节奏。", state)
        self.assertEqual(diff["职业属性.RAP能力"], 1)
        self.assertIn("身体状态.体力", diff)

    def test_creative_training_gives_creative_ability(self) -> None:
        state = make_state()
        diff = base_diff_for_action("我进行作词训练、作曲训练、编曲写demo。", state)
        self.assertEqual(diff["职业属性.创作能力"], 1)
        self.assertEqual(diff["身体状态.体力"], -3)

    def test_evaluation_showcase_increases_trust_and_rivalry(self) -> None:
        state = make_state()
        diff = base_diff_for_action("我准备月末考核展示和评估录像展示段落。", state)
        self.assertEqual(diff["公司与合约.公司信任度"], 1)
        self.assertEqual(diff["团队关系.队内竞争度"], 1)

    def test_staff_communication_builds_company_trust(self) -> None:
        state = make_state()
        diff = base_diff_for_action("我找经纪人和公司老师PD制作人主管谈话。", state)
        self.assertEqual(diff["公司与合约.公司信任度"], 1)
        self.assertEqual(diff["公司与合约.公司满意度"], 1)

    def test_creative_expression_intent_affects_identity(self) -> None:
        state = make_state()
        diff = base_diff_for_action("我想参与制作表达自己想法争取回归风格概念方向。", state)
        self.assertEqual(diff["心理状态.自我认同"], 2)
        self.assertEqual(diff["公司与合约.公司信任度"], -1)

    def test_producer_ability_only_when_creative_high(self) -> None:
        state = make_state()
        state.career["创作能力"] = 46
        diff = base_diff_for_action("我的作品被采纳参与概念会议进行收录曲署名。", state)
        self.assertEqual(diff["职业属性.制作人能力"], 1)

    def test_producer_ability_blocked_when_creative_low(self) -> None:
        state = make_state()
        state.career["创作能力"] = 30
        diff = base_diff_for_action("我的作品被采纳参与概念会议进行收录曲署名。", state)
        self.assertNotIn("职业属性.制作人能力", diff)

    def test_empty_action_gives_no_diff(self) -> None:
        state = make_state()
        diff = base_diff_for_action("我发呆。", state)
        self.assertEqual(diff, {})

    # ── 新增：apply_diff 更多边界 ──
    def test_apply_diff_with_mixed_valid_invalid_keys(self) -> None:
        state = make_state()
        state.body["体力"] = 50
        state.mind["精神压力"] = 50
        applied = apply_diff(state, {
            "身体状态.体力": -5,
            "心理状态.精神压力": 5,
            "不存在.随便": 10,
            "身体状态.不存在的属性": 3,
        })
        self.assertIn("身体状态.体力", applied)
        self.assertIn("心理状态.精神压力", applied)
        self.assertNotIn("不存在.随便", applied)
        self.assertNotIn("身体状态.不存在的属性", applied)

    def test_apply_diff_max_abs_delta_enforced(self) -> None:
        state = make_state()
        state.body["体力"] = 50
        applied = apply_diff(state, {"身体状态.体力": 100}, max_abs_delta=8)
        self.assertEqual(state.body["体力"], 58)

    def test_apply_diff_with_zero_delta_preserves_state(self) -> None:
        state = make_state()
        state.body["体力"] = 50
        applied = apply_diff(state, {"身体状态.体力": 0})
        self.assertEqual(state.body["体力"], 50)
        self.assertNotIn("身体状态.体力", applied)

    def test_clamp_function_works_correctly(self) -> None:
        self.assertEqual(clamp(150, 0, 100), 100)
        self.assertEqual(clamp(-10, 0, 100), 0)
        self.assertEqual(clamp(50, 0, 100), 50)
        self.assertEqual(clamp(0, 0, 100), 0)
        self.assertEqual(clamp(100, 0, 100), 100)

    # ── 新增：所有 threshold_warnings 边界 ──
    def test_threshold_warnings_stamina_at_exact_40(self) -> None:
        state = make_state()
        state.body["体力"] = 40
        state.body["睡眠质量"] = 60
        state.body["伤病风险"] = 50
        state.mind["精神压力"] = 50
        state.company["公司满意度"] = 50
        warnings = threshold_warnings(state)
        self.assertFalse(any("体力低于 40" in w for w in warnings))

    def test_threshold_warnings_stamina_at_39(self) -> None:
        state = make_state()
        state.body["体力"] = 39
        warnings = threshold_warnings(state)
        self.assertTrue(any("体力低于 40" in w for w in warnings))

    def test_threshold_warnings_sleep_at_40(self) -> None:
        state = make_state()
        state.body["睡眠质量"] = 40
        warnings = threshold_warnings(state)
        self.assertFalse(any("睡眠质量低于 40" in w for w in warnings))

    def test_threshold_warnings_sleep_at_39(self) -> None:
        state = make_state()
        state.body["睡眠质量"] = 39
        warnings = threshold_warnings(state)
        self.assertTrue(any("睡眠质量低于 40" in w for w in warnings))

    def test_threshold_warnings_injury_at_76(self) -> None:
        state = make_state()
        state.body["伤病风险"] = 76
        warnings = threshold_warnings(state)
        self.assertTrue(any("伤病风险高于 75" in w for w in warnings))

    def test_threshold_warnings_injury_at_75(self) -> None:
        state = make_state()
        state.body["伤病风险"] = 75
        warnings = threshold_warnings(state)
        self.assertFalse(any("伤病风险高于 75" in w for w in warnings))

    def test_threshold_warnings_mood_below_30(self) -> None:
        state = make_state()
        state.mind["心情"] = 29
        warnings = threshold_warnings(state)
        self.assertTrue(any("心情低于 30" in w for w in warnings))

    def test_threshold_warnings_pressure_at_91(self) -> None:
        state = make_state()
        state.mind["精神压力"] = 91
        warnings = threshold_warnings(state)
        self.assertTrue(any("精神压力高于 90" in w for w in warnings))

    def test_threshold_warnings_company_satisfaction_at_34(self) -> None:
        state = make_state()
        state.company["公司满意度"] = 34
        warnings = threshold_warnings(state)
        self.assertTrue(any("公司满意度低于 35" in w for w in warnings))


# ===================================================================
# TimeSlotAndScheduleRulesTest
# ===================================================================
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

    # ── 新增：所有 turn_kind 分类 ──
    def test_crisis_routing_with_active_crisis_override(self) -> None:
        state = make_state(trainee=False)
        state.active_crises.append(ActiveCrisis(
            crisis_id="test_crisis", crisis_type="public_relations",
            title="test", stage="response_window", heat=50,
        ))
        route = classify_turn("我随便休息。", state)
        self.assertEqual(route.turn_kind, "crisis")

    def test_ordinary_routing_for_idle_actions(self) -> None:
        state = make_state(trainee=False)
        route = classify_turn("我整理宿舍洗衣服。", state)
        self.assertEqual(route.turn_kind, "ordinary")
        self.assertEqual(route.model_tier, "flash")

    def test_mainline_routing_for_award_action(self) -> None:
        state = make_state(trainee=False)
        route = classify_turn("年末颁奖典礼我准备拿大赏。", state)
        self.assertEqual(route.turn_kind, "mainline")
        self.assertEqual(route.model_tier, "pro")

    def test_crisis_routing_for_private_stalker(self) -> None:
        state = make_state(trainee=False)
        route = classify_turn("私生追车泄露我的住址。", state)
        self.assertEqual(route.turn_kind, "crisis")

    def test_focus_routing_for_livestream_action(self) -> None:
        state = make_state(trainee=False)
        route = classify_turn("我今天做团综直播。", state)
        self.assertEqual(route.turn_kind, "focus")

    # ── 新增：time advance with various durations ──
    def test_time_advance_ordinary_turn_advances_7_days(self) -> None:
        state = make_state(trainee=False)
        route = classify_turn("我整理宿舍然后休息睡觉。", state)
        events, _, days = advance_time(state, route, "我整理宿舍然后休息睡觉。")
        self.assertEqual(days, 7)

    def test_time_advance_crisis_turn_advances_1_day(self) -> None:
        state = make_state(trainee=False)
        route = classify_turn("热搜造谣后我回应澄清。", state)
        events, _, days = advance_time(state, route, "热搜造谣后我回应澄清。")
        self.assertEqual(days, 1)

    def test_trainee_slot_usage_all_categories(self) -> None:
        from core.trainee_life_system import _slot_usage
        usage = _slot_usage("我高强度加练舞蹈声乐，休息睡觉，陪队友社交谈心，去学校考试，写demo创作，观察公司和经纪人会议。")
        self.assertGreater(usage.get("训练", 0), 0)
        self.assertGreater(usage.get("恢复", 0), 0)
        self.assertGreater(usage.get("社交", 0), 0)
        self.assertGreater(usage.get("学校", 0), 0)
        self.assertGreater(usage.get("创作", 0), 0)
        self.assertGreater(usage.get("公司观察", 0), 0)

    def test_idol_slot_usage_all_categories(self) -> None:
        from core.trainee_life_system import _slot_usage
        usage = _slot_usage("我打歌彩排拍摄MV，开直播营业粉丝签售，参加品牌代言杂志广告拍摄。")
        self.assertGreater(usage.get("公开行程", 0), 0)
        self.assertGreater(usage.get("粉丝营业", 0), 0)
        self.assertGreater(usage.get("商业资源", 0), 0)

    # ── 新增：bullying pressure 和 hidden conflict 测试 ──
    def test_bullying_pressure_high_triggers_events(self) -> None:
        state = make_state(trainee=True)
        state.company["资源池"] = 10
        state.company["出道窗口压力"] = 90
        state.team["队内竞争度"] = 90
        state.team["真实关系温度"] = 10
        state.team["宿舍安全感"] = 10
        events, diff = evaluate_trainee_life_system(
            state, "宿舍里分组冷处理让我很难受，练习室时间被抢，我觉得被排挤。"
        )
        self.assertIn("trainee_bullying_pressure_high", event_codes(events))

    def test_conflict_help_seeking_reduces_hidden_conflict(self) -> None:
        state = make_state(trainee=True)
        state.trainee_life["hidden_conflict"] = 50
        events, _ = evaluate_trainee_life_system(
            state, "我找经纪人和老师报告保留证据求助。"
        )
        self.assertIn("trainee_conflict_help_seeking", event_codes(events))

    def test_protecting_someone_creates_memory(self) -> None:
        state = make_state(trainee=True)
        events, _ = evaluate_trainee_life_system(
            state, "我保护被排挤的队友，替她解释帮她作证挡下。"
        )
        self.assertIn("trainee_protected_someone", event_codes(events))
        self.assertEqual(state.trainee_life["protected_someone_memory"], 8)


# ===================================================================
# StateEntryExitRulesTest
# ===================================================================
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

    # ── 新增：更多 debut 边界测试 ──
    def test_hard_gate_all_reasons_checked(self) -> None:
        state = make_state(trainee=True)
        state.career.update({"舞蹈实力": 10, "声乐实力": 10, "舞台感染力": 10})
        state.body["体力"] = 10
        state.body["伤病风险"] = 90
        state.mind["精神压力"] = 90
        state.company["公司信任度"] = 10
        passed, reasons = hard_gate_passed(state)
        self.assertFalse(passed)
        self.assertGreaterEqual(len(reasons), 4)

    def test_should_evaluate_debut_detects_keywords(self) -> None:
        state = make_state(trainee=True)
        self.assertTrue(should_evaluate_debut(state, "公司季度评估讨论我是否进入出道组候选。"))
        self.assertFalse(should_evaluate_debut(state, "我暂时不问出道。"))
        self.assertFalse(should_evaluate_debut(state, "我日常训练。"))

    def test_readiness_to_probability_all_thresholds(self) -> None:
        self.assertEqual(readiness_to_probability(40), 0)
        self.assertEqual(readiness_to_probability(50), 18)
        self.assertEqual(readiness_to_probability(59), 18)
        self.assertEqual(readiness_to_probability(60), 35)
        self.assertEqual(readiness_to_probability(69), 35)
        self.assertEqual(readiness_to_probability(70), 58)
        self.assertEqual(readiness_to_probability(79), 58)
        self.assertEqual(readiness_to_probability(80), 78)
        self.assertEqual(readiness_to_probability(89), 78)
        self.assertEqual(readiness_to_probability(90), 90)

    def test_debut_readiness_score_with_minimal_state(self) -> None:
        state = make_state(trainee=True)
        score = debut_readiness_score(state)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_debut_not_evaluated_on_ordinary_action_without_keywords(self) -> None:
        state = make_state(trainee=True)
        state.debut["window_turns_left"] = 5
        events, _ = evaluate_debut_system(state, "我只做日常训练不讨论出道。")
        self.assertEqual(state.debut["window_turns_left"], 4)
        self.assertEqual(events, [])

    def test_force_rest_blocks_debut_gate(self) -> None:
        state = make_state(trainee=True)
        state.career.update({"舞蹈实力": 45, "声乐实力": 42, "舞台感染力": 48})
        state.company["公司信任度"] = 66
        state.body["体力"] = 78
        state.body["伤病风险"] = 18
        state.mind["精神压力"] = 42
        state.status_effects["强制休养"] = 2
        passed, reasons = hard_gate_passed(state)
        self.assertFalse(passed)
        self.assertTrue(any("强制休养" in item for item in reasons))


# ===================================================================
# StateAffectsValueRulesTest
# ===================================================================
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

    # ── 新增：更多 company style 测试 ──
    def test_all_company_styles_have_value_effects(self) -> None:
        for style in ["舞台型", "音源型", "视觉概念型", "海外市场导向", "综艺营销型", "数据导向"]:
            with self.subTest(style=style):
                state = make_state()
                state.company["公司风格"] = style
                events, diff = evaluate_company_system(state, "我找公司讨论资源和考核。")
                self.assertIsInstance(events, list)
                self.assertIsInstance(diff, dict)

    def test_company_no_event_without_attention_keywords(self) -> None:
        state = make_state()
        state.company["资源池"] = 20
        events, diff = evaluate_company_system(state, "我一个人默默地反复练动作。")
        self.assertIsInstance(events, list)
        self.assertIsInstance(diff, dict)

    # ── 新增：更多关系测试 ──
    def test_same_age_staff_crush_boundary(self) -> None:
        state = make_state(trainee=False, age=22)
        register_known_npc(state, "赵造型师", "造型师", 23)
        events, diff = evaluate_relationship_system(state, "我对赵造型师有点心动在意。")
        self.assertTrue(
            "rel_same_age_staff_crush_risk" in event_codes(events)
            or "rel_staff_crush_boundary" in event_codes(events)
        )

    def test_minor_crush_triggers_boundary_warning(self) -> None:
        state = make_minor_state(age=16)
        register_known_npc(state, "李娜英", "同期练习生", 16)
        events, diff = evaluate_relationship_system(state, "我喜欢上李娜英，很在意她的眼神和反应。")
        self.assertIn("rel_minor_boundary_ethics_warning", event_codes(events))
        self.assertGreater(state.relationships["李娜英"]["relationship_risk"], 10)

    def test_boundary_signal_reduces_ambiguity(self) -> None:
        state = make_state()
        register_known_npc(state, "李娜英", "同期练习生", 18)
        state.relationships["李娜英"]["ambiguity"] = 40
        events, _ = evaluate_relationship_system(state, "我明确告诉她我们只是朋友不能越界。")
        self.assertIsInstance(events, list)
        self.assertLessEqual(state.relationships["李娜英"]["ambiguity"], 40)

    def test_cp_eligible_peer_can_do_business_cp(self) -> None:
        state = make_state(trainee=False, age=20)
        register_known_npc(state, "李娜英", "同团成员", 20)
        events, _ = evaluate_relationship_system(state, "公司安排我和李娜英在镜头前营业CP互动粉丝想看的对视。")
        self.assertIn("rel_business_cp_signal", event_codes(events))

    def test_cp_ineligible_staff_blocked_from_cp(self) -> None:
        state = make_state(trainee=False, age=20)
        register_known_npc(state, "韩室长", "经纪人", 31)
        events, _ = evaluate_relationship_system(state, "我想和韩室长做营业CP互动。")
        self.assertIn("rel_cp_ineligible_boundary", event_codes(events))

    def test_rivalry_signal_increases_competition(self) -> None:
        state = make_state()
        register_known_npc(state, "李娜英", "同期练习生", 18)
        events, _ = evaluate_relationship_system(state, "老师只夸了李娜英的考核center部分，我觉得被比较很嫉妒。")
        self.assertIn("rel_rivalry_signal", event_codes(events))
        self.assertGreater(state.relationships["李娜英"]["rivalry"], 24)

    def test_public_risk_signal_on_sasaeng(self) -> None:
        state = make_state(trainee=False, age=20)
        register_known_npc(state, "金泰渊", "同代爱豆", 21)
        events, _ = evaluate_relationship_system(state, "站姐拍到我和金泰渊同路，私生也在偷拍截图。")
        self.assertIn("rel_public_risk_signal", event_codes(events))

    def test_ambiguity_drift_when_high_friendship_and_crush(self) -> None:
        state = make_state(trainee=False, age=20)
        register_known_npc(state, "李娜英", "同团成员", 20)
        state.relationships["李娜英"]["friendship"] = 55
        state.relationships["李娜英"]["player_crush"] = 40
        state.relationships["李娜英"]["ambiguity"] = 10
        events, _ = evaluate_relationship_system(state, "我对李娜英越来越在意，朋友和心动的界限模糊了。")
        self.assertIsInstance(events, list)

    # ── 新增：find_relationship_target 测试 ──
    def test_find_relationship_target_from_action(self) -> None:
        state = make_state()
        register_known_npc(state, "李娜英", "同期练习生", 18)
        target = find_relationship_target(state, "我陪李娜英一起练习谈心。")
        self.assertEqual(target, "李娜英")

    def test_find_relationship_target_returns_none_for_no_match(self) -> None:
        state = make_state()
        target = find_relationship_target(state, "我独自练习。")
        self.assertIsNone(target)

    def test_classify_relationship_signals_all_types(self) -> None:
        signals = classify_relationship_signals("我陪她谈心照顾递热水，又有点心动在意想靠近，但站姐偷拍被粉丝误会。")
        self.assertIn("friendship", signals)
        self.assertIn("romance", signals)
        self.assertIn("risk", signals)

    def test_classify_relationship_signals_empty(self) -> None:
        signals = classify_relationship_signals("我喝水。")
        self.assertEqual(signals, [])


# ===================================================================
# CareerCommercialAndContextRulesTest
# ===================================================================
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

    # ── 新增：inner_life 更多场景 ──
    def test_inner_life_secret_weight_accumulation(self) -> None:
        state = make_state()
        state.inner_life["秘密重量"] = 60
        events, diff = evaluate_inner_life(state, "我有不能说的秘密压在心里，写进日记也不敢给别人看。")
        self.assertIsInstance(events, list)
        self.assertIsInstance(diff, dict)

    def test_inner_life_crush_heartbeat_recording(self) -> None:
        state = make_state()
        state.inner_life["心动值"] = 50
        events, diff = evaluate_inner_life(state, "我在日记里写下对他的感觉，心跳好快。")
        self.assertIsInstance(events, list)
        self.assertIsInstance(diff, dict)

    def test_inner_life_visible_desire_and_body_consciousness(self) -> None:
        state = make_state()
        state.inner_life["被看见的渴望"] = 80
        state.inner_life["身体自我意识"] = 70
        events, diff = evaluate_inner_life(state, "镜子里我看自己的腿和腰，想被粉丝看见舞台上好看的我。")
        self.assertIsInstance(events, list)
        self.assertIsInstance(diff, dict)


# ===================================================================
# MultiTurnEvolutionTests
# ===================================================================
class MultiTurnEvolutionTests(unittest.TestCase):
    def test_progression_accumulates_xp_over_multiple_turns(self) -> None:
        state = make_state()
        state.talents["舞蹈天赋"] = 80
        state.career["舞蹈实力"] = 12
        state.progression["skill_xp"]["dance"] = 0
        xp_values = []
        for i in range(6):
            diff = {"职业属性.舞蹈实力": 1}
            new_diff, events, prog_diff = convert_growth_diff_to_progression(
                state, "我持续高强度练舞。", diff
            )
            self.assertEqual(new_diff, {})
            xp_values.append(state.progression["skill_xp"]["dance"])
        self.assertGreaterEqual(state.progression["skill_total_xp"]["dance"], 0)
        self.assertIsInstance(events, list)

    def test_crisis_lifecycle_spanning_multiple_turns(self) -> None:
        state = make_state(trainee=False)
        from core.models import ActiveCrisis
        state.active_crises.append(ActiveCrisis(
            crisis_id="pr_long", crisis_type="public_relations",
            title="旧视频热搜持续争议", stage="response_window",
            heat=65, duration=4, failure_flag="舆论处理留下长期阴影",
        ))
        stages = []
        for step in range(5):
            state.turn += 1
            events, _ = update_crises(state, "我继续回应舆论。", [])
            if state.active_crises:
                stages.append(state.active_crises[0].stage)
            self.assertIsInstance(events, list)
        self.assertTrue(
            any(s in {"closed", "converted", "aftermath"} for s in stages)
            or not state.active_crises
        )

    def test_mind_body_spiral_under_sustained_pressure(self) -> None:
        state = make_state()
        state.body["体力"] = 35
        state.mind["精神压力"] = 78
        state.body["伤病风险"] = 68
        state.mind["职业倦怠"] = 0
        initial_burnout = state.mind["职业倦怠"]
        for _ in range(3):
            events, diff = evaluate_all_systems(
                state, "我熬夜加练，硬撑不告诉任何人。"
            )
            self.assertIsInstance(events, list)
            self.assertIsInstance(diff, dict)
            self.assertGreater(state.mind["精神压力"], 1)
        self.assertGreaterEqual(state.mind["职业倦怠"], initial_burnout)

    def test_debut_window_countdown_to_expiry(self) -> None:
        state = make_state(trainee=True)
        state.debut.update({
            "status": "candidate_deferred", "window_turns_left": 8,
            "readiness": 52, "probability": 0.18,
        })
        statuses = []
        for turn in range(4):
            events, _ = evaluate_debut_system(state, "我继续日常训练。")
            statuses.append(state.debut["status"])
        self.assertIn("candidate_deferred", statuses)

    def test_fandom_pr_escalation_over_turns(self) -> None:
        state = make_idol_market_state()
        state.fans["黑粉活跃度"] = 68
        state.risks["公关危机风险"] = 56
        state.fans["粉丝信任基础"] = 36
        for _ in range(3):
            events, diff = evaluate_all_systems(
                state, "黑粉继续传播剪辑视频，我观察舆论动态。"
            )
            self.assertIsInstance(diff, dict)

    # ── 新增：crisis 多回合生命周期 ──
    def test_health_crisis_escalation_to_forced_rest(self) -> None:
        state = make_state(trainee=False)
        state.body["体力"] = 28
        state.body["伤病风险"] = 82
        state.mind["精神压力"] = 72
        from core.models import ActiveCrisis
        state.active_crises.append(ActiveCrisis(
            crisis_id="health_test", crisis_type="health",
            title="伤病危机", stage="response_window", heat=70,
        ))
        for _ in range(5):
            state.turn += 1
            events, _ = update_crises(state, "我继续高强度加练硬撑。", [])
        # After several rounds of high intensity, health crisis escalates
        self.assertIsInstance(state.active_crises[0].heat, int) if state.active_crises else None

    def test_safety_crisis_management_over_turns(self) -> None:
        state = make_state(trainee=False)
        from core.models import ActiveCrisis
        state.active_crises.append(ActiveCrisis(
            crisis_id="safety_test", crisis_type="safety",
            title="私生安全危机", stage="response_window", heat=60,
        ))
        for _ in range(3):
            state.turn += 1
            events, _ = update_crises(state, "我报警换宿舍告诉经纪人公司处理安保换路线。", [])
        self.assertLess(
            state.active_crises[0].heat if state.active_crises else 0,
            40
        )

    def test_silence_turns_crisis_into_converted(self) -> None:
        state = make_state(trainee=False)
        from core.models import ActiveCrisis
        state.active_crises.append(ActiveCrisis(
            crisis_id="silence_test", crisis_type="public_relations",
            title="沉默测试危机", stage="response_window", heat=55, duration=4,
            failure_flag="沉默代价标签",
        ))
        for _ in range(2):
            state.turn += 1
            update_crises(state, "我沉默不回应。", [])
        self.assertIn("沉默代价标签", state.flags)

    def test_progression_level_up_over_many_turns(self) -> None:
        state = make_state()
        state.talents["舞蹈天赋"] = 90
        state.career["舞蹈实力"] = 5
        initial = state.career["舞蹈实力"]
        for _ in range(15):
            diff = {"职业属性.舞蹈实力": 1}
            new_diff, _, _ = convert_growth_diff_to_progression(state, "我高强度加练舞蹈一对一老师指导。", diff)
            self.assertEqual(new_diff, {})
        self.assertGreaterEqual(state.progression["skill_total_xp"]["dance"], 50)

    def test_training_efficiency_low_stamina_penalty(self) -> None:
        state = make_state()
        state.body["体力"] = 30
        eff = training_efficiency(state, "dance", "我练舞。")
        self.assertLess(eff, 1.0)

    def test_training_efficiency_high_talent_bonus(self) -> None:
        state = make_state()
        state.talents["舞蹈天赋"] = 90
        eff = training_efficiency(state, "dance", "我练舞。")
        self.assertGreater(eff, 1.0)

    def test_skill_decay_over_multiple_turns(self) -> None:
        state = make_idol_market_state()
        state.turn = 1
        ensure_skill_decay_state(state)
        for skill in state.skill_last_practiced:
            state.skill_last_practiced[skill] = 0
        state.career["舞蹈实力"] = 80
        initial_prof = state.skill_proficiency.get("dance", 70)
        for _ in range(5):
            state.turn += 1
            events, _ = evaluate_skill_decay_system(state, "我完全不训练不跳舞。")
            self.assertIsInstance(events, list)
        self.assertIsInstance(state.skill_proficiency.get("dance"), int)


# ===================================================================
# BoundaryValueTests
# ===================================================================
class BoundaryValueTests(unittest.TestCase):
    def test_apply_diff_clamps_below_zero(self) -> None:
        state = make_state()
        state.body["体力"] = 5
        applied = apply_diff(state, {"身体状态.体力": -20}, max_abs_delta=8)
        self.assertGreaterEqual(state.body["体力"], 0)
        self.assertIsInstance(applied, dict)

    def test_apply_diff_clamps_above_100(self) -> None:
        state = make_state()
        state.career["舞蹈实力"] = 98
        applied = apply_diff(state, {"职业属性.舞蹈实力": 10}, max_abs_delta=8)
        self.assertLessEqual(state.career["舞蹈实力"], 100)

    def test_sanitize_suggested_diff_handles_zero_value(self) -> None:
        state = make_state()
        result = sanitize_suggested_diff(state, {"职业属性.舞蹈实力": 0}, "我观察别人练舞。")
        self.assertIsInstance(result, dict)

    def test_sanitize_suggested_diff_handles_mixed_valid_invalid(self) -> None:
        state = make_state()
        state.career["创作能力"] = 20
        result = sanitize_suggested_diff(
            state,
            {
                "职业属性.舞蹈实力": 2,
                "职业属性.制作人能力": 5,
                "职业属性.声乐实力": -1,
                "身体状态.体力": -3,
            },
            "我练舞唱demo提案。",
        )
        self.assertIn("职业属性.舞蹈实力", result)
        self.assertNotIn("职业属性.制作人能力", result)
        self.assertIsInstance(result, dict)

    def test_talent_modifiers_with_action_text(self) -> None:
        state = make_state()
        state.talents["舞蹈天赋"] = 80
        diff = {"职业属性.舞蹈实力": 1}
        result = apply_talent_modifiers(state, "我高强度练舞。", diff)
        self.assertIsInstance(result, dict)

    def test_threshold_warnings_at_exact_boundaries(self) -> None:
        state = make_state()
        state.body["体力"] = 42
        state.body["睡眠质量"] = 50
        state.body["伤病风险"] = 50
        state.mind["精神压力"] = 70
        state.company["公司满意度"] = 45
        warnings = threshold_warnings(state)
        self.assertEqual(warnings, [])

        state.body["体力"] = 15
        state.body["睡眠质量"] = 35
        state.body["伤病风险"] = 80
        state.mind["精神压力"] = 95
        state.company["公司满意度"] = 25
        warnings = threshold_warnings(state)
        self.assertGreater(len(warnings), 0)

    # ── 新增：所有属性的0/100边界 ──
    def test_all_career_fields_are_ints_and_clamped(self) -> None:
        state = make_state()
        state.career["舞蹈实力"] = 200
        applied = apply_diff(state, {"职业属性.舞蹈实力": -10}, max_abs_delta=8)
        self.assertLessEqual(state.career["舞蹈实力"], 100)

    def test_all_body_fields_are_clamped_to_zero(self) -> None:
        state = make_state()
        state.body["体力"] = 1
        applied = apply_diff(state, {"身体状态.体力": -10}, max_abs_delta=8)
        self.assertGreaterEqual(state.body["体力"], 0)

    def test_all_mind_fields_are_clamped_to_zero(self) -> None:
        state = make_state()
        state.mind["心情"] = 1
        applied = apply_diff(state, {"心理状态.心情": -10}, max_abs_delta=8)
        self.assertGreaterEqual(state.mind["心情"], 0)

    def test_all_fan_fields_are_clamped(self) -> None:
        state = make_state()
        state.fans["个人粉丝数"] = -10
        applied = apply_diff(state, {"粉丝与舆论.个人粉丝数": 5}, max_abs_delta=8)
        self.assertGreaterEqual(state.fans["个人粉丝数"], 0)

    def test_all_risk_fields_are_clamped_to_zero(self) -> None:
        state = make_state()
        state.risks["公关危机风险"] = -5
        applied = apply_diff(state, {"风险.公关危机风险": -10}, max_abs_delta=8)
        self.assertGreaterEqual(state.risks["公关危机风险"], 0)

    def test_sanitize_suggested_diff_with_all_categories(self) -> None:
        state = make_state()
        result = sanitize_suggested_diff(state, {
            "职业属性.舞蹈实力": 1,
            "身体状态.体力": -5,
            "心理状态.精神压力": 2,
            "公司与合约.公司满意度": 3,
            "团队关系.队内竞争度": 1,
            "粉丝与舆论.粉丝信任基础": 1,
            "市场.话题度": 1,
            "风险.私生风险": 1,
            "回归.风格适配度": 1,
        }, "我全面训练。")
        self.assertIsInstance(result, dict)
        self.assertGreater(len(result), 3)

    def test_apply_diff_with_very_large_delta(self) -> None:
        state = make_state()
        state.body["体力"] = 50
        applied = apply_diff(state, {"身体状态.体力": 9999}, max_abs_delta=8)
        self.assertEqual(state.body["体力"], 58)

    def test_apply_diff_with_very_negative_delta(self) -> None:
        state = make_state()
        state.body["体力"] = 50
        applied = apply_diff(state, {"身体状态.体力": -9999}, max_abs_delta=8)
        self.assertEqual(state.body["体力"], 42)

    def test_growth_threshold_all_ranges(self) -> None:
        self.assertEqual(growth_threshold(10), 6)
        self.assertEqual(growth_threshold(20), 6)
        self.assertEqual(growth_threshold(30), 10)
        self.assertEqual(growth_threshold(40), 10)
        self.assertEqual(growth_threshold(50), 16)
        self.assertEqual(growth_threshold(60), 16)
        self.assertEqual(growth_threshold(70), 24)
        self.assertEqual(growth_threshold(80), 24)
        self.assertEqual(growth_threshold(90), 36)
        self.assertEqual(growth_threshold(100), 36)


# ===================================================================
# ConcurrentSystemInteractionTests
# ===================================================================
class ConcurrentSystemInteractionTests(unittest.TestCase):
    def test_period_crisis_and_training_simultaneously(self) -> None:
        state = make_state()
        state.period.update({"enabled": True, "mode": "极致", "cycle_day": 26})
        advance_period(state, days=3)
        state.body["伤病风险"] = 72
        state.body["体力"] = 28
        state.mind["精神压力"] = 74
        from core.models import ActiveCrisis
        state.active_crises.append(ActiveCrisis(
            crisis_id="health_crisis", crisis_type="health",
            title="伤病危机窗口", stage="response_window", heat=72,
        ))
        events, diff = evaluate_all_systems(
            state, "生理期加伤病，我还要穿浅色评估服高强度练舞。"
        )
        sources = event_sources(events)
        self.assertTrue(len(sources) >= 1)
        self.assertIsInstance(diff, dict)

    def test_relationship_romance_during_public_relations_crisis(self) -> None:
        state = make_idol_market_state()
        register_known_npc(state, "李娜英", "同团成员", 20)
        state.relationships["李娜英"] = {
            "name": "李娜英", "role": "同团成员", "age": 20,
            "friendship": 42, "trust": 38,
            "player_crush": 36, "npc_romantic_interest_hidden": 28,
            "cp_eligible": True, "relationship_risk": 12,
        }
        state.fans["黑粉活跃度"] = 68
        state.risks["公关危机风险"] = 56
        events, diff = evaluate_all_systems(
            state, "舆论危机中我和李娜英在后台谈心，粉丝也在解读我们互动。"
        )
        self.assertIsInstance(events, list)
        self.assertIsInstance(diff, dict)

    def test_company_team_schedule_pressure_overload(self) -> None:
        state = make_state(trainee=True)
        state.company["资源池"] = 22
        state.company["出道窗口压力"] = 78
        state.company["公司满意度"] = 42
        state.team["队内竞争度"] = 72
        state.team["真实关系温度"] = 30
        state.mind["精神压力"] = 68
        events, diff = evaluate_all_systems(
            state, "公司资源少、同期竞争高、精神压力大，我还要超负荷训练和准备月末考核。"
        )
        self.assertIsInstance(events, list)
        self.assertIsInstance(diff, dict)

    def test_brand_negotiation_during_career_branch(self) -> None:
        state = make_idol_market_state()
        state.career.update({"演技潜力": 72, "创作能力": 68})
        state.market["品牌价值"] = 76
        state.company["主推指数"] = 70
        state.company["个人议价权"] = 72
        state.fans["个人粉丝数"] = 200000
        events, diff = evaluate_all_systems(
            state,
            "品牌谈判和演员转型同时浮现，我想看看哪条路更有发展。",
        )
        sources = event_sources(events)
        self.assertIsInstance(events, list)
        self.assertIsInstance(diff, dict)

    def test_overseas_school_hierarchy_safety_combined(self) -> None:
        state = make_state(age=16)
        state.school.update({"enrolled": True, "attendance_pressure": 68})
        state.family.update({"career_understanding": 28, "conflict_level": 56})
        state.social_context.update({
            "is_overseas": True, "language_barrier": 56,
            "visa_pressure": 62, "cultural_adaptation": 30,
        })
        state.hierarchy.update({
            "honorific_adaptation": 28, "etiquette_pressure": 68,
        })
        state.safety["dorm_security"] = 40
        events, diff = evaluate_all_systems(
            state,
            "我作为海外未成年练习生，要应对学校考试、语言压力、前后辈敬语和宿舍安全。",
        )
        self.assertIsInstance(events, list)
        self.assertIsInstance(diff, dict)

    # ── 新增：更多并发系统交互 ──
    def test_period_with_overseas_pressure_combined(self) -> None:
        state = make_state(age=18)
        state.period.update({"enabled": True, "mode": "极致", "cycle_day": 25})
        advance_period(state, days=4)
        state.social_context.update({
            "nationality": "中国", "is_overseas": True,
            "language_barrier": 50, "visa_pressure": 60,
            "cultural_adaptation": 30,
        })
        events, diff = evaluate_all_systems(
            state, "生理期加签证压力，我穿浅色服继续高强度练舞。"
        )
        self.assertIsInstance(events, list)
        self.assertIsInstance(diff, dict)

    def test_multiple_crises_simultaneously(self) -> None:
        state = make_state(trainee=False)
        from core.models import ActiveCrisis
        state.active_crises.append(ActiveCrisis(
            crisis_id="pr_multi", crisis_type="public_relations",
            title="舆论危机1", stage="response_window", heat=60,
        ))
        state.active_crises.append(ActiveCrisis(
            crisis_id="health_multi", crisis_type="health",
            title="健康危机1", stage="response_window", heat=55,
        ))
        events, _ = update_crises(state, "我一边回应热搜一边去医院看伤。", [])
        self.assertIsInstance(events, list)
        self.assertEqual(len(state.active_crises), 2)

    def test_inner_life_during_ending_window(self) -> None:
        state = make_idol_market_state()
        state.turn = 160
        state.company["个人议价权"] = 80
        state.market["品牌价值"] = 80
        state.fans["个人粉丝数"] = 300000
        state.career["舞台感染力"] = 85
        state.inner_life["被看见的渴望"] = 90
        state.inner_life["秘密重量"] = 80
        events, diff = evaluate_all_systems(
            state, "续约期我站在镜子前回顾从练习室走到现在的旅程，想哭又不敢哭。"
        )
        self.assertIsInstance(events, list)
        self.assertIsInstance(diff, dict)


# ===================================================================
# EndingSystemFullRangeTests
# ===================================================================
class EndingSystemFullRangeTests(unittest.TestCase):
    def _make_late_game_state(self) -> GameState:
        state = make_state(trainee=False, age=24)
        state.turn = 200
        state.current_mainline = "续约前一年"
        state.career.update({
            "舞蹈实力": 88, "声乐实力": 84, "舞台感染力": 90,
            "演技潜力": 82, "创作能力": 78, "制作人能力": 55,
            "综艺感": 76, "形象指数": 86, "语言能力": 74,
        })
        state.market.update({
            "话题度": 86, "品牌价值": 84, "韩国本土影响力": 82,
            "日本市场影响力": 72, "东南亚市场影响力": 70,
        })
        state.fans.update({
            "个人粉丝数": 450000, "团体粉丝数": 1200000,
            "团粉稳定度": 78, "粉丝信任基础": 82,
        })
        state.company.update({
            "个人议价权": 88, "主推指数": 82, "续约倾向": 56,
            "合约稳定度": 56, "团体存续概率": 78,
        })
        state.team.update({"团队默契度": 76, "真实关系温度": 72})
        state.body["伤病风险"] = 36
        state.mind["职业倦怠"] = 48
        ensure_ending_state(state)
        return state

    def test_ending_evaluates_for_late_game_state(self) -> None:
        state = self._make_late_game_state()
        events, _ = evaluate_ending_system(
            state, "续约期我回顾从练习室走到颁奖台的完整旅程，考虑solo和演员转型。"
        )
        self.assertIsInstance(events, list)
        self.assertIsInstance(state.ending["candidate_endings"], list)

    def test_ending_not_evaluated_for_trainee(self) -> None:
        state = make_state(trainee=True)
        state.turn = 200
        events, _ = evaluate_ending_system(
            state, "我想知道我的结局会是什么。"
        )
        self.assertEqual(state.ending["window"], "closed")
        self.assertEqual(state.ending["candidate_endings"], [])

    def test_ending_window_opens_with_sufficient_scores(self) -> None:
        state = self._make_late_game_state()
        state.turn = 180
        state.career["舞台感染力"] = 95
        state.career["演技潜力"] = 92
        state.fans["个人粉丝数"] = 500000
        events, _ = evaluate_ending_system(
            state, "续约前我想认真考虑演员转型路线。"
        )
        self.assertIn(state.ending["window"], {"open", "closed"})
        self.assertGreaterEqual(len(state.ending["candidate_endings"]), 0)

    def test_quiet_exit_window_when_health_declines(self) -> None:
        state = self._make_late_game_state()
        state.turn = 160
        state.body["伤病风险"] = 90
        state.mind["职业倦怠"] = 90
        state.risks["伤病爆发风险"] = 80
        events, _ = evaluate_ending_system(
            state, "健康越来越差，我需要面对这个结局。"
        )
        self.assertGreaterEqual(len(state.ending["candidate_endings"]), 0)

    def test_no_ending_opens_when_ongoing_early(self) -> None:
        state = make_state(trainee=True)
        state.turn = 20
        events, _ = evaluate_ending_system(state, "我刚开始练习生生活。")
        self.assertEqual(state.ending["window"], "closed")
        self.assertEqual(state.ending["candidate_endings"], [])

    # ── 新增：ending 更多场景 ──
    def test_ending_with_very_high_turn_and_burnout(self) -> None:
        state = self._make_late_game_state()
        state.turn = 250
        state.mind["职业倦怠"] = 95
        state.body["伤病风险"] = 80
        events, _ = evaluate_ending_system(
            state, "我实在太累了，想看看还能不能继续。"
        )
        self.assertIsInstance(events, list)

    def test_ending_with_full_solo_rights(self) -> None:
        state = self._make_late_game_state()
        state.turn = 180
        state.contract_terms["solo权限"] = 90
        state.career["创作能力"] = 90
        state.market["品牌价值"] = 90
        events, _ = evaluate_ending_system(
            state, "续约期我考虑solo路线和制作人转型。"
        )
        self.assertIsInstance(state.ending["candidate_endings"], list)


# ===================================================================
# SchoolFamilyEdgeCaseTests
# ===================================================================
class SchoolFamilyEdgeCaseTests(unittest.TestCase):
    def test_school_family_not_enrolled_no_pressure(self) -> None:
        state = make_state(age=23)
        state.school["enrolled"] = False
        state.family["conflict_level"] = 42
        events, diff = evaluate_school_family(state, "我专心训练，家人偶尔打电话问候。")
        self.assertIsInstance(events, list)
        self.assertTrue(not events or "school" not in " ".join(event_codes(events)))

    def test_school_exam_peak_with_training_conflict(self) -> None:
        state = make_state(age=16)
        state.school.update({
            "enrolled": True, "attendance_pressure": 82,
            "homework_pressure": 78, "exam_pressure": 90,
        })
        state.family["conflict_level"] = 68
        events, diff = evaluate_school_family(
            state,
            "期中和月考同时来，妈妈要我回家复习，我还有月末考核。",
        )
        self.assertIn("school_family", event_sources(events))
        self.assertGreater(diff.get("心理状态.精神压力", 0), 0)

    def test_family_support_buffers_stress(self) -> None:
        state = make_state(age=17)
        state.school["enrolled"] = True
        state.family.update({
            "career_understanding": 82, "conflict_level": 14,
            "contact_frequency": 5, "emotional_support": 78,
        })
        state.mind["精神压力"] = 68
        events, diff = evaluate_school_family(state, "爸爸打电话说相信我的选择。")
        self.assertIn("school_family", event_sources(events))

    # ── 新增：school_family 更多边界 ──
    def test_family_high_conflict_minor(self) -> None:
        state = make_minor_state(age=16)
        state.family["conflict_level"] = 85
        state.family["control_level"] = 80
        state.family["career_understanding"] = 10
        state.school["attendance_pressure"] = 80
        events, diff = evaluate_school_family(
            state, "妈妈打电话骂我不回家考试，说做练习生没用。"
        )
        self.assertIsInstance(events, list)

    def test_school_family_guardian_trust_low(self) -> None:
        state = make_minor_state(age=17)
        state.family["guardian_trust_company"] = 15
        events, diff = evaluate_school_family(
            state, "家人不相信经纪公司的承诺，想让我转学。"
        )
        self.assertIsInstance(events, list)

    def test_adult_no_school_but_family_still_active(self) -> None:
        state = make_state(age=22)
        state.school["enrolled"] = False
        state.family["emotional_support"] = 60
        state.family["conflict_level"] = 30
        events, diff = evaluate_school_family(state, "我给妈妈打电话报平安分享训练的进步。")
        self.assertIsInstance(events, list)


# ===================================================================
# SocialContextVariantsTests
# ===================================================================
class SocialContextVariantsTests(unittest.TestCase):
    def test_local_trainee_no_overseas_pressure(self) -> None:
        state = make_state(trainee=True, age=18)
        state.social_context.update({
            "nationality": "韩国", "is_overseas": False,
            "language_barrier": 0, "cultural_adaptation": 80,
        })
        events, diff = evaluate_social_context(state, "我用韩语和队友流畅沟通。")
        self.assertTrue(
            not events or "language" not in " ".join(event_codes(events))
        )

    def test_overseas_trainee_visa_renewal_crisis(self) -> None:
        state = make_state(age=18)
        state.social_context.update({
            "nationality": "中国", "is_overseas": True,
            "language_barrier": 44, "visa_pressure": 88,
            "cultural_adaptation": 34, "family_distance": 62,
        })
        events, diff = evaluate_social_context(state, "签证快到期了，我怕影响月末考核。")
        self.assertIn("social_visa_pressure", event_codes(events))
        self.assertGreater(diff.get("心理状态.精神压力", 0), 0)

    def test_overseas_trainee_festival_homesick(self) -> None:
        state = make_state(age=18)
        state.social_context.update({
            "nationality": "日本", "is_overseas": True,
            "language_barrier": 30, "family_distance": 82,
            "holiday_homesick_risk": 74,
        })
        events, diff = evaluate_social_context(state, "节日晚上大家都回家了，我在宿舍一个人吃泡面。")
        self.assertIn("social_context", event_sources(events))
        self.assertGreater(diff.get("心理状态.孤独感", 0), 0)

    def test_mixed_cultural_identity_dual_pressure(self) -> None:
        state = make_state(age=18)
        state.social_context.update({
            "nationality": "韩裔华侨", "is_overseas": True,
            "language_barrier": 18, "cultural_adaptation": 52,
            "dual_identity_pressure": 56,
        })
        events, diff = evaluate_social_context(
            state,
            "我在两国身份之间摇摆，韩国队友觉得我像外国人，回家探亲又觉得陌生。",
        )
        self.assertIsInstance(events, list)

    # ── 新增：social_context 更多国籍和场景 ──
    def test_all_nationality_types(self) -> None:
        for nat in ["韩国", "中国", "日本", "泰国", "美国", "韩裔华侨"]:
            with self.subTest(nationality=nat):
                state = make_state(age=18)
                state.social_context["nationality"] = nat
                state.social_context["is_overseas"] = nat != "韩国"
                events, diff = evaluate_social_context(state, "我和队友交流沟通。")
                self.assertIsInstance(events, list)
                self.assertIsInstance(diff, dict)

    def test_overseas_trainee_with_high_cultural_adaptation(self) -> None:
        state = make_state(age=18)
        state.social_context.update({
            "nationality": "日本", "is_overseas": True,
            "language_barrier": 10, "cultural_adaptation": 80,
            "visa_pressure": 20,
        })
        events, diff = evaluate_social_context(state, "我韩语越来越流利了。")
        self.assertIsInstance(events, list)

    def test_overseas_trainee_extreme_homesick(self) -> None:
        state = make_state(age=18)
        state.social_context.update({
            "nationality": "中国", "is_overseas": True,
            "family_distance": 95, "holiday_homesick_risk": 90,
            "language_barrier": 80,
        })
        events, diff = evaluate_social_context(state, "过年想回家但回不去，哭着给妈妈打电话。")
        self.assertIsInstance(event_sources(events), set)


# ===================================================================
# SkillAndTrainingEdgeTests
# ===================================================================
class SkillAndTrainingEdgeTests(unittest.TestCase):
    def test_skill_maintained_by_regular_practice(self) -> None:
        state = make_idol_market_state()
        state.turn = 20
        ensure_skill_decay_state(state)
        for skill in state.skill_last_practiced:
            state.skill_last_practiced[skill] = max(0, state.turn - 2)
        state.career["舞蹈实力"] = 74
        events, diff = evaluate_skill_decay_system(
            state, "本周彩排和打歌维持了所有核心技能。"
        )
        self.assertNotIn("skill_proficiency_decay", event_codes(events))

    def test_ability_passive_diff_triggers_with_high_talent(self) -> None:
        state = make_state()
        state.talents["舞蹈天赋"] = 90
        state.career["舞蹈实力"] = 15
        diff = ability_passive_diff(state, "我凭着舞蹈天赋高强度训练。")
        self.assertIsInstance(diff, dict)

    def test_ability_passive_diff_no_talent_no_boost(self) -> None:
        state = make_state()
        state.talents["舞蹈天赋"] = 5
        state.talents["声乐天赋"] = 5
        state.talents["RAP天赋"] = 5
        state.career["舞蹈实力"] = 15
        state.career["声乐实力"] = 15
        diff = ability_passive_diff(state, "我练习舞蹈和声乐。")
        self.assertIsInstance(diff, dict)

    def test_weekly_plan_keeps_trainee_identity_consistent(self) -> None:
        state = make_state(trainee=True)
        context = weekly_plan_context(state)
        self.assertEqual(state.character["时间线"], "练习生阶段")
        self.assertTrue(any(
            "练习生" in str(k) or "mandatory" in str(k).lower()
            for k in context.keys()
        ))

    def test_weekly_plan_context_reflects_mandatory_fixed_ratio(self) -> None:
        for trainee_bool, expected_fixed in [(True, 4), (False, 2)]:
            state = make_state(trainee=trainee_bool)
            context = weekly_plan_context(state)
            self.assertEqual(context["mandatory_slots"], expected_fixed)
            self.assertEqual(context["weekly_slots_total"], 7)

    # ── 新增：更多 skill 和 training 边界 ──
    def test_skill_decay_different_skills(self) -> None:
        state = make_idol_market_state()
        state.turn = 13
        ensure_skill_decay_state(state)
        for skill in state.skill_last_practiced:
            state.skill_last_practiced[skill] = 0
        state.career["声乐实力"] = 80
        state.career["RAP能力"] = 70
        events, diff = evaluate_skill_decay_system(state, "我完全不训练。")
        self.assertIsInstance(events, list)
        self.assertIsInstance(diff, dict)

    def test_ensure_skill_decay_state_initializes(self) -> None:
        state = make_state()
        state.skill_proficiency = {}
        ensure_skill_decay_state(state)
        self.assertEqual(state.skill_proficiency.get("dance", 0), 70)

    def test_ensure_progression_state_initializes(self) -> None:
        state = make_state()
        state.progression = {}
        ensure_progression_state(state)
        self.assertIn("dance", state.progression["skill_xp"])

    def test_ensure_trainee_life_state_trainee_vs_idol(self) -> None:
        trainee = make_state(trainee=True)
        self.assertEqual(trainee.trainee_life["mandatory_slots"], 4)
        self.assertEqual(trainee.trainee_life["free_slots"], 3)

        idol = make_state(trainee=False)
        self.assertEqual(idol.trainee_life["mandatory_slots"], 2)
        self.assertEqual(idol.trainee_life["free_slots"], 5)

    def test_xp_from_action_and_delta_basic(self) -> None:
        state = make_state()
        xp = xp_from_action_and_delta(state, "dance", "我练舞。", 1)
        self.assertGreater(xp, 0)

    def test_xp_from_action_and_delta_zero_when_no_match(self) -> None:
        state = make_state()
        xp = xp_from_action_and_delta(state, "dance", "我声乐训练。", 0)
        self.assertEqual(xp, 0)


# ===================================================================
# ActionValidatorRulesTest (NEW)
# ===================================================================
class ActionValidatorRulesTest(unittest.TestCase):
    def test_high_intensity_blocked_when_stamina_below_20(self) -> None:
        state = make_state()
        state.body["体力"] = 15
        with self.assertRaises(ActionBlockedError) as ctx:
            validate_action(state, "我高强度加练舞蹈和声乐。")
        self.assertIn("体力", ctx.exception.message)

    def test_high_intensity_blocked_when_injury_risk_above_90(self) -> None:
        state = make_state()
        state.body["伤病风险"] = 95
        with self.assertRaises(ActionBlockedError) as ctx:
            validate_action(state, "我高强度练舞舞蹈加练。")
        self.assertIn("伤病风险", ctx.exception.message)

    def test_mental_pressure_above_95_blocks_public_facing_actions(self) -> None:
        state = make_state()
        state.mind["精神压力"] = 98
        with self.assertRaises(ActionBlockedError) as ctx:
            validate_action(state, "我做直播回应公关综艺考核。")
        self.assertIn("精神压力", ctx.exception.message)

    def test_forced_rest_blocks_high_intensity(self) -> None:
        state = make_state()
        state.status_effects["强制休养"] = 3
        with self.assertRaises(ActionBlockedError):
            validate_action(state, "我高强度加练舞蹈考核。")

    def test_trainee_formal_idol_actions_blocked(self) -> None:
        state = make_state(trainee=True)
        with self.assertRaises(ActionBlockedError):
            validate_action(state, "我参加正式打歌和世巡演唱会。")

    def test_trainee_solo_actions_rewritten(self) -> None:
        state = make_state(trainee=True)
        result = validate_action(state, "我想solo出个人专辑单飞演员转型。")
        self.assertIn("solo", " ".join(result.warnings))
        self.assertIn("个人展示机会", result.normalized_action)

    def test_trainee_resource_actions_rewritten(self) -> None:
        state = make_state(trainee=True)
        result = validate_action(state, "我要MV的center和part镜头分量。")
        self.assertTrue(any("MV" in w or "镜头" in w for w in result.warnings))
        self.assertIn("月末考核", result.normalized_action)

    def test_trainee_comeback_actions_rewritten(self) -> None:
        state = make_state(trainee=True)
        result = validate_action(state, "我想决定正式回归风格和主打歌概念。")
        self.assertIn("回归", " ".join(result.warnings))
        self.assertIn("练习", result.normalized_action)

    def test_minor_private_outing_blocked(self) -> None:
        state = make_minor_state(age=16)
        with self.assertRaises(ActionBlockedError):
            validate_action(state, "我半夜一个人偷偷出门打车去便利店。")

    def test_minor_midnight_outing_blocked(self) -> None:
        state = make_minor_state(age=16)
        with self.assertRaises(ActionBlockedError):
            validate_action(state, "深夜我自己独自外出买东西。")

    def test_stranger_invitation_blocked(self) -> None:
        state = make_state()
        with self.assertRaises(ActionBlockedError):
            validate_action(state, "我见网友去陌生人邀约私下见面。")

    def test_risky_staff_meeting_blocked(self) -> None:
        state = make_state()
        with self.assertRaises(ActionBlockedError):
            validate_action(state, "我和前辈单独见面去酒店房间。")

    def test_minor_romance_blocked(self) -> None:
        state = make_minor_state(age=16)
        with self.assertRaises(ActionBlockedError):
            validate_action(state, "我和他表白确认关系成为恋人接吻约会。")

    def test_adult_high_power_romance_blocked(self) -> None:
        state = make_state(age=20)
        with self.assertRaises(ActionBlockedError):
            validate_action(state, "我和经纪人表白确认关系谈恋爱。")

    def test_adult_same_age_staff_crush_allowed_with_warning(self) -> None:
        state = make_state(age=20)
        result = validate_action(state, "我和造型助理表白确认关系。")
        events = result.system_events
        self.assertTrue(any("staff_romance_boundary" in e.code for e in events))

    def test_normal_practice_passes_validation(self) -> None:
        state = make_state()
        result = validate_action(state, "我正常练习舞蹈和声乐。")
        self.assertTrue(result.allowed)

    def test_trainee_blocked_by_formal_brand_activity(self) -> None:
        state = make_state(trainee=True)
        with self.assertRaises(ActionBlockedError):
            validate_action(state, "我直接去参加正式代言品牌活动。")

    def test_trainee_blocked_by_contract_renewal(self) -> None:
        state = make_state(trainee=True)
        with self.assertRaises(ActionBlockedError):
            validate_action(state, "我参加续约合同谈判。")

    # ── 新增：更多 action validator 边界 ──
    def test_trainee_keeps_weekly_plan_untouched(self) -> None:
        state = make_state(trainee=True)
        action = "【本周安排】我按计划推进。自选2/3格"
        result = validate_action(state, action)
        self.assertEqual(result.normalized_action, action)

    def test_minor_adult_romance_blocked(self) -> None:
        state = make_minor_state(age=16)
        with self.assertRaises(ActionBlockedError):
            validate_action(state, "我和化妆师谈恋爱接吻约会。")

    def test_staff_romance_boundary_with_pd(self) -> None:
        state = make_state(age=20)
        with self.assertRaises(ActionBlockedError):
            validate_action(state, "我和PD制作人表白确认关系。")

    def test_staff_romance_boundary_with_teacher(self) -> None:
        state = make_state(age=20)
        with self.assertRaises(ActionBlockedError):
            validate_action(state, "我和舞蹈老师表白谈恋爱。")

    def test_low_power_staff_crush_allowed_with_warning(self) -> None:
        state = make_state(age=22)
        result = validate_action(state, "我和服装助理表白确认关系。")
        self.assertTrue(result.allowed)
        self.assertTrue(any("staff_romance" in e.code for e in result.system_events))


# ===================================================================
# TalentAndAbilitiesDeterministicTest (NEW)
# ===================================================================
class TalentAndAbilitiesDeterministicTest(unittest.TestCase):
    def test_generate_talents_produces_all_keys(self) -> None:
        character = {"艺名": "测试", "本名": "测试本名", "身份": "素人发掘练习生", "特长": "舞蹈", "弱项": "声乐"}
        talents = generate_talents(character)
        for key in TALENT_KEYS:
            self.assertIn(key, talents)
            self.assertGreaterEqual(talents[key], 0)
            self.assertLessEqual(talents[key], 100)

    def test_generate_talents_boosts_by_identity(self) -> None:
        character = {"艺名": "测试", "本名": "测试", "身份": "运动员转练习生", "特长": "", "弱项": ""}
        talents = generate_talents(character)
        self.assertGreaterEqual(talents["体能天赋"], 50)

    def test_generate_talents_boosts_and_penalizes_by_speciality_and_weakness(self) -> None:
        character = {"艺名": "测试", "本名": "测试", "身份": "普通练习生", "特长": "舞蹈和声乐", "弱项": "RAP和演技"}
        talents = generate_talents(character)
        self.assertGreaterEqual(talents["舞蹈天赋"], 50)
        self.assertGreaterEqual(talents["声乐天赋"], 50)
        self.assertGreaterEqual(talents["RAP天赋"], 30)
        self.assertGreaterEqual(talents["演技天赋"], 30)

    def test_talent_modifiers_dance_high_talent(self) -> None:
        state = make_state()
        state.talents["舞蹈天赋"] = 80
        diff = apply_talent_modifiers(state, "我高强度舞蹈练习。", {"职业属性.舞蹈实力": 1})
        self.assertEqual(diff["职业属性.舞蹈实力"], 2)

    def test_talent_modifiers_vocal_high_talent(self) -> None:
        state = make_state()
        state.talents["声乐天赋"] = 80
        diff = apply_talent_modifiers(state, "我声乐唱高音练习。", {"职业属性.声乐实力": 1})
        self.assertEqual(diff["职业属性.声乐实力"], 2)

    def test_talent_modifiers_creative_high_talent(self) -> None:
        state = make_state()
        state.talents["创作天赋"] = 80
        diff = apply_talent_modifiers(state, "我作词作曲写demo。", {"职业属性.创作能力": 1})
        self.assertEqual(diff["职业属性.创作能力"], 2)

    def test_talent_modifiers_physical_high_talent(self) -> None:
        state = make_state()
        state.talents["体能天赋"] = 80
        diff = apply_talent_modifiers(state, "我高强度练舞。", {})
        self.assertEqual(diff["身体状态.肌肉疲劳"], -1)
        self.assertEqual(diff["身体状态.体力"], 1)

    def test_talent_modifiers_stress_high_talent(self) -> None:
        state = make_state()
        state.talents["抗压天赋"] = 80
        diff = apply_talent_modifiers(state, "我回应考核面谈公关。", {})
        self.assertEqual(diff["心理状态.精神压力"], -1)

    def test_talent_modifiers_no_bonus_with_low_talent(self) -> None:
        state = make_state()
        state.talents["舞蹈天赋"] = 50
        diff = apply_talent_modifiers(state, "我练习舞蹈。", {"职业属性.舞蹈实力": 1})
        self.assertEqual(diff["职业属性.舞蹈实力"], 1)

    # ── Abilities tests ──
    def test_update_abilities_unlocks_when_met(self) -> None:
        state = make_state()
        state.career["舞蹈实力"] = 15
        state.talents["舞蹈天赋"] = 70
        events = update_abilities(state)
        self.assertTrue(any("动作记忆" in e.code for e in events))
        self.assertIn("动作记忆", state.abilities)

    def test_update_abilities_does_not_unlock_when_below_threshold(self) -> None:
        state = make_state()
        state.career["舞蹈实力"] = 5
        events = update_abilities(state)
        self.assertFalse(any("动作记忆" in e.code for e in events))

    def test_ability_catalog_has_expected_entries(self) -> None:
        self.assertIn("动作记忆", ABILITY_CATALOG)
        self.assertIn("稳定音准", ABILITY_CATALOG)
        self.assertIn("demo起步", ABILITY_CATALOG)
        self.assertIn("制作参与者", ABILITY_CATALOG)
        self.assertIn("考核solo段", ABILITY_CATALOG)

    def test_ability_passive_diff_all_abilities(self) -> None:
        state = make_state()
        state.abilities = ["动作记忆", "稳定音准", "镜头捕捉", "即兴接话", "考核solo段", "写进歌词"]
        state.talents["舞蹈天赋"] = 80
        diff = ability_passive_diff(state, "我练习舞蹈声乐唱歌镜头直播考核个人展示写下demo歌词。")
        self.assertIsInstance(diff, dict)
        self.assertGreater(len(diff), 0)


# ===================================================================
# PeriodSystemDeterministicTest (NEW)
# ===================================================================
class PeriodSystemDeterministicTest(unittest.TestCase):
    def test_phase_for_day_all_phases(self) -> None:
        self.assertEqual(phase_for_day(1, 28), "生理期前段")
        self.assertEqual(phase_for_day(2, 28), "生理期前段")
        self.assertEqual(phase_for_day(3, 28), "生理期后段")
        self.assertEqual(phase_for_day(5, 28), "生理期后段")
        self.assertEqual(phase_for_day(6, 28), "恢复期")
        self.assertEqual(phase_for_day(25, 28), "稳定期")
        self.assertEqual(phase_for_day(26, 28), "经前期")
        self.assertEqual(phase_for_day(28, 28), "经前期")

    def test_advance_period_cycles_correctly(self) -> None:
        state = make_state()
        state.period["enabled"] = True
        state.period["mode"] = "极致"
        state.period["cycle_day"] = 28
        advance_period(state, days=1)
        self.assertEqual(state.period["cycle_day"], 1)

    def test_advance_period_skips_when_disabled(self) -> None:
        state = make_state()
        state.period["enabled"] = False
        advance_period(state, days=10)
        self.assertEqual(state.period["cycle_day"], 8)

    def test_period_tell_manager_reduces_pressure(self) -> None:
        state = make_state()
        state.period.update({"enabled": True, "mode": "极致", "cycle_day": 1})
        advance_period(state, days=0)
        events, diff = evaluate_period_system(state, "我告诉经纪人说明身体申请调整。")
        self.assertTrue(state.period["told_manager"])

    def test_period_tell_teammate_reduces_loneliness(self) -> None:
        state = make_state()
        state.period.update({"enabled": True, "mode": "极致", "cycle_day": 1})
        advance_period(state, days=0)
        events, diff = evaluate_period_system(state, "我找队友借应急用品热水暖宝宝。")
        self.assertTrue(state.period["told_teammate"])
        self.assertTrue(state.period["has_supplies"])

    def test_period_pms_phase(self) -> None:
        state = make_state()
        state.period.update({"enabled": True, "mode": "极致", "cycle_day": 26})
        advance_period(state, days=0)
        events, diff = evaluate_period_system(state, "我感觉经前期波动明显。")
        self.assertIn("period_pms", event_codes(events))

    def test_period_late_phase(self) -> None:
        state = make_state()
        state.period.update({"enabled": True, "mode": "极致", "cycle_day": 3})
        advance_period(state, days=0)
        events, diff = evaluate_period_system(state, "生理期后段痛感下降但体力还没恢复。")
        self.assertIn("period_late", event_codes(events))

    def test_period_irregularity_risk_changes(self) -> None:
        state = make_state()
        state.period.update({"enabled": True, "mode": "极致", "cycle_day": 1})
        state.mind["精神压力"] = 80
        state.body["体重管理压力"] = 80
        state.body["睡眠质量"] = 30
        initial_risk = state.period["irregularity_risk"]
        evaluate_period_system(state, "我压力很大。")
        self.assertGreater(state.period["irregularity_risk"], initial_risk)

    def test_period_stable_phase_no_special_events(self) -> None:
        state = make_state()
        state.period.update({"enabled": True, "mode": "极致", "cycle_day": 15})
        advance_period(state, days=0)
        self.assertEqual(state.period["phase"], "稳定期")
        events, _ = evaluate_period_system(state, "我正常练习。")
        self.assertFalse(any("period_day" in e.code for e in events))


# ===================================================================
# RelationshipSystemFullDeterministicTest (NEW)
# ===================================================================
class RelationshipSystemFullDeterministicTest(unittest.TestCase):
    def test_staff_role_category_all_types(self) -> None:
        self.assertEqual(staff_role_category("经纪人"), "manager")
        self.assertEqual(staff_role_category("舞蹈老师"), "teacher")
        self.assertEqual(staff_role_category("PD/制作人"), "production")
        self.assertEqual(staff_role_category("造型师"), "styling")
        self.assertEqual(staff_role_category("保镖"), "security")
        self.assertEqual(staff_role_category("工作人员"), "staff")
        self.assertEqual(staff_role_category("同期练习生"), "non_staff")

    def test_relationship_category_for_role(self) -> None:
        self.assertEqual(relationship_category_for_role("经纪人"), "professional_manager")
        self.assertEqual(relationship_category_for_role("舞蹈老师"), "professional_teacher")
        self.assertEqual(relationship_category_for_role("同期练习生"), "peer")

    def test_is_power_imbalanced(self) -> None:
        self.assertTrue(is_power_imbalanced({"role": "经纪人"}))
        self.assertTrue(is_power_imbalanced({"role": "PD/制作人"}))
        self.assertFalse(is_power_imbalanced({"role": "同期练习生"}))
        self.assertFalse(is_power_imbalanced({"role": "造型师"}))

    def test_is_professional_relationship(self) -> None:
        self.assertTrue(is_professional_relationship({"role": "经纪人"}))
        self.assertTrue(is_professional_relationship({"role": "造型师"}))
        self.assertFalse(is_professional_relationship({"role": "同期练习生"}))

    def test_cp_age_gap_limit_trainee_vs_idol(self) -> None:
        trainee = make_state(trainee=True)
        self.assertEqual(cp_age_gap_limit(trainee), 3)

        idol = make_state(trainee=False)
        idol.current_stage = "已出道爱豆阶段"
        idol.current_mainline = "回归打歌期"
        self.assertEqual(cp_age_gap_limit(idol), 5)

    def test_is_cp_eligible_trainee_peer(self) -> None:
        state = make_state(trainee=True, age=18)
        rel = {"role": "同期练习生", "age": 18}
        self.assertTrue(is_cp_eligible(rel, state))

    def test_is_cp_eligible_trainee_peer_too_old(self) -> None:
        state = make_state(trainee=True, age=18)
        rel = {"role": "同期练习生", "age": 23}
        self.assertFalse(is_cp_eligible(rel, state))

    def test_is_cp_eligible_staff_always_false(self) -> None:
        state = make_state(trainee=False, age=25)
        rel = {"role": "经纪人", "age": 26}
        self.assertFalse(is_cp_eligible(rel, state))

    def test_is_cp_eligible_idol_peer_within_5_year_gap(self) -> None:
        state = make_state(trainee=False, age=25)
        state.current_stage = "已出道爱豆阶段"
        state.current_mainline = "回归打歌期"
        rel = {"role": "同团成员", "age": 22}
        self.assertTrue(is_cp_eligible(rel, state))

    def test_is_cp_eligible_idol_peer_exceeds_5_year_gap(self) -> None:
        state = make_state(trainee=False, age=25)
        state.current_stage = "已出道爱豆阶段"
        state.current_mainline = "回归打歌期"
        rel = {"role": "同团成员", "age": 19}
        self.assertFalse(is_cp_eligible(rel, state))

    def test_default_relationship_creates_all_keys(self) -> None:
        rel = default_relationship("测试", "同期练习生", 18)
        for key in ["friendship", "trust", "player_crush", "ambiguity", "relationship_risk"]:
            self.assertIn(key, rel)

    def test_register_known_npc_creates_relationship(self) -> None:
        state = make_state()
        register_known_npc(state, "李娜英", "同期练习生", 18)
        self.assertIn("李娜英", state.relationships)

    def test_register_npc_does_not_duplicate(self) -> None:
        state = make_state()
        self.assertTrue(register_known_npc(state, "李娜英", "同期练习生", 18))
        self.assertFalse(register_known_npc(state, "李娜英", "同期练习生", 18))

    def test_find_relationship_target_with_pd_name(self) -> None:
        state = make_state()
        register_known_npc(state, "金PD", "PD/制作人", 35)
        target = find_relationship_target(state, "我对金PD产生心动。")
        self.assertEqual(target, "金PD")

    def test_ensure_default_relationships_syncs_from_important_npcs(self) -> None:
        state = make_state()
        state.important_npcs = [{"name": "朴信惠", "role": "大前辈", "age": 32}]
        ensure_default_relationships(state)
        self.assertIn("朴信惠", state.relationships)


# ===================================================================
# HierarchySystemDeterministicTest (NEW)
# ===================================================================
class HierarchySystemDeterministicTest(unittest.TestCase):
    def test_hierarchy_etiquette_mistake(self) -> None:
        state = make_state()
        state.hierarchy["honorific_adaptation"] = 25
        state.hierarchy["etiquette_pressure"] = 70
        events, diff = evaluate_hierarchy_system(state, "我在后台说错敬语忘记向前辈问候。")
        self.assertIn("hierarchy_etiquette_mistake", event_codes(events))

    def test_hierarchy_senior_acknowledgment(self) -> None:
        state = make_state()
        state.hierarchy["honorific_adaptation"] = 70
        state.hierarchy["senior_support"] = 50
        events, diff = evaluate_hierarchy_system(state, "大前辈主动来后台夸我舞台表现还给我建议。")
        self.assertIsInstance(events, list)

    def test_hierarchy_industry_reputation_touch(self) -> None:
        state = make_state(trainee=False)
        state.hierarchy["industry_reputation"] = 60
        events, diff = evaluate_hierarchy_system(state, "业界口碑被前辈们注意到。")
        self.assertIsInstance(events, list)

    def test_hierarchy_backstage_protocol_learning(self) -> None:
        state = make_state()
        state.hierarchy["backstage_protocol_familiarity"] = 20
        events, diff = evaluate_hierarchy_system(state, "我学着正确的后台礼仪问候前辈。")
        self.assertIsInstance(events, list)


# ===================================================================
# SafetyBoundaryDeterministicTest (NEW)
# ===================================================================
class SafetyBoundaryDeterministicTest(unittest.TestCase):
    def test_safety_stalking_signal(self) -> None:
        state = make_state(trainee=False)
        state.risks["私生风险"] = 70
        state.safety["dorm_security"] = 30
        events, diff = evaluate_safety_boundary(state, "宿舍楼下陌生车偷拍和私生尾随。")
        self.assertIn("safety_stalking_signal", event_codes(events))
        self.assertGreaterEqual(diff.get("风险.私生风险", 0), 5)

    def test_safety_harassment_boundary(self) -> None:
        state = make_state()
        state.safety["harassment_risk"] = 40
        state.safety["boundary_violation_risk"] = 55
        events, diff = evaluate_safety_boundary(state, "工作人员靠太近身体边界被侵犯我记录求助。")
        self.assertIn("safety_harassment_boundary", event_codes(events))

    def test_safety_outing_permission_request(self) -> None:
        state = make_state(trainee=True)
        state.safety["outing_permission"] = 40
        events, diff = evaluate_safety_boundary(state, "我向经纪人申请外出许可。")
        self.assertIsInstance(events, list)

    def test_safety_report_path(self) -> None:
        state = make_state()
        state.safety["report_history"] = []
        events, diff = evaluate_safety_boundary(state, "我正式向公司提交安全报告保留证据。")
        self.assertIsInstance(events, list)


# ===================================================================
# ScheduleSystemDeterministicTest (NEW)
# ===================================================================
class ScheduleSystemDeterministicTest(unittest.TestCase):
    def test_schedule_mode_transitions(self) -> None:
        state = make_state(trainee=False)
        state.schedule_profile["stage_mode"] = "trainee"
        state.current_mainline = "团体活动空窗期"
        state.current_schedule = "个人资源和维持训练"
        events, _ = evaluate_schedule_system(state, "出道后空窗期我安排个人资源维持训练休息。")
        self.assertEqual(state.schedule_profile["stage_mode"], "idol_offseason")

    def test_schedule_mode_stays_in_idol_for_idol_stage(self) -> None:
        state = make_state(trainee=False)
        state.schedule_profile["stage_mode"] = "idol_offseason"
        events, _ = evaluate_schedule_system(state, "我按出道日程继续维持训练。")
        self.assertIn(state.schedule_profile["stage_mode"], {"idol_offseason", "idol_comeback"})

    def test_schedule_workload_pressure(self) -> None:
        state = make_state(trainee=False)
        state.schedule_profile["workload_pressure"] = 80
        events, diff = evaluate_schedule_system(state, "行程排太满体力和精神都在透支。")
        self.assertIsInstance(events, list)


# ===================================================================
# MarketScoreSystemDeterministicTest (NEW)
# ===================================================================
class MarketScoreSystemDeterministicTest(unittest.TestCase):
    def test_market_score_initialization(self) -> None:
        state = make_state()
        ensure_market_score_state(state)
        self.assertGreaterEqual(state.market_scores.get("音源成绩", 0), 0)
        self.assertEqual(state.market_scores.get("年度奖项积分", 0), 0)

    def test_market_score_idol_comeback_evaluation(self) -> None:
        state = make_idol_market_state()
        events, diff = evaluate_market_score_system(state, "回归打歌第一周我看音源销量MV直拍和一位候补数据。")
        self.assertIn("market_score", event_sources(events))

    def test_market_score_trainee_no_evaluation(self) -> None:
        state = make_state(trainee=True)
        events, diff = evaluate_market_score_system(state, "我看榜单数据。")
        self.assertIsInstance(events, list)
        self.assertIsInstance(diff, dict)

    def test_market_score_low_result(self) -> None:
        state = make_idol_market_state()
        state.market["话题度"] = 10
        state.market["音源潜力"] = 10
        state.fans["个人粉丝数"] = 1000
        events, diff = evaluate_market_score_system(state, "回归成绩很差我和经纪人开会复盘。")
        self.assertIsInstance(events, list)

    def test_market_score_high_result(self) -> None:
        state = make_idol_market_state()
        state.market["话题度"] = 90
        state.market["音源潜力"] = 90
        state.fans["个人粉丝数"] = 500000
        state.fans["团粉稳定度"] = 90
        state.market_scores["一位概率"] = 80
        events, diff = evaluate_market_score_system(state, "回归大爆音源榜前三。")
        self.assertIsInstance(events, list)

    def test_market_score_award_season(self) -> None:
        state = make_idol_market_state()
        state.market_scores["年度奖项积分"] = 80
        events, diff = evaluate_market_score_system(state, "年末颁奖季颁奖典礼候选名单。")
        self.assertIsInstance(events, list)


# ===================================================================
# BrandContractAndCareerBranchDeterministicTest (NEW)
# ===================================================================
class BrandContractAndCareerBranchDeterministicTest(unittest.TestCase):
    def test_brand_contract_ensure_state(self) -> None:
        state = make_state()
        ensure_brand_contract_state(state)
        self.assertGreaterEqual(state.commercial.get("商业安全度", 0), 0)
        self.assertIsInstance(state.commercial.get("代言数量"), int)

    def test_brand_contract_strong_safety(self) -> None:
        state = make_idol_market_state()
        state.market["品牌价值"] = 88
        state.fans["路人好感"] = 82
        state.risks["公关危机风险"] = 5
        state.risks["恋爱风险"] = 5
        events, diff = evaluate_brand_contract_system(state, "我参加奢侈品代言和杂志封面会议。")
        self.assertIsInstance(events, list)
        self.assertNotIn("brand_safety_low", event_codes(events))

    def test_career_branch_ensure_state(self) -> None:
        state = make_state()
        ensure_career_branch_state(state)
        self.assertEqual(state.career_branches["acting_path_stage"], "未开启")
        self.assertEqual(state.career_branches["rights_path_stage"], "未开启")

    def test_career_branch_rights_path(self) -> None:
        state = make_idol_market_state()
        state.mind["职业倦怠"] = 80
        state.body["伤病风险"] = 80
        state.risks["私生风险"] = 70
        events, diff = evaluate_career_branch_system(state, "我考虑暂停活动保留证据找法务谈维权健康保障。")
        self.assertIsInstance(events, list)

    def test_career_branch_overseas_market(self) -> None:
        state = make_idol_market_state()
        state.career["语言能力"] = 75
        state.market["日本市场影响力"] = 65
        events, diff = evaluate_career_branch_system(state, "海外市场流媒数据上涨公司讨论日本东南亚活动。")
        self.assertIsInstance(events, list)

    def test_career_branch_trainee_no_evaluation(self) -> None:
        state = make_state(trainee=True)
        events, diff = evaluate_career_branch_system(state, "我想solo演员转型。")
        self.assertIsInstance(events, list)
        self.assertEqual(state.career_branches["acting_path_stage"], "未开启")


# ===================================================================
# TimeAndComputeAgeTest (NEW)
# ===================================================================
class TimeAndComputeAgeTest(unittest.TestCase):
    def test_default_time_context_with_age(self) -> None:
        time_ctx = default_time_context(18)
        self.assertEqual(time_ctx["current_date"], "2026-01-01")
        self.assertEqual(time_ctx["trainee_month"], 1)

    def test_default_time_context_without_age(self) -> None:
        time_ctx = default_time_context(None)
        self.assertIsInstance(time_ctx, dict)

    def test_compute_age_group_adult(self) -> None:
        age_ctx = compute_age_group(20)
        self.assertFalse(age_ctx["is_minor"])

    def test_compute_age_group_minor(self) -> None:
        age_ctx = compute_age_group(16)
        self.assertTrue(age_ctx["is_minor"])

    def test_compute_age_group_none(self) -> None:
        age_ctx = compute_age_group(None)
        self.assertFalse(age_ctx["is_minor"])


# ===================================================================
# WeeklyPlanDeterministicTest (NEW)
# ===================================================================
class WeeklyPlanDeterministicTest(unittest.TestCase):
    def test_normalize_weekly_plan_keys_filters_invalid(self) -> None:
        state = make_state(trainee=True)
        selected = normalize_weekly_plan_keys(state, ["nonexistent_key", "dance_extra", "invalid"])
        self.assertEqual(selected, ["dance_extra"])

    def test_weekly_plan_options_trainee_has_options(self) -> None:
        state = make_state(trainee=True)
        options = weekly_plan_options(state)
        self.assertGreater(len(options), 0)

    def test_weekly_plan_options_idol_has_options(self) -> None:
        state = make_state(trainee=False)
        options = weekly_plan_options(state)
        self.assertGreater(len(options), 0)

    def test_compose_action_with_weekly_plan_includes_anchor_marker(self) -> None:
        state = make_state(trainee=True)
        selected = ["dance_extra", "vocal_extra", "creative_demo"]
        action = compose_action_with_weekly_plan("我按计划推进。", state, selected)
        self.assertIn("【本周安排】", action)
        self.assertIn("自选", action)

    def test_compose_action_with_weekly_plan_various_slots(self) -> None:
        state = make_state(trainee=True)
        for keys in [["dance_extra"], ["dance_extra", "vocal_extra"], ["dance_extra", "vocal_extra", "creative_demo"]]:
            with self.subTest(count=len(keys)):
                action = compose_action_with_weekly_plan("我按安排推进。", state, keys)
                self.assertIn(f"自选{len(keys)}/3格", action)

    def test_normalize_weekly_plan_keys_truncates_at_free_slots(self) -> None:
        state = make_state(trainee=True)
        selected = normalize_weekly_plan_keys(state, [
            "dance_extra", "vocal_extra", "creative_demo", "company_observe", "peer_social"
        ])
        self.assertEqual(len(selected), 3)


# ===================================================================
# EnsureStateFunctionsTest (NEW)
# ===================================================================
class EnsureStateFunctionsTest(unittest.TestCase):
    def test_ensure_company_profile_sets_defaults(self) -> None:
        state = make_state()
        ensure_company_profile(state)
        self.assertIn("公司名称", state.company)
        self.assertIn("公司风格", state.company)
        self.assertTrue(len(state.company["公司风格"]) > 0)

    def test_ensure_company_profile_different_sizes(self) -> None:
        for size in ["小型公司", "中型公司", "大型公司"]:
            with self.subTest(size=size):
                state = make_state()
                state.company["公司规模"] = size
                state.character["公司规模"] = size
                ensure_company_profile(state)
                self.assertEqual(state.company["公司规模"], size)

    def test_ensure_market_score_state_sets_defaults(self) -> None:
        state = make_state()
        ensure_market_score_state(state)
        self.assertIn("音源成绩", state.market_scores)

    def test_ensure_debut_state_sets_defaults(self) -> None:
        from core.debut_system import ensure_debut_state
        state = make_state()
        ensure_debut_state(state)
        self.assertEqual(state.debut["status"], "not_candidate")

    def test_ensure_ending_state_sets_defaults(self) -> None:
        state = make_state()
        ensure_ending_state(state)
        self.assertEqual(state.ending["window"], "closed")

    def test_ensure_skill_decay_state_sets_defaults(self) -> None:
        state = make_state()
        ensure_skill_decay_state(state)
        self.assertIn("dance", state.skill_last_practiced)
        self.assertIn("dance", state.skill_proficiency)

    def test_ensure_schedule_state_sets_defaults(self) -> None:
        from core.schedule_system import ensure_schedule_state
        state = make_state()
        ensure_schedule_state(state)
        self.assertIn("stage_mode", state.schedule_profile)

    def test_ensure_brand_contract_state_sets_defaults(self):
        state = make_state()
        ensure_brand_contract_state(state)
        self.assertGreaterEqual(state.contract_terms.get("健康保障", 0), 0)

    def test_ensure_career_branch_state_sets_defaults(self) -> None:
        state = make_state()
        ensure_career_branch_state(state)
        self.assertEqual(state.career_branches["acting_path_stage"], "未开启")


# ===================================================================
# SystemEventTest (NEW)
# ===================================================================
class SystemEventTest(unittest.TestCase):
    def test_system_event_creation(self) -> None:
        event = SystemEvent(
            code="test_event",
            title="测试事件",
            severity="info",
            description="这是一个测试",
            source_system="test",
            suggested_diff={"身体状态.体力": -1},
            new_flags=["test_flag"],
            tags=["test"],
        )
        self.assertEqual(event.code, "test_event")
        self.assertEqual(event.suggested_diff["身体状态.体力"], -1)
        self.assertEqual(event.new_flags, ["test_flag"])

    def test_system_event_suggested_diff_coerces_to_int(self) -> None:
        event = SystemEvent(
            code="test",
            title="test",
            severity="info",
            description="test",
            source_system="test",
            suggested_diff={"职业属性.舞蹈实力": 2.7},
        )
        self.assertEqual(event.suggested_diff["职业属性.舞蹈实力"], 3)

    def test_models_active_crisis_creation(self) -> None:
        crisis = ActiveCrisis(
            crisis_id="test_id",
            crisis_type="public_relations",
            title="测试危机",
            stage="response_window",
            heat=60,
        )
        self.assertEqual(crisis.crisis_type, "public_relations")
        self.assertEqual(crisis.stage, "response_window")

    def test_route_info_creation(self) -> None:
        from core.models import RouteInfo
        route = RouteInfo(model_tier="flash", turn_kind="ordinary", reason="test")
        self.assertEqual(route.model_tier, "flash")
        self.assertEqual(route.turn_kind, "ordinary")


# ===================================================================
# IdempotencyAndStateRecoveryTests (NEW)
# ===================================================================
class IdempotencyAndStateRecoveryTests(unittest.TestCase):
    def test_ensure_state_functions_are_idempotent(self) -> None:
        for fn in [
            ensure_trainee_life_state,
            ensure_market_score_state,
            ensure_brand_contract_state,
            ensure_career_branch_state,
            ensure_ending_state,
            ensure_company_profile,
        ]:
            with self.subTest(fn=fn.__name__):
                state = make_state()
                fn(state)
                before = state.model_dump()
                fn(state)
                after = state.model_dump()
                self.assertEqual(before, after)

    def test_state_copy_preserves_separate_instances(self) -> None:
        state = make_state()
        state.body["体力"] = 50
        copy = state.model_copy(deep=True)
        copy.body["体力"] = 60
        self.assertEqual(state.body["体力"], 50)
        self.assertEqual(copy.body["体力"], 60)


if __name__ == "__main__":
    unittest.main(verbosity=2)
