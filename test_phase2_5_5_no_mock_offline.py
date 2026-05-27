from __future__ import annotations

import json
import tempfile
import py_compile
from pathlib import Path

from core.config import AppConfig
from core.engine import TurnEngine
from core.storage import SaveStorage
from core.llm import DeepSeekProvider, parse_turn_response, LLMError
from core.prompts import build_messages
from core.models import GameState, RouteInfo
from core.character_validator import validate_character_input
from core.action_validator import validate_action, ActionBlockedError
from core.rules import base_diff_for_action, sanitize_suggested_diff, apply_diff
from core.systems import classify_turn, evaluate_all_systems
from core.time_system import compute_age_group, default_time_context
from core.relationship_system import ensure_default_relationships, evaluate_relationship_system, relationship_ui_summary
from core.period_system import default_period_state, advance_period, evaluate_period_system
from core.inner_life import default_inner_life, evaluate_inner_life
from core.school_family import default_school_context, default_family_context, evaluate_school_family
from core.social_context import default_social_context, evaluate_social_context
from core.safety_boundary import default_safety_context, evaluate_safety_boundary
from core.hierarchy_system import default_hierarchy_context, evaluate_hierarchy_system


def ok(name: str) -> None:
    print(f"[PASS] {name}")


def make_character(**extra):
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
        "出身来源标签": ["校园舞蹈社"],
    }
    raw.update(extra)
    return validate_character_input(raw).data


def make_state(age=18, stage="练习生阶段", mainline="初入公司") -> GameState:
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


def test_no_mock_code_removed():
    root = Path(__file__).resolve().parent
    scanned = []
    for rel in ["core/llm.py", "core/engine.py", "app.py"]:
        text = (root / rel).read_text(encoding="utf-8")
        scanned.append(text)
        assert "MockProvider" not in text, f"{rel} still contains MockProvider"
        assert "use_mock" not in text, f"{rel} still contains use_mock"
    assert "使用 Mock 模式" not in "\n".join(scanned)
    ok("MockProvider/use_mock/UI mock switch 已移除")


def test_static_syntax():
    root = Path(__file__).resolve().parent
    for py in list((root / "core").glob("*.py")) + [root / "app.py"]:
        py_compile.compile(str(py), doraise=True)
    ok("核心 Python 文件语法通过")


def test_llm_parser_without_mock():
    raw = json.dumps({
        "narrative": "练习室里只有风扇声。",
        "npc_reactions": [{"name": "裴智秀", "reaction": "她递给你一瓶水。"}],
        "choices": [],
        "suggested_diff": {"职业属性.舞蹈实力": 1},
        "new_flags": [],
        "resolved_flags": [],
        "public_summary": "你完成了一次训练。",
        "private_notes": "测试"
    }, ensure_ascii=False)
    parsed = parse_turn_response(raw)
    assert parsed.narrative
    assert len(parsed.choices) == 5
    ok("LLM JSON 解析与默认选项补全正常")


def test_engine_initialization_and_no_key_rollback():
    tmp = tempfile.TemporaryDirectory()
    storage = SaveStorage(Path(tmp.name) / "saves.db")
    config = AppConfig()
    config.get_api_key_fallback = lambda: ""  # type: ignore[method-assign]

    engine = TurnEngine(storage, config)
    state = engine.create_initial_state(make_character())
    save_id = storage.create_save(state)
    old_json = state.model_dump_json()
    old_saved_json = storage.load_save(save_id).model_dump_json()

    try:
        engine.run_turn(save_id, state, "我这周每天高强度加练，也担心学校作业和韩语敬语")
        raise AssertionError("run_turn should fail without DeepSeek API key")
    except LLMError:
        pass

    assert state.model_dump_json() == old_json, "state mutated after failed API call"
    assert storage.load_save(save_id).model_dump_json() == old_saved_json, "save mutated after failed API call"
    ok("DeepSeek 调用失败时不推进状态、不写入存档")


