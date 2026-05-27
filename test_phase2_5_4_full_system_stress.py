from __future__ import annotations

import json
import tempfile
import traceback
import py_compile
from pathlib import Path
from typing import Callable, Dict, List, Any

from core.models import GameState, TurnResponse, Choice, RouteInfo, SystemEvent
from core.config import AppConfig
from core.storage import SaveStorage
from core.engine import TurnEngine
from core.llm import MockProvider, parse_turn_response, LLMError
from core.prompts import build_messages
from core.character_validator import validate_character_input, CharacterValidationError
from core.initial_allocator import parse_profile_tags, allocate_initial_state
from core.talents import generate_talents, apply_talent_modifiers
from core.abilities import update_abilities, ability_passive_diff, ABILITY_CATALOG
from core.action_validator import validate_action, ActionBlockedError
from core.rules import base_diff_for_action, sanitize_suggested_diff, apply_diff, threshold_warnings
from core.systems import classify_turn, evaluate_all_systems
from core.crisis import update_crises
from core.time_system import compute_age_group, default_time_context, advance_time
from core.social_context import default_social_context, evaluate_social_context
from core.school_family import default_school_context, default_family_context, evaluate_school_family
from core.safety_boundary import default_safety_context, evaluate_safety_boundary
from core.hierarchy_system import default_hierarchy_context, evaluate_hierarchy_system
from core.period_system import default_period_state, advance_period, evaluate_period_system
from core.inner_life import default_inner_life, evaluate_inner_life, add_secret
from core.relationship_system import (
    ensure_default_relationships,
    evaluate_relationship_system,
    is_cp_eligible,
    is_same_age_staff_crush_allowed,
    professional_romance_policy,
    relationship_ui_summary,
    cp_age_gap_limit,
)


REPORT: List[Dict[str, Any]] = []


def record(name: str, category: str, ok: bool, note: str = "") -> None:
    REPORT.append({"name": name, "category": category, "ok": ok, "note": note})
    print(f"[{'PASS' if ok else 'FAIL'}] {category} :: {name}" + (f" -- {note}" if note else ""))


def assert_true(expr: bool, msg: str) -> None:
    if not expr:
        raise AssertionError(msg)


def make_character(**extra) -> Dict[str, Any]:
    raw = {
        "艺名": "Luna",
        "本名": "林娜",
        "年龄": "16",
        "身高": "166",
        "国籍": "中国",
        "身份": "海外追梦练习生",
        "时间线": "练习生阶段",
        "生理周期系统": "简化",
        "特长": "舞蹈",
        "弱项": "声乐",
        "家庭状况": "父母支持但担心学业",
        "练习生经历": "校园舞蹈社一年",
        "出身来源标签": ["校园舞蹈社"],
    }
    raw.update(extra)
    return validate_character_input(raw).data


def make_state(age: int = 18, stage: str = "练习生阶段", mainline: str = "初入公司") -> GameState:
    state = GameState(current_stage=stage, current_mainline=mainline, current_schedule="普通行程")
    state.character = {"年龄": age, "国籍": "中国", "身份": "海外追梦练习生", "时间线": stage}
    state.age_context = compute_age_group(age)
    state.time = default_time_context(age)
    state.social_context = default_social_context(state.character)
    state.school = default_school_context(state.age_context, state.character)
    state.family = default_family_context(state.age_context, {"家庭状况": "父母支持但担心学业"}, state.social_context)
    state.safety = default_safety_context(state.age_context)
    state.hierarchy = default_hierarchy_context(state.social_context)
    state.period = default_period_state(enabled=True, mode="简化")
    state.inner_life = default_inner_life()
    ensure_default_relationships(state)
    return state


def make_engine():
    tmp = tempfile.TemporaryDirectory()
    storage = SaveStorage(Path(tmp.name) / "saves.db")
    config = AppConfig()
    engine = TurnEngine(storage, config, use_mock=True)
    return tmp, storage, config, engine


