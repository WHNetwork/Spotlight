from __future__ import annotations

import tempfile
from pathlib import Path

from core.config import AppConfig
from core.engine import TurnEngine
from core.storage import SaveStorage
from core.character_validator import validate_character_input
from core.action_validator import validate_action, ActionBlockedError
from core.models import GameState, RouteInfo
from core.time_system import default_time_context, compute_age_group, advance_time
from core.social_context import default_social_context, evaluate_social_context
from core.school_family import default_school_context, default_family_context, evaluate_school_family
from core.safety_boundary import default_safety_context, evaluate_safety_boundary
from core.hierarchy_system import default_hierarchy_context, evaluate_hierarchy_system
from core.relationship_system import ensure_default_relationships, evaluate_relationship_system


def ok(name: str):
    print(f"[PASS] {name}")


def make_engine():
    tmp = tempfile.TemporaryDirectory()
    storage = SaveStorage(Path(tmp.name) / "saves.db")
    config = AppConfig()
    return tmp, storage, config, TurnEngine(storage, config, use_mock=True)


def make_char(**extra):
    data = {
        "艺名": "Luna",
        "年龄": "16",
        "身高": "166",
        "国籍": "中国",
        "身份": "海外追梦练习生",
        "时间线": "练习生阶段",
        "生理周期系统": "简化",
        "特长": "舞蹈",
        "弱项": "声乐",
        "家庭状况": "父母支持但担心学业",
        "出身来源标签": ["校园舞蹈社"],
    }
    data.update(extra)
    return validate_character_input(data).data


def test_initial_contexts():
    tmp, storage, config, engine = make_engine()
    state = engine.create_initial_state(make_char())
    assert state.age_context["is_minor"] is True
    assert state.school["enrolled"] is True
    assert state.social_context["is_overseas"] is True
    assert state.safety["independent_outing_allowed"] is False
    assert state.hierarchy["honorific_adaptation"] < 65
    ok("初始年龄/学校/国籍/安全/前后辈上下文生成正常")


def test_time_duration_and_evaluation():
    state = GameState(current_stage="练习生阶段", current_mainline="初入公司")
    state.time = default_time_context(16)
    state.age_context = compute_age_group(16)
    route = RouteInfo(turn_kind="ordinary")
    events, diff, days = advance_time(state, route, "普通训练")
    assert days == 7
    assert state.time["days_elapsed"] == 7
    assert state.time["next_evaluation_days"] == 21

    state.time["next_evaluation_days"] = 2
    events, diff, days = advance_time(state, route, "普通训练")
    assert any(e.code == "time_monthly_evaluation_due" for e in events)
    ok("普通回合推进 7 天，月末考核倒计时可触发")


def test_crisis_duration():
    state = GameState(current_stage="练习生阶段", current_mainline="初入公司")
    state.time = default_time_context(18)
    route = RouteInfo(turn_kind="crisis")
    events, diff, days = advance_time(state, route, "回应舆论")
    assert days == 1
    ok("危机回合推进 1 天")


def test_minor_private_outing_blocked():
    state = GameState(current_stage="练习生阶段", current_mainline="初入公司")
    state.age_context = compute_age_group(16)
    try:
        validate_action(state, "我想凌晨自己出门去便利店")
        raise AssertionError("minor private outing should be blocked")
    except ActionBlockedError:
        ok("未成年深夜私自出入会被阻止")


def test_stranger_invite_blocked():
    state = GameState(current_stage="练习生阶段", current_mainline="初入公司")
    state.age_context = compute_age_group(19)
    try:
        validate_action(state, "我不告诉公司，去私下见一个陌生网友")
        raise AssertionError("stranger invite should be blocked")
    except ActionBlockedError:
        ok("陌生邀约/不告知公司私下见面会被阻止")


def test_school_family_training_conflict():
    state = GameState(current_stage="练习生阶段", current_mainline="初入公司")
    state.age_context = compute_age_group(16)
    state.time = default_time_context(16)
    state.time["turn_duration_days"] = 7
    state.school = default_school_context(state.age_context, {})
    state.family = default_family_context(state.age_context, {"家庭状况": "父母不理解，经常吵"}, {"family_distance": 30})
    events, diff = evaluate_school_family(state, "我这周每天高强度加练到很晚")
    assert any(e.code == "school_training_conflict" for e in events)
    assert state.school["attendance_pressure"] > 35
    ok("在学练习生高强度训练会触发学校冲突")


def test_family_contact():
    state = GameState(current_stage="练习生阶段", current_mainline="初入公司")
    state.age_context = compute_age_group(16)
    state.time = default_time_context(16)
    state.time["turn_duration_days"] = 7
    sc = {"family_distance": 70}
    state.school = default_school_context(state.age_context, {})
    state.family = default_family_context(state.age_context, {"家庭状况": "父母支持理解"}, sc)
    events, diff = evaluate_school_family(state, "我给妈妈打电话，说最近训练很累")
    assert any(e.code == "family_support_contact" for e in events)
    assert state.family["last_contact_days"] == 0
    ok("家庭联系会按支持/理解度触发不同事件")