def test_prompt_and_route_without_calling_api():
    state = make_state(18)
    action = "我回应热搜争议，也想被看见"
    validation = validate_action(state, action)
    route = classify_turn(validation.normalized_action, state)
    base_diff = base_diff_for_action(validation.normalized_action, state)
    events, system_diff = evaluate_all_systems(state, validation.normalized_action)
    messages = build_messages(state, validation.normalized_action, base_diff, system_diff, events, route, validation)
    text = "\n".join(m["content"] for m in messages)
    assert "game_state" in text
    assert "生理周期" in text
    assert "友情" in text
    assert route.turn_kind == "crisis"
    ok("Prompt 构造与模型路由可离线测试")


def test_all_core_systems_offline():
    state = make_state(18)

    diff = base_diff_for_action("我练舞、声乐、写demo，然后休息", state)
    assert "职业属性.舞蹈实力" in diff
    assert "职业属性.声乐实力" in diff

    clean = sanitize_suggested_diff(state, {"职业属性.制作人能力": 50}, "我想参与制作")
    assert "职业属性.制作人能力" not in clean

    applied = apply_diff(state, {"职业属性.舞蹈实力": 99}, max_abs_delta=8)
    assert applied["职业属性.舞蹈实力"][1] - applied["职业属性.舞蹈实力"][0] == 8

    state.period["cycle_day"] = 28
    advance_period(state, days=1)
    pe, _ = evaluate_period_system(state, "我生理期腹痛，还想高强度练舞")
    assert pe

    ie, _ = evaluate_inner_life(state, "老师没有夸我，我很想被看见，于是写进日记")
    assert ie

    re, _ = evaluate_relationship_system(state, "裴智秀陪我练习，还借热水，我们深夜谈心")
    assert state.relationships["裴智秀"]["friendship"] > 20

    staff_events, _ = evaluate_relationship_system(state, "我发现自己很喜欢同龄造型助理宋夏，很在意她帮我整理服装时的眼神")
    assert any(e.code == "rel_same_age_staff_crush_risk" for e in staff_events)
    assert "CP" not in relationship_ui_summary("宋夏", state.relationships["宋夏"], state)

    state.time["turn_duration_days"] = 7
    se, _ = evaluate_school_family(state, "我这周每天高强度加练到很晚，还担心学校作业")
    assert se

    le, _ = evaluate_social_context(state, "我听不懂韩语敬语，晚上很想家")
    assert le

    safe, _ = evaluate_safety_boundary(state, "宿舍楼下连续几天有陌生车，像是被私生跟踪偷拍")
    assert safe

    he, _ = evaluate_hierarchy_system(state, "我在后台见到前辈，努力用敬语问候和鞠躬")
    assert he
    ok("核心系统离线烟测通过")


def test_action_blocking_still_works():
    minor = make_state(16)
    for action in [
        "我想凌晨自己出门去便利店",
        "我不告诉公司，去私下见一个陌生网友",
        "我想和工作人员单独去房间谈谈",
    ]:
        try:
            validate_action(minor, action)
            raise AssertionError(f"should be blocked: {action}")
        except ActionBlockedError:
            pass

    low_body = make_state(18)
    low_body.body["体力"] = 10
    try:
        validate_action(low_body, "我要继续高强度练舞")
        raise AssertionError("low stamina should block")
    except ActionBlockedError:
        pass
    ok("行动闸门仍正常")


if __name__ == "__main__":
    tests = [
        test_no_mock_code_removed,
        test_static_syntax,
        test_llm_parser_without_mock,
        test_engine_initialization_and_no_key_rollback,
        test_prompt_and_route_without_calling_api,
        test_all_core_systems_offline,
        test_action_blocking_still_works,
    ]
    for test in tests:
        test()
    print(f"\n全部测试通过：{len(tests)}/{len(tests)}。Mock 引擎已移除，离线规则系统正常。")
