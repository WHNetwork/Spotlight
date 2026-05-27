from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Callable

import types

# 测试脚本只依赖核心逻辑。若运行环境缺少 keyring/python-dotenv，则用轻量 fallback，
# 不影响游戏本体；你的 conda 环境已安装这些包时会使用真实依赖。
try:
    import keyring  # noqa: F401
except ModuleNotFoundError:
    sys.modules["keyring"] = types.SimpleNamespace(
        get_password=lambda *args, **kwargs: "",
        set_password=lambda *args, **kwargs: None,
    )
try:
    import dotenv  # noqa: F401
except ModuleNotFoundError:
    sys.modules["dotenv"] = types.SimpleNamespace(load_dotenv=lambda *args, **kwargs: None)

PROJECT_ROOT = Path(__file__).resolve().parent
if not (PROJECT_ROOT / "core").exists():
    raise SystemExit("请把 test_phase2_1.py 放在项目根目录，也就是 app.py 同级目录下运行。")

sys.path.insert(0, str(PROJECT_ROOT))

from core.action_validator import ActionBlockedError, validate_action
from core.config import AppConfig
from core.crisis import update_crises
from core.engine import TurnEngine
from core.models import GameState, SystemEvent
from core.rules import base_diff_for_action, sanitize_suggested_diff
from core.storage import SaveStorage
from core.systems import classify_turn, evaluate_all_systems
from core.talents import generate_talents


PASS = "✅"
FAIL = "❌"


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_case(name: str, fn: Callable[[], None]) -> bool:
    try:
        fn()
        print(f"{PASS} {name}")
        return True
    except Exception as exc:
        print(f"{FAIL} {name}: {exc}")
        return False


def make_state() -> GameState:
    state = GameState()
    state.current_stage = "练习生阶段"
    state.current_mainline = "初入公司"
    state.current_schedule = "第一天报到"
    state.character = {
        "艺名": "Luna",
        "本名": "韩书允",
        "身份": "前运动员转型练习生",
        "特长": "舞蹈",
        "弱项": "声乐",
    }
    state.talents = generate_talents(state.character)
    return state


def test_talent_generation() -> None:
    state = make_state()
    assert_true("舞蹈天赋" in state.talents, "缺少舞蹈天赋")
    assert_true("体能天赋" in state.talents, "缺少体能天赋")
    assert_true(0 <= state.talents["舞蹈天赋"] <= 100, "舞蹈天赋越界")
    assert_true(state.talents["体能天赋"] >= 50, "前运动员体能天赋没有明显加成")


def test_stage_rewrite_resource_action() -> None:
    state = make_state()
    result = validate_action(state, "我要申请 MV 镜头和 center 位置")
    assert_true(result.allowed, "资源行动不应该直接阻止，应在练习生阶段降级")
    assert_true(result.normalized_action != result.original_action, "资源行动没有被阶段门控改写")
    assert_true("月末考核" in result.normalized_action or "评估录像" in result.normalized_action, "改写结果不符合练习生阶段")
    assert_true(result.system_events, "改写时应该产生 validator 系统事件")


def test_stage_block_formal_idol_action() -> None:
    state = make_state()
    try:
        validate_action(state, "我要参加大赏并争取代言")
    except ActionBlockedError as exc:
        assert_true("练习生阶段" in exc.message, "阻止理由没有说明阶段问题")
        return
    raise AssertionError("练习生阶段的大赏/代言行为应该被阻止")


def test_health_gate_blocks_high_intensity() -> None:
    state = make_state()
    state.body["体力"] = 15
    try:
        validate_action(state, "我继续高强度练舞，哪怕已经很累")
    except ActionBlockedError as exc:
        assert_true("体力低于 20" in exc.message, "阻止理由不对")
        return
    raise AssertionError("体力低于 20 时，高强度训练应该被阻止")


def test_producer_ability_source_constraint() -> None:
    state = make_state()
    action = "我想参与制作下一次回归风格，提交自己的 demo"
    validation = validate_action(state, action)
    diff = base_diff_for_action(validation.normalized_action, state)
    assert_true("职业属性.制作人能力" not in diff, "单纯表达制作意向不应增加制作人能力")
    fake_llm_diff = {"职业属性.制作人能力": 5, "心理状态.自我认同": 2}
    clean = sanitize_suggested_diff(state, fake_llm_diff, validation.normalized_action)
    assert_true("职业属性.制作人能力" not in clean, "sanitize_suggested_diff 没有移除不合理的制作人能力加成")