def peer(name: str, age: int, role: str = "练习生") -> Dict[str, Any]:
    return {
        "name": name,
        "role": role,
        "age": age,
        "public_relation_state": "普通同期",
        "private_relation_state": "普通同期",
        "friendship": 20,
        "trust": 20,
        "dependence": 0,
        "intimacy_comfort": 10,
        "rivalry": 20,
        "boundary_clarity": 50,
        "care_memory": 0,
        "shared_secret": 0,
        "player_crush": 0,
        "player_misread_probability": 10,
        "player_expectation": 0,
        "fear_of_ruining_friendship": 10,
        "npc_romantic_interest_hidden": 20,
        "npc_boundary_hidden": 60,
        "ambiguity": 0,
        "business_cp_level": 0,
        "cp_fandom_pressure": 0,
        "relationship_risk": 0,
        "last_signals": [],
        "observed_clues": [],
        "confirmed_state": "未确认",
    }


def run_test(name: str, category: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        record(name, category, True)
    except Exception as exc:
        record(name, category, False, f"{type(exc).__name__}: {exc}")
        traceback.print_exc()
        raise


def test_static_integrity() -> None:
    root = Path(__file__).resolve().parent
    required_files = [
        "app.py",
        "core/models.py",
        "core/engine.py",
        "core/action_validator.py",
        "core/rules.py",
        "core/systems.py",
        "core/crisis.py",
        "core/relationship_system.py",
        "core/time_system.py",
        "core/period_system.py",
        "core/inner_life.py",
        "data/system_prompt.md",
        "data/modules/00_core_rules.md",
        "data/modules/01_output_contract.md",
        "data/modules/02_stage_gate.md",
        "data/modules/03_attribute_sources.md",
        "data/modules/04_crisis_lifecycle.md",
        "data/modules/05_talent_system.md",
        "data/modules/06_tone.md",
        "data/modules/07_initial_allocation_and_abilities.md",
        "data/modules/08_period_system.md",
        "data/modules/09_inner_life_system.md",
        "data/modules/10_relationship_system.md",
        "data/modules/11_time_age_school_safety_hierarchy.md",
    ]
    for rel in required_files:
        assert_true((root / rel).exists(), f"missing file: {rel}")

    for py in list((root / "core").glob("*.py")) + [root / "app.py"]:
        py_compile.compile(str(py), doraise=True)


def test_character_validation_and_profiles() -> None:
    invalid_cases = [
        {"艺名": "", "本名": "", "年龄": "18", "身高": "166", "身份": "素人", "时间线": "练习生阶段"},
        {"艺名": "A", "年龄": "abc", "身高": "166", "身份": "素人", "时间线": "练习生阶段"},
        {"艺名": "A", "年龄": "18", "身高": "90", "身份": "素人", "时间线": "练习生阶段"},
        {"艺名": "A", "年龄": "18", "身高": "166", "身份": "", "时间线": "练习生阶段"},
        {"艺名": "A", "年龄": "18", "身高": "166", "身份": "素人", "时间线": "练习生阶段", "特长": "舞蹈", "弱项": "舞蹈"},
    ]
    for raw in invalid_cases:
        try:
            validate_character_input(raw)
            raise AssertionError(f"invalid character passed: {raw}")
        except CharacterValidationError:
            pass

    char = make_character(年龄="16岁", 身高="166cm")
    assert_true(char["年龄"] == 16 and char["身高"] == 166, "age/height normalization failed")
    tags = parse_profile_tags({**char, "身份": "前运动员转型 海外练习生 选秀淘汰者", "特长": "舞蹈作词", "弱项": "韩语声乐"})
    for tag in ["前运动员", "海外练习生", "选秀淘汰者", "舞蹈基础", "创作兴趣", "语言短板", "声乐短板"]:
        assert_true(tag in tags, f"missing tag: {tag}")


def test_initial_allocation_and_contexts() -> None:
    _, _, _, engine = make_engine()
    cases = [
        make_character(身份="素人学生被星探发现", 时间线="练习生阶段", 年龄="16"),
        make_character(身份="前运动员转型", 时间线="练习生阶段", 年龄="17", 出身来源标签=["运动员"]),
        make_character(身份="选秀节目淘汰者", 时间线="练习生阶段", 年龄="18", 出身来源标签=["选秀节目淘汰者"]),
        make_character(身份="小公司再出道", 时间线="练习生阶段", 年龄="20", 出身来源标签=["再出道"]),
        make_character(身份="正式爱豆", 时间线="回归瓶颈期", 年龄="22"),
        make_character(身份="成熟爱豆", 时间线="续约前一年", 年龄="26"),
    ]
    for char in cases:
        state = engine.create_initial_state(char)
        assert_true(state.initial_allocation_log, "allocation log empty")
        assert_true("制作人能力" in state.career, "producer ability missing")
        if "练习生" in state.current_stage:
            assert_true(state.career["制作人能力"] == 0, "trainee producer ability must start at 0")
            assert_true(max(state.career.values()) <= 20, f"trainee career too high: {state.career}")
        assert_true("age_group" in state.age_context, "age context missing")
        assert_true("current_date" in state.time, "time context missing")
        assert_true("language_barrier" in state.social_context, "social context missing")
        assert_true("honorific_adaptation" in state.hierarchy, "hierarchy context missing")


def test_storage_llm_and_prompt_contract() -> None:
    tmp, storage, config, engine = make_engine()
    state = engine.create_initial_state(make_character())
    save_id = storage.create_save(state)
    loaded = storage.load_save(save_id)
    assert_true(loaded.save_name == state.save_name, "save/load mismatch")
    assert_true(storage.latest_save_id() == save_id, "latest save mismatch")
    assert_true(storage.list_saves(), "list saves empty")

    raw = MockProvider().generate([], model="mock")
    parsed = parse_turn_response(raw)
    assert_true(parsed.choices and parsed.narrative, "mock parse failed")

    fenced = "```json\n{\"narrative\":\"x\",\"choices\":[],\"suggested_diff\":{}}\n```"
    parsed2 = parse_turn_response(fenced)
    assert_true(len(parsed2.choices) == 5, "default choices fallback failed")

    try:
        parse_turn_response("not json at all")
        raise AssertionError("invalid json should fail")
    except LLMError:
        pass

    messages = build_messages(state, "普通训练", {"职业属性.舞蹈实力": 1}, {}, [], RouteInfo(), validate_action(state, "普通训练"))
    assert_true(messages and messages[0]["role"] == "system", "prompt message structure bad")
    prompt_text = "\n".join(m["content"] for m in messages)
    for key in ["生理周期", "少女心事", "友情", "前后辈", "阶段"]:
        assert_true(key in prompt_text, f"prompt missing module content: {key}")


def test_model_routing_and_config() -> None:
    state = make_state(18)
    assert_true(classify_turn("普通训练", state).turn_kind == "ordinary", "ordinary route failed")
    assert_true(classify_turn("我要直播谈心", state).turn_kind == "focus", "focus route failed")
    assert_true(classify_turn("我要回应热搜争议", state).turn_kind == "crisis", "crisis route failed")

    idol = make_state(22, "正式爱豆阶段", "回归准备")
    assert_true(classify_turn("我要决定回归主打歌概念", idol).turn_kind == "mainline", "idol mainline route failed")

    trainee = make_state(18, "练习生阶段", "初入公司")
    assert_true(classify_turn("我要参加大赏", trainee).turn_kind in {"focus", "crisis"}, "trainee formal route should be degraded/focus")

    cfg = AppConfig()
    cfg.model_policy = "auto"
    assert_true(isinstance(cfg.model_for_tier("pro"), str) and cfg.model_for_tier("pro"), "config auto model mapping failed")
    cfg.model_policy = "flash"
    assert_true(cfg.model_for_tier("pro") == cfg.flash_model, "flash policy failed")
    cfg.model_policy = "pro"
    assert_true(cfg.model_for_tier("flash") == cfg.pro_model, "pro policy failed")
    cfg.model_policy = "custom"
    cfg.custom_model = "custom-test-model"
    assert_true(cfg.model_for_tier("flash") == "custom-test-model", "custom policy failed")


def test_action_validator_all_gates() -> None:
    trainee = make_state(18, "练习生阶段", "初入公司")

    rewritten = validate_action(trainee, "我要申请 MV 镜头和打歌 center")
    assert_true(rewritten.normalized_action != rewritten.original_action, "resource stage rewrite failed")
    assert_true(rewritten.system_events, "stage rewrite event missing")

    solo = validate_action(trainee, "我要 solo 单飞转型演员")
    assert_true("个人展示" in solo.normalized_action or solo.system_events, "solo rewrite failed")

    comeback = validate_action(trainee, "我想决定下一次回归风格，提交自己的 demo")
    assert_true("作词作曲训练" in comeback.normalized_action or "练习用 demo" in comeback.normalized_action, "comeback rewrite failed")

    for action in ["我要参加大赏并拿代言"]:
        try:
            validate_action(trainee, action)
            raise AssertionError(f"should be blocked: {action}")
        except ActionBlockedError:
            pass

    minor_trainee = make_state(16, "练习生阶段", "初入公司")
    for action in ["我想凌晨自己出门去便利店", "我不告诉公司去私下见一个陌生网友", "我想和工作人员单独去房间谈谈"]:
        try:
            validate_action(minor_trainee, action)
            raise AssertionError(f"should be blocked: {action}")
        except ActionBlockedError:
            pass

    low_body = make_state(18)
    low_body.body["体力"] = 15
    try:
        validate_action(low_body, "我要继续高强度练舞")
        raise AssertionError("low stamina should block")
    except ActionBlockedError:
        pass

    injured = make_state(18)
    injured.body["伤病风险"] = 95
    try:
        validate_action(injured, "我要练舞")
        raise AssertionError("injury risk should block")
    except ActionBlockedError:
        pass

    mental = make_state(18)
    mental.mind["精神压力"] = 99
    try:
        validate_action(mental, "我要直播回应争议")
        raise AssertionError("mental pressure should block")
    except ActionBlockedError:
        pass

    adult = make_state(18)
    result = validate_action(adult, "我想向同龄造型助理宋夏表白，确认关系")
    assert_true(result.allowed and result.system_events, "same-age low-power staff warning should not block but must warn")


def test_rules_diff_sanitize_apply_and_thresholds() -> None:
    state = make_state(18)
    diff = base_diff_for_action("我练舞、声乐、写demo，然后休息", state)
    assert_true("职业属性.舞蹈实力" in diff and "职业属性.声乐实力" in diff, "base diff missing training stats")

    dirty = {"职业属性.制作人能力": 99, "职业属性.舞蹈实力": 50, "不存在.字段": 100}
    clean = sanitize_suggested_diff(state, dirty, "我想参与制作")
    assert_true("职业属性.制作人能力" not in clean, "producer ability sanitization failed")

    applied = apply_diff(state, {"职业属性.舞蹈实力": 999, "身体状态.体力": -999, "不存在.字段": 5}, max_abs_delta=8)
    assert_true(applied["职业属性.舞蹈实力"][1] - applied["职业属性.舞蹈实力"][0] == 8, "positive clamp failed")
    assert_true(applied["身体状态.体力"][0] - applied["身体状态.体力"][1] == 8, "negative clamp failed")

    state.body["体力"] = 10
    state.body["伤病风险"] = 90
    state.mind["精神压力"] = 90
    warnings = threshold_warnings(state)
    assert_true(len(warnings) >= 3, "threshold warnings insufficient")


def test_talents_abilities_and_passives() -> None:
    char = make_character(特长="舞蹈声乐作词", 弱项="RAP")
    talents = generate_talents(char)
    assert_true(talents["舞蹈天赋"] > 50 and talents["声乐天赋"] > 50, "talent boost failed")
    assert_true(talents["RAP天赋"] < 50, "talent weakness failed")

    state = make_state(18)
    state.talents.update({"舞蹈天赋": 80, "声乐天赋": 80, "创作天赋": 80, "镜头天赋": 80, "综艺天赋": 80, "抗压天赋": 80})
    state.career.update({"舞蹈实力": 12, "声乐实力": 12, "创作能力": 18, "舞台感染力": 14, "综艺感": 12})
    events = update_abilities(state)
    assert_true(len(events) >= 5, f"not enough abilities unlocked: {state.abilities}")
    for ability in ["动作记忆", "稳定音准", "demo起步", "写进歌词"]:
        assert_true(ability in state.abilities, f"missing ability: {ability}")

    passive = ability_passive_diff(state, "我高强度练舞，然后写进歌词")
    assert_true("职业属性.舞蹈实力" in passive and "职业属性.创作能力" in passive, "ability passive diff failed")

    base = {"职业属性.舞蹈实力": 1}
    modified = apply_talent_modifiers(state, "练舞", base)
    assert_true(modified["职业属性.舞蹈实力"] >= 2, "talent modifier failed")


def test_core_systems_evaluator() -> None:
    state = make_state(22, "正式爱豆阶段", "回归准备")
    state.body["体力"] = 20
    state.body["伤病风险"] = 90
    state.body["嗓音状态"] = 30
    state.mind["精神压力"] = 80
    state.fans["黑粉活跃度"] = 80
    state.team["营业疲劳"] = 80
    state.team["真实关系温度"] = 20
    state.risks["恋爱风险"] = 70
    state.risks["私生风险"] = 80
    state.risks["队内不和曝光风险"] = 50
    state.comeback["制作参与等级"] = 0
    state.flags.extend(["镜头前和谐裂缝", "伤病风险临界"])

    events, diff = evaluate_all_systems(state, "我要回应公关争议，争取回归概念和center资源")
    codes = {e.code for e in events}
    expected = {
        "health_low_stamina",
        "health_injury_warning",
        "health_voice_warning",
        "mind_high_pressure",
        "resource_negotiation",
        "pr_response_window",
        "fandom_anti_high",
        "lens_harmony_crack",
        "love_risk_visible",
        "sasaeng_security_warning",
        "comeback_low_authority",
        "delayed_team_pr_risk",
        "delayed_injury_debt",
    }
    missing = expected - codes
    assert_true(not missing, f"missing system events: {missing}")
    assert_true(diff, "system diff empty")


def test_time_age_and_cp_age_gap() -> None:
    trainee = make_state(18, "练习生阶段", "初入公司")
    idol = make_state(22, "正式爱豆阶段", "回归准备")
    assert_true(cp_age_gap_limit(trainee) == 3, "trainee cp gap should be 3")
    assert_true(cp_age_gap_limit(idol) == 5, "idol cp gap should be 5")
    assert_true(is_cp_eligible(peer("T21", 21, "练习生"), trainee), "trainee +3 should allow")
    assert_true(not is_cp_eligible(peer("T22", 22, "练习生"), trainee), "trainee +4 should block")
    assert_true(is_cp_eligible(peer("I27", 27, "爱豆"), idol), "idol +5 should allow")
    assert_true(not is_cp_eligible(peer("I28", 28, "爱豆"), idol), "idol +6 should block")
    minor = make_state(17, "练习生阶段", "初入公司")
    assert_true(not is_cp_eligible(peer("Adult", 18, "练习生"), minor), "minor/adult cp should block")

    route = RouteInfo(turn_kind="ordinary")
    events, diff, days = advance_time(trainee, route, "普通训练")
    assert_true(days == 7 and trainee.time["next_evaluation_days"] == 21, "ordinary time advance failed")
    trainee.time["next_evaluation_days"] = 2
    events, diff, days = advance_time(trainee, route, "普通训练")
    assert_true(any(e.code == "time_monthly_evaluation_due" for e in events), "evaluation due event missing")
    summary_events, _, summary_days = advance_time(trainee, route, "快进一个月做月度总结")
    assert_true(summary_days == 30, "monthly summary duration failed")


def test_period_inner_life_relationships() -> None:
    state = make_state(18)

    state.period["cycle_day"] = 28
    advance_period(state, days=1)
    assert_true(state.period["phase"] == "生理期前段", "period phase advance failed")
    pe, pdiff = evaluate_period_system(state, "我生理期腹痛，还想高强度练舞并穿浅色服装拍评估录像")
    pcodes = {e.code for e in pe}
    assert_true({"period_day1_2", "period_high_intensity_risk", "period_clothing_anxiety"}.issubset(pcodes), f"period events missing: {pcodes}")

    ie, idiff = evaluate_inner_life(state, "老师没有夸我，我很想被看见，也把这些话写进歌词本")
    icodes = {e.code for e in ie}
    assert_true("inner_visible_desire" in icodes and "inner_diary_outlet" in icodes, "inner life outlet failed")
    evaluate_inner_life(state, "我发现自己很在意她看我的眼神，好像心动")
    assert_true(state.crush_threads, "crush thread not created")

    ensure_default_relationships(state)
    fe, fdiff = evaluate_relationship_system(state, "裴智秀陪我练习，还借热水，我们深夜谈心")
    assert_true(state.relationships["裴智秀"]["friendship"] > 20, "peer friendship failed")
    assert_true(state.relationships["裴智秀"]["player_crush"] == 0, "friendship should not auto-crush")

    revents, rdiff = evaluate_relationship_system(state, "我发现自己很喜欢同龄造型助理宋夏，很在意她帮我整理服装时的眼神")
    rel = state.relationships["宋夏"]
    assert_true(rel["player_crush"] > 0 and rel["professional_boundary_pressure"] > 0, "same-age staff high-risk crush failed")
    assert_true(any(e.code == "rel_same_age_staff_crush_risk" for e in revents), "staff crush risk event missing")
    assert_true("CP" not in relationship_ui_summary("宋夏", rel, state), "staff UI should not show CP")

    cp_events, cp_diff = evaluate_relationship_system(state, "公司安排我和裴智秀在镜头前营业CP互动给粉丝看")
    assert_true(state.relationships["裴智秀"]["business_cp_level"] > 0, "peer business cp failed")
    no_cp_events, _ = evaluate_relationship_system(state, "公司安排我和宋夏在镜头前营业CP互动给粉丝看")
    assert_true(state.relationships["宋夏"]["business_cp_level"] == 0, "staff should not enter CP")


def test_school_family_social_safety_hierarchy() -> None:
    state = make_state(16)
    state.time["turn_duration_days"] = 7
    se, sdiff = evaluate_school_family(state, "我这周每天高强度加练到很晚，还担心学校作业")
    assert_true(any(e.code == "school_training_conflict" for e in se), "school conflict missing")
    assert_true(state.school["attendance_pressure"] > 35, "school pressure not updated")

    fe, fdiff = evaluate_school_family(state, "我给妈妈打电话，说最近训练很累")
    assert_true(any(e.code in {"family_support_contact", "family_misunderstanding"} for e in fe), "family contact missing")

    le, ldiff = evaluate_social_context(state, "我听不懂韩语敬语，晚上很想家，想打电话")
    assert_true({"social_language_pressure", "social_homesick"}.issubset({e.code for e in le}), "social context events missing")

    he, hdiff = evaluate_hierarchy_system(state, "我在后台见到前辈，努力用敬语问候和鞠躬")
    assert_true(any(e.code == "hierarchy_etiquette_scene" for e in he), "hierarchy event missing")
    he2, hdiff2 = evaluate_hierarchy_system(state, "我忘记问候前辈，还说错敬语")
    assert_true(any(e.code == "hierarchy_etiquette_mistake" for e in he2), "hierarchy mistake missing")

    safe_e, safe_d = evaluate_safety_boundary(state, "宿舍楼下连续几天有陌生车，像是被私生跟踪偷拍")
    assert_true(any(e.code == "safety_stalking_signal" for e in safe_e), "stalking safety event missing")
    har_e, har_d = evaluate_safety_boundary(state, "工作人员让我单独去房间，我觉得身体边界很不舒服，像是骚扰")
    assert_true(any(e.code == "safety_harassment_boundary" for e in har_e), "harassment boundary event missing")
    bully_e, bully_d = evaluate_safety_boundary(state, "练习生霸凌排挤我，抢我的东西")
    assert_true(any(e.code == "safety_bullying_signal" for e in bully_e), "bullying event missing")


def test_crisis_lifecycle_all_types() -> None:
    state = make_state(22, "正式爱豆阶段", "回归准备")
    system_events = [
        SystemEvent(code="pr_response_window", title="PR", source_system="test", description="pr"),
        SystemEvent(code="health_injury_warning", title="Health", source_system="test", description="health"),
        SystemEvent(code="sasaeng_security_warning", title="Safety", source_system="test", description="safety"),
        SystemEvent(code="lens_harmony_crack", title="Team", source_system="test", description="team"),
    ]
    events, diff = update_crises(state, "我先沉默不回应，继续硬撑高强度练舞，还公开行程", system_events)
    types = {c.crisis_type for c in state.active_crises}
    assert_true({"public_relations", "health", "safety", "team_pr"}.issubset(types), f"crises not opened: {types}")

    for _ in range(3):
        events, diff = update_crises(state, "我回应澄清并提交证据，也去医院康复，告诉经纪人加强安保，公司处理", [])
    assert_true(isinstance(events, list) and isinstance(diff, dict), "crisis update structures invalid")

    # Force health crisis overheat to test status effect.
    state2 = make_state(18)
    update_crises(state2, "硬撑高强度练舞", [SystemEvent(code="health_injury_warning", title="Health", source_system="test", description="health")])
    for _ in range(4):
        update_crises(state2, "硬撑高强度练舞", [])
    assert_true("强制休养" in state2.status_effects or state2.active_crises, "health crisis did not create persistent state")


def test_engine_mock_full_flow_and_persistence() -> None:
    tmp, storage, config, engine = make_engine()
    state = engine.create_initial_state(make_character())
    save_id = storage.create_save(state)
    old_date = state.time["current_date"]

    actions = [
        "我这周每天高强度加练，也担心学校作业和韩语敬语",
        "裴智秀陪我练习，还借给我热水，我们深夜谈心",
        "老师没有夸我，我很想被看见，于是把心事写进日记",
        "我告诉经纪人身体状态，并向队友借应急用品和热水",
        "我在后台见到前辈，努力用敬语问候和鞠躬",
        "宿舍楼下连续几天有陌生车，像是被私生跟踪偷拍",
        "我发现自己很喜欢同龄造型助理宋夏，很在意她帮我整理服装时的眼神",
        "快进一个月做月度总结，我想整理训练和学校的平衡",
    ]

    for i, action in enumerate(actions, start=1):
        try:
            state, response, applied, route, events, validation = engine.run_turn(save_id, state, action)
        except ActionBlockedError as exc:
            raise AssertionError(f"unexpected blocked at {i}: {action} -> {exc.message}") from exc
        assert_true(state.turn == i, f"turn not incremented at {i}")
        assert_true(isinstance(response.narrative, str), "narrative missing")
        assert_true(state.route_history, "route history missing")
        assert_true(events, "events missing")
        assert_true(state.time["days_elapsed"] > 0, "time not advanced")

    assert_true(state.time["current_date"] != old_date, "date did not move")
    loaded = storage.load_save(save_id)
    assert_true(loaded.turn == state.turn, "saved turn mismatch")
    assert_true(len(storage.list_saves()) == 1, "save list count mismatch")
    assert_true(state.growth_history or state.system_events, "no growth/system history recorded")

    # blocked action should not advance time/turn because run_turn raises before state mutation.
    old_turn = state.turn
    old_date = state.time["current_date"]
    try:
        engine.run_turn(save_id, state, "我想凌晨自己出门去便利店")
        raise AssertionError("blocked action completed")
    except ActionBlockedError:
        assert_true(state.turn == old_turn, "blocked turn advanced")
        assert_true(state.time["current_date"] == old_date, "blocked date advanced")


def test_backfill_old_save_and_ui_summaries() -> None:
    state = make_state(18)
    state.relationships["旧经纪人"] = {
        "name": "旧经纪人",
        "role": "经纪人",
        "age": None,
        "friendship": 999,
        "trust": -50,
        "player_crush": 80,
        "ambiguity": 80,
        "business_cp_level": 99,
        "cp_fandom_pressure": 99,
    }
    ensure_default_relationships(state)
    rel = state.relationships["旧经纪人"]
    assert_true(rel["cp_eligible"] is False, "old staff cp eligibility not cleared")
    assert_true(rel["business_cp_level"] == 0 and rel["cp_fandom_pressure"] == 0, "old staff CP fields not zeroed")
    summary = relationship_ui_summary("旧经纪人", rel, state)
    assert_true("CP" not in summary, f"staff summary still shows CP: {summary}")

    lines = [relationship_ui_summary(name, r, state) for name, r in state.relationships.items()]
    for line in lines:
        if any(role in line for role in ["经纪人", "老师", "造型助理", "制作PD"]):
            assert_true("CP" not in line, f"professional UI contains CP: {line}")


def test_fuzz_action_matrix_no_weird_crash() -> None:
    state = make_state(18)
    actions = [
        "",
        "   ",
        "普通训练",
        "我练舞练到很晚",
        "我休息，睡觉，吃饭",
        "我回应热搜争议",
        "我说我想被看见，然后写日记",
        "我向队友借热水",
        "我和裴智秀营业CP",
        "我和宋夏营业CP",
        "我听不懂韩语敬语",
        "我给妈妈打电话",
        "我在后台向前辈问候",
        "我觉得有人跟踪我",
        "我想参与制作下一次回归风格，提交demo",
        "快进一个月做总结",
    ]
    blocked = 0
    allowed = 0
    for action in actions:
        try:
            result = validate_action(state, action)
            allowed += 1
            action_text = result.normalized_action
            classify_turn(action_text, state)
            base_diff_for_action(action_text, state)
            evaluate_all_systems(state, action_text)
            evaluate_period_system(state, action_text)
            evaluate_inner_life(state, action_text)
            evaluate_relationship_system(state, action_text)
            evaluate_school_family(state, action_text)
            evaluate_social_context(state, action_text)
            evaluate_safety_boundary(state, action_text)
            evaluate_hierarchy_system(state, action_text)
        except ActionBlockedError:
            blocked += 1
    assert_true(allowed >= 10, "too many fuzz actions blocked")
    assert_true(blocked >= 0, "blocked counter invalid")


def main() -> None:
    tests: List[tuple[str, str, Callable[[], None]]] = [
        ("静态文件、语法、模块完整性", "static", test_static_integrity),
        ("角色校验与 profile tag", "character", test_character_validation_and_profiles),
        ("初始分配与上下文初始化", "initialization", test_initial_allocation_and_contexts),
        ("存档、LLM 解析、Prompt 合同", "storage_prompt_llm", test_storage_llm_and_prompt_contract),
        ("模型路由与配置策略", "routing_config", test_model_routing_and_config),
        ("行动闸门全矩阵", "action_validator", test_action_validator_all_gates),
        ("基础 diff、清洗、clamp、阈值", "rules", test_rules_diff_sanitize_apply_and_thresholds),
        ("天赋、能力解锁、被动效果", "talents_abilities", test_talents_abilities_and_passives),
        ("健康/资源/公关/粉圈/团队/回归/延迟系统", "core_systems", test_core_systems_evaluator),
        ("时间、年龄、CP 年龄差", "time_age_cp", test_time_age_and_cp_age_gap),
        ("生理期、少女心事、关系系统", "period_inner_relationship", test_period_inner_life_relationships),
        ("学校、家庭、国籍、前后辈、安全", "school_family_social_safety", test_school_family_social_safety_hierarchy),
        ("危机生命周期全类型", "crisis", test_crisis_lifecycle_all_types),
        ("Mock 引擎连续回合与持久化", "engine_persistence", test_engine_mock_full_flow_and_persistence),
        ("旧存档回填与 UI 摘要", "migration_ui", test_backfill_old_save_and_ui_summaries),
        ("随机行动矩阵 smoke test", "fuzz", test_fuzz_action_matrix_no_weird_crash),
    ]

    for name, category, fn in tests:
        run_test(name, category, fn)

    passed = sum(1 for row in REPORT if row["ok"])
    total = len(REPORT)
    report_path = Path(__file__).resolve().parent / "stress_report.json"
    report_path.write_text(json.dumps({"passed": passed, "total": total, "items": REPORT}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nFULL SYSTEM STRESS RESULT: {passed}/{total} passed.")
    print(f"Report written to: {report_path}")
    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