def test_social_language_and_homesick():
    state = GameState(current_stage="练习生阶段")
    state.social_context = default_social_context({"国籍": "中国"})
    events, diff = evaluate_social_context(state, "我听不懂韩语敬语，晚上很想家，想给父母打电话")
    codes = {e.code for e in events}
    assert "social_language_pressure" in codes
    assert "social_homesick" in codes
    ok("海外练习生会触发语言压力与想家事件")


def test_safety_signals():
    state = GameState(current_stage="练习生阶段")
    state.age_context = compute_age_group(18)
    state.safety = default_safety_context(state.age_context)
    events, diff = evaluate_safety_boundary(state, "宿舍楼下连续几天有陌生车，像是被私生跟踪偷拍")
    assert any(e.code == "safety_stalking_signal" for e in events)
    assert diff["风险.私生风险"] > 0
    ok("私生/跟踪信号进入安全系统")


def test_harassment_boundary():
    state = GameState(current_stage="练习生阶段")
    state.age_context = compute_age_group(18)
    state.safety = default_safety_context(state.age_context)
    events, diff = evaluate_safety_boundary(state, "工作人员让我单独去房间，我觉得身体边界很不舒服，像是骚扰")
    assert any(e.code == "safety_harassment_boundary" for e in events)
    assert diff["心理状态.精神压力"] > 0
    ok("骚扰/身体边界侵犯会进入安全危机而非普通剧情")


def test_hierarchy_events():
    state = GameState(current_stage="练习生阶段")
    state.social_context = default_social_context({"国籍": "中国"})
    state.hierarchy = default_hierarchy_context(state.social_context)
    events, diff = evaluate_hierarchy_system(state, "我在后台见到前辈，努力用敬语问候和鞠躬")
    assert any(e.code == "hierarchy_etiquette_scene" for e in events)
    ok("前后辈礼仪系统可触发")


def test_relationship_still_separate():
    state = GameState(current_stage="练习生阶段")
    state.age_context = compute_age_group(18)
    ensure_default_relationships(state)
    events, diff = evaluate_relationship_system(state, "裴智秀陪我练习，还借给我热水，我们深夜谈心")
    rel = state.relationships["裴智秀"]
    assert rel["friendship"] > 20
    assert rel["player_crush"] == 0
    ok("友情仍不自动变成爱情")


def test_engine_integration():
    tmp, storage, config, engine = make_engine()
    state = engine.create_initial_state(make_char())
    save_id = storage.create_save(state)
    old_date = state.time["current_date"]
    state, response, applied, route, events, validation = engine.run_turn(save_id, state, "我这周每天高强度加练，也担心学校作业和韩语敬语")
    assert state.turn == 1
    assert state.time["current_date"] != old_date
    sources = {e.source_system for e in events}
    assert "time" in sources
    assert "school_family" in sources or "social_context" in sources
    ok("回合引擎整合时间/学校/国籍系统")


def test_blocked_action_no_engine_call_needed():
    tmp, storage, config, engine = make_engine()
    state = engine.create_initial_state(make_char())
    save_id = storage.create_save(state)
    try:
        engine.run_turn(save_id, state, "我想凌晨自己出门去便利店")
        raise AssertionError("blocked action should not complete")
    except ActionBlockedError:
        assert state.turn == 0
        ok("被阻止行动不会推进回合")


def test_system_logic_consistency():
    """系统联动合理性检查：未成年海外练习生深夜私自出行阻止；
    同时友情/生理期/学校/礼仪等普通系统仍能独立触发。"""
    tmp, storage, config, engine = make_engine()
    state = engine.create_initial_state(make_char())
    assert state.age_context["is_minor"] is True
    assert state.school["enrolled"] is True
    assert state.social_context["is_overseas"] is True
    assert state.period["enabled"] is True
    assert state.relationships
    assert state.time["next_evaluation_days"] == 28
    ok("系统初始化联动一致：年龄、学校、海外、生理期、关系、考核均存在")


if __name__ == "__main__":
    tests = [
        test_initial_contexts,
        test_time_duration_and_evaluation,
        test_crisis_duration,
        test_minor_private_outing_blocked,
        test_stranger_invite_blocked,
        test_school_family_training_conflict,
        test_family_contact,
        test_social_language_and_homesick,
        test_safety_signals,
        test_harassment_boundary,
        test_hierarchy_events,
        test_relationship_still_separate,
        test_engine_integration,
        test_blocked_action_no_engine_call_needed,
        test_system_logic_consistency,
    ]
    for t in tests:
        t()
    print(f"\n全部测试通过：{len(tests)}/{len(tests)}。Phase 2.5 时间、年龄、学校、家庭、安全、前后辈与既有系统联动正常。")