def test_system_event_resource_after_rewrite() -> None:
    state = make_state()
    validation = validate_action(state, "我要申请 MV 镜头和 center 位置")
    events, system_diff = evaluate_all_systems(state, validation.normalized_action)
    codes = {e.code for e in events}
    assert_true("trainee_resource_request" in codes, "练习生资源请求事件没有触发")
    assert_true("公司与合约.公司信任度" in system_diff, "系统 diff 没有写入公司信任度变化")


def test_route_crisis_uses_pro() -> None:
    state = make_state()
    route = classify_turn("我想回应网上关于队内不和的舆论", state)
    assert_true(route.model_tier == "pro", "危机/舆论行动应路由到 Pro")
    assert_true(route.turn_kind == "crisis", "危机/舆论行动应标记为 crisis")


def test_crisis_lifecycle_open_and_reduce_heat() -> None:
    state = make_state()
    pr_event = SystemEvent(
        code="pr_response_window",
        title="进入回应窗口",
        severity="warning",
        description="测试公关危机",
        source_system="public_relations",
    )
    events, diff = update_crises(state, "我选择沉默，不回应", [pr_event])
    assert_true(state.active_crises, "没有打开 ActiveCrisis")
    crisis = state.active_crises[0]
    old_heat = crisis.heat
    events2, diff2 = update_crises(state, "我选择回应和澄清，并拿出证据", [])
    assert_true(crisis.heat < old_heat, "回应澄清后危机热度没有下降")
    assert_true("风险.公关危机风险" in diff2, "回应危机没有生成公关风险 diff")


def test_engine_mock_rewrite_turn_persists() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        storage = SaveStorage(Path(tmp) / "saves.db")
        config = AppConfig()
        engine = TurnEngine(storage, config, use_mock=True)
        state = engine.create_initial_state({
            "艺名": "Luna",
            "本名": "韩书允",
            "身份": "素人学生被星探发现",
            "时间线": "练习生阶段",
            "特长": "舞蹈",
            "弱项": "声乐",
        })
        save_id = storage.create_save(state)
        state2, response, applied, route, system_events, validation = engine.run_turn(
            save_id,
            state,
            "我要申请 MV 镜头和 center 位置",
        )
        assert_true(state2.turn == 1, "回合数没有增加")
        assert_true(validation.normalized_action != validation.original_action, "engine 没有执行阶段门控改写")
        assert_true(system_events, "engine 没有记录系统事件")
        loaded = storage.load_save(save_id)
        assert_true(loaded.turn == 1, "存档没有保存回合数")
        assert_true(loaded.flags, "存档没有保存 flag")


def main() -> int:
    print("KPOP 女团爱豆模拟器 Phase 2.1 规则测试")
    print(f"项目目录：{PROJECT_ROOT}")
    print("-" * 72)

    cases = [
        ("天赋系统生成", test_talent_generation),
        ("练习生阶段：正式资源行动被改写", test_stage_rewrite_resource_action),
        ("练习生阶段：大赏/代言等正式爱豆行动被阻止", test_stage_block_formal_idol_action),
        ("健康闸门：体力低于 20 阻止高强度训练", test_health_gate_blocks_high_intensity),
        ("属性来源约束：制作人能力不能因表达意愿上涨", test_producer_ability_source_constraint),
        ("系统事件：练习生资源请求触发", test_system_event_resource_after_rewrite),
        ("模型路由：危机/舆论行动走 Pro", test_route_crisis_uses_pro),
        ("危机生命周期：开启并通过回应降低热度", test_crisis_lifecycle_open_and_reduce_heat),
        ("TurnEngine Mock：改写行动、保存存档、记录事件", test_engine_mock_rewrite_turn_persists),
    ]

    passed = 0
    for name, fn in cases:
        if run_case(name, fn):
            passed += 1

    print("-" * 72)
    print(f"通过：{passed}/{len(cases)}")
    if passed != len(cases):
        print("有测试失败。把上面的失败信息贴给我，我继续修。")
        return 1
    print("全部测试通过。Phase 2.1 的规则闸门、阶段门控、危机生命周期和 Mock 回合推进基本正常。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
