from __future__ import annotations

import tempfile
from pathlib import Path

from core.config import AppConfig
from core.engine import TurnEngine
from core.storage import SaveStorage
from core.character_validator import validate_character_input
from core.models import GameState
from core.relationship_system import (
    ensure_default_relationships,
    evaluate_relationship_system,
    default_relationship,
)
from core.action_validator import validate_action, ActionBlockedError


def ok(name: str):
    print(f"[PASS] {name}")


def make_state(age=18):
    state = GameState(current_stage="练习生阶段", current_mainline="初入公司", current_schedule="第一天报到")
    state.age_context = {
        "age": age,
        "age_group": "未成年中后期" if age < 18 else "成年初期",
        "is_minor": age < 18,
        "guardian_required": age < 18,
        "romance_allowed": age >= 18,
    }
    ensure_default_relationships(state)
    return state


def test_friendship_not_romance():
    state = make_state()
    events, diff = evaluate_relationship_system(state, "裴智秀陪我练习，还借给我热水和应急用品，我们深夜谈心")
    rel = state.relationships["裴智秀"]
    assert rel["friendship"] > 20
    assert rel["trust"] > 20
    assert rel["player_crush"] == 0
    assert any(e.code == "rel_friendship_signal" for e in events)
    ok("友情照顾只增加信任/照顾记忆，不自动变成恋爱")


def test_player_crush_not_npc_consent():
    state = make_state()
    events, diff = evaluate_relationship_system(state, "我发现自己很在意裴智秀看我的眼神，好像有一点心动")
    rel = state.relationships["裴智秀"]
    assert rel["player_crush"] > 0
    assert rel["confirmed_state"] == "未确认"
    assert rel["private_relation_state"] in {"普通同期", "朋友", "单方面心动", "友情被误读"}
    assert any(e.code == "rel_romance_signal_player_side" for e in events)
    ok("玩家心动不会自动代表 NPC 同意")


def test_business_cp_separate_from_private_romance():
    state = make_state()
    events, diff = evaluate_relationship_system(state, "公司安排我和裴智秀在镜头前营业CP，对视互动给粉丝看")
    rel = state.relationships["裴智秀"]
    assert rel["business_cp_level"] > 0
    assert rel["cp_fandom_pressure"] > 0
    assert rel["player_crush"] == 0
    assert any(e.code == "rel_business_cp_signal" for e in events)
    ok("营业 CP 与真实浪漫关系分离")


def test_boundary_signal_reduces_ambiguity():
    state = make_state()
    rel = state.relationships["裴智秀"]
    rel["player_crush"] = 50
    rel["ambiguity"] = 50
    rel["player_expectation"] = 50
    events, diff = evaluate_relationship_system(state, "裴智秀温和地说我们只是朋友，希望保持边界")
    rel = state.relationships["裴智秀"]
    assert rel["boundary_clarity"] > 55
    assert rel["ambiguity"] < 50
    assert rel["player_expectation"] < 50
    assert any(e.code == "rel_boundary_signal" for e in events)
    ok("边界信号会降低暧昧不确定性和期待")


def test_minor_romance_blocked():
    state = make_state(age=16)
    try:
        validate_action(state, "我想向裴智秀表白，确认关系成为恋人")
        raise AssertionError("minor romance confirmation should be blocked")
    except ActionBlockedError:
        ok("未成年正式恋爱确认会被行动闸门阻止")


def test_power_imbalance_blocked():
    state = make_state(age=20)
    try:
        validate_action(state, "我想向经纪人表白，确认关系成为恋人")
        raise AssertionError("power imbalance romance should be blocked")
    except ActionBlockedError:
        ok("权力差异恋爱推进会被行动闸门阻止")


def test_engine_mock_relationship_integration():
    tmp = tempfile.TemporaryDirectory()
    storage = SaveStorage(Path(tmp.name) / "saves.db")
    config = AppConfig()
    engine = TurnEngine(storage, config, use_mock=True)
    char = validate_character_input({
        "艺名": "Luna",
        "年龄": "18",
        "身高": "166",
        "身份": "素人学生被星探发现",
        "时间线": "练习生阶段",
        "生理周期系统": "简化",
        "特长": "舞蹈",
        "弱项": "声乐",
        "出身来源标签": ["校园舞蹈社"],
    }).data
    state = engine.create_initial_state(char)
    save_id = storage.create_save(state)
    state, response, applied, route, events, validation = engine.run_turn(save_id, state, "裴智秀陪我练习，还借给我热水，我们深夜谈心")
    assert any(e.source_system == "relationship" for e in events)
    assert state.relationships["裴智秀"]["friendship"] > 20
    ok("回合引擎能整合关系系统")


if __name__ == "__main__":
    test_friendship_not_romance()
    test_player_crush_not_npc_consent()
    test_business_cp_separate_from_private_romance()
    test_boundary_signal_reduces_ambiguity()
    test_minor_romance_blocked()
    test_power_imbalance_blocked()
    test_engine_mock_relationship_integration()
    print("\n全部测试通过。Phase 2.4 友情/暧昧/爱情/营业CP 分离系统正常。")
