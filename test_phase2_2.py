from __future__ import annotations

import tempfile
from pathlib import Path

from core.action_validator import validate_action, ActionBlockedError
from core.character_validator import validate_character_input, CharacterValidationError
from core.config import AppConfig
from core.engine import TurnEngine
from core.initial_allocator import parse_profile_tags
from core.models import GameState
from core.storage import SaveStorage
from core.abilities import update_abilities


def ok(name: str):
    print(f"[PASS] {name}")


def test_character_validation():
    try:
        validate_character_input({"艺名": "", "本名": "", "年龄": "十八", "身高": "abc", "身份": "", "时间线": ""})
        raise AssertionError("invalid character should fail")
    except CharacterValidationError:
        ok("角色创建格式校验能拦截错误输入")

    norm = validate_character_input({
        "艺名": "Luna",
        "本名": "",
        "年龄": "18岁",
        "身高": "166cm",
        "身份": "素人学生被星探发现",
        "时间线": "练习生阶段",
        "特长": "舞蹈",
        "弱项": "声乐",
        "出身来源标签": "校园舞蹈社, 街头星探",
    })
    assert norm.data["年龄"] == 18
    assert norm.data["身高"] == 166
    assert "校园舞蹈社" in norm.data["出身来源标签"]
    ok("角色创建输入能规范化年龄、身高和来源标签")


def test_initial_allocation_low_career():
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
        "特长": "舞蹈",
        "弱项": "声乐",
        "出身来源标签": ["校园舞蹈社"],
    }).data
    state = engine.create_initial_state(char)
    assert max(state.career.values()) <= 15, state.career
    assert state.career["制作人能力"] == 0
    assert "舞蹈基础" in state.profile_tags
    assert state.initial_allocation_log
    ok("练习生初始职业属性低值化，制作人能力为 0")


def test_special_background_caps():
    tmp = tempfile.TemporaryDirectory()
    storage = SaveStorage(Path(tmp.name) / "saves.db")
    config = AppConfig()
    engine = TurnEngine(storage, config, use_mock=True)
    char = validate_character_input({
        "艺名": "Rin",
        "年龄": "19",
        "身高": "168",
        "身份": "选秀节目淘汰者",
        "时间线": "练习生阶段",
        "特长": "舞台表现",
        "弱项": "作曲",
        "出身来源标签": ["选秀节目淘汰者"],
    }).data
    state = engine.create_initial_state(char)
    assert max(state.career.values()) <= 20
    assert state.fans["个人粉丝数"] > 0
    ok("特殊背景练习生允许小幅突破但不超过 20")


def test_action_validation_stage_gate():
    state = GameState(current_stage="练习生阶段", current_mainline="初入公司", current_schedule="第一天报到")
    res = validate_action(state, "我要申请 MV 镜头和打歌 center")
    assert res.normalized_action != res.original_action
    assert "月末考核" in res.normalized_action
    ok("练习生阶段正式资源行动会被降级")

    try:
        validate_action(state, "我要参加大赏并拿代言")
        raise AssertionError("formal idol forbidden should be blocked")
    except ActionBlockedError:
        ok("练习生阶段大赏/代言行动被阻止")


def test_ability_unlock():
    state = GameState(current_stage="练习生阶段")
    state.career["舞蹈实力"] = 12
    state.talents["舞蹈天赋"] = 70
    events = update_abilities(state)
    assert "动作记忆" in state.abilities
    assert events
    ok("能力系统能按属性和天赋解锁")


def test_mock_turn_with_low_initial_and_no_producer_gain():
    tmp = tempfile.TemporaryDirectory()
    storage = SaveStorage(Path(tmp.name) / "saves.db")
    config = AppConfig()
    engine = TurnEngine(storage, config, use_mock=True)
    char = validate_character_input({
        "艺名": "Mina",
        "年龄": "18",
        "身高": "165",
        "身份": "素人学生被星探发现",
        "时间线": "练习生阶段",
        "特长": "作词",
        "弱项": "舞蹈",
        "出身来源标签": ["校园舞蹈社"],
    }).data
    state = engine.create_initial_state(char)
    save_id = storage.create_save(state)
    before = state.career["制作人能力"]
    state, response, applied, route, events, validation = engine.run_turn(save_id, state, "我想参与制作下一次回归风格，提交自己的 demo")
    assert validation.normalized_action != validation.original_action
    assert state.career["制作人能力"] == before
    assert "职业属性.制作人能力" not in applied
    ok("参与制作意向不会直接增加制作人能力，练习生阶段会被门控改写")


if __name__ == "__main__":
    test_character_validation()
    test_initial_allocation_low_career()
    test_special_background_caps()
    test_action_validation_stage_gate()
    test_ability_unlock()
    test_mock_turn_with_low_initial_and_no_producer_gain()
    print("\n全部测试通过。Phase 2.2 初始分配、角色校验和能力系统正常。")
