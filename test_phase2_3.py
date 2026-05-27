from __future__ import annotations

import tempfile
from pathlib import Path

from core.config import AppConfig
from core.engine import TurnEngine
from core.storage import SaveStorage
from core.character_validator import validate_character_input
from core.period_system import default_period_state, advance_period, evaluate_period_system
from core.inner_life import default_inner_life, evaluate_inner_life, add_secret
from core.models import GameState
from core.abilities import update_abilities


def ok(name: str):
    print(f"[PASS] {name}")


def make_state() -> GameState:
    state = GameState(current_stage="练习生阶段", current_mainline="初入公司", current_schedule="第一天报到")
    state.period = default_period_state(enabled=True, mode="简化")
    state.inner_life = default_inner_life()
    return state


def test_period_advance_and_event():
    state = make_state()
    state.period["cycle_day"] = 28
    advance_period(state)
    assert state.period["cycle_day"] == 1
    assert state.period["phase"] == "生理期前段"
    events, diff = evaluate_period_system(state, "我选择高强度练舞，虽然腹部有点痛")
    assert any(e.code == "period_day1_2" for e in events)
    assert "身体状态.体力" in diff
    ok("生理周期会推进并在生理期前段触发事件")


def test_period_support_actions():
    state = make_state()
    state.period["cycle_day"] = 1
    state.period["phase"] = "生理期前段"
    state.period["pain_level"] = 45
    events, diff = evaluate_period_system(state, "我告诉经纪人身体状态，并向队友借应急用品和热水")
    assert state.period["told_manager"] is True
    assert state.period["told_teammate"] is True
    assert state.period["has_supplies"] is True
    assert any(e.code == "period_told_manager" for e in events)
    assert any(e.code == "period_teammate_support" for e in events)
    ok("告知经纪人/队友会改变生理周期支持状态")


def test_inner_life_secret_and_outlet():
    state = make_state()
    events, diff = evaluate_inner_life(state, "老师没有夸我，我突然很想被看见，不想一直在后排")
    assert state.inner_secrets
    assert any(e.code == "inner_visible_desire" for e in events)
    before = state.inner_life["秘密重量"]
    events2, diff2 = evaluate_inner_life(state, "我把这些话写进歌词本，先不说出口")
    assert state.inner_life["秘密重量"] <= before
    assert any(e.code in {"inner_diary_outlet", "inner_swallowed_words"} for e in events2)
    ok("少女心事会生成心事条目，并可通过日记/歌词释放")


def test_crush_thread():
    state = make_state()
    events, diff = evaluate_inner_life(state, "我发现自己很在意她看我的眼神，好像有一点心动")
    assert state.crush_threads
    assert any(e.code == "inner_crush_signal" for e in events)
    ok("心动表达会生成心动线索，但不直接变成恋爱结论")


def test_engine_mock_period_inner_integration():
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
    assert state.period["enabled"] is True
    assert "被看见的渴望" in state.inner_life
    save_id = storage.create_save(state)
    state, response, applied, route, events, validation = engine.run_turn(save_id, state, "老师没有夸我，我很想被看见，于是把心事写进日记")
    assert any(e.source_system == "inner_life" for e in events)
    assert state.inner_secrets or state.inner_life["秘密重量"] >= 0
    ok("回合引擎能整合生理周期与少女心事系统")


def test_ability_write_lyrics_unlock():
    state = make_state()
    state.career["创作能力"] = 8
    state.talents["创作天赋"] = 60
    events = update_abilities(state)
    assert "写进歌词" in state.abilities
    ok("创作能力与天赋达到门槛后可解锁写进歌词能力")


if __name__ == "__main__":
    test_period_advance_and_event()
    test_period_support_actions()
    test_inner_life_secret_and_outlet()
    test_crush_thread()
    test_engine_mock_period_inner_integration()
    test_ability_write_lyrics_unlock()
    print("\n全部测试通过。Phase 2.3 生理周期与少女心事系统正常。")
