from __future__ import annotations

from core.models import GameState
from core.time_system import compute_age_group
from core.relationship_system import (
    ensure_default_relationships,
    evaluate_relationship_system,
    is_cp_eligible,
    relationship_ui_summary,
)


def ok(name: str):
    print(f"[PASS] {name}")


def make_state(age=18):
    state = GameState(current_stage="练习生阶段", current_mainline="初入公司")
    state.age_context = compute_age_group(age)
    ensure_default_relationships(state)
    return state


def test_staff_not_cp_eligible():
    state = make_state(18)
    assert is_cp_eligible(state.relationships["韩室长"], state) is False
    assert is_cp_eligible(state.relationships["尹老师"], state) is False
    manager_summary = relationship_ui_summary("韩室长", state.relationships["韩室长"], state)
    teacher_summary = relationship_ui_summary("尹老师", state.relationships["尹老师"], state)
    assert "CP" not in manager_summary
    assert "CP" not in teacher_summary
    assert "边界:职务" in manager_summary
    assert "边界:职务" in teacher_summary
    ok("经纪人/老师不显示 CP0，而显示职务边界")


def test_peer_cp_eligible():
    state = make_state(18)
    assert is_cp_eligible(state.relationships["裴智秀"], state) is True
    assert "CP0" in relationship_ui_summary("裴智秀", state.relationships["裴智秀"], state)
    ok("同龄同期练习生可以显示 CP")


def test_business_cp_guard_for_staff():
    state = make_state(18)
    events, diff = evaluate_relationship_system(state, "公司安排我和韩室长在镜头前营业CP互动给粉丝看")
    rel = state.relationships["韩室长"]
    assert rel["business_cp_level"] == 0
    assert rel["cp_fandom_pressure"] == 0
    assert any(e.code == "rel_cp_ineligible_boundary" for e in events)
    summary = relationship_ui_summary("韩室长", rel, state)
    assert "CP" not in summary
    ok("经纪人营业请求不会进入 CP 系统，而转成边界事件")


def test_business_cp_allowed_for_peer():
    state = make_state(18)
    events, diff = evaluate_relationship_system(state, "公司安排我和裴智秀在镜头前营业CP互动给粉丝看")
    rel = state.relationships["裴智秀"]
    assert rel["business_cp_level"] > 0
    assert rel["cp_fandom_pressure"] > 0
    assert any(e.code == "rel_business_cp_signal" for e in events)
    assert "CP" in relationship_ui_summary("裴智秀", rel, state)
    ok("同龄同期练习生营业 CP 正常计算")


def test_age_gap_not_cp_eligible():
    state = make_state(18)
    state.relationships["前辈爱豆"] = {
        **state.relationships["裴智秀"],
        "name": "前辈爱豆",
        "role": "爱豆",
        "age": 25,
        "business_cp_level": 0,
        "cp_fandom_pressure": 0,
    }
    assert is_cp_eligible(state.relationships["前辈爱豆"], state) is False
    summary = relationship_ui_summary("前辈爱豆", state.relationships["前辈爱豆"], state)
    assert "CP" not in summary
    assert "边界:年龄差>" in summary
    ok("年龄差过大的爱豆不进入 CP 系统")


if __name__ == "__main__":
    tests = [
        test_staff_not_cp_eligible,
        test_peer_cp_eligible,
        test_business_cp_guard_for_staff,
        test_business_cp_allowed_for_peer,
        test_age_gap_not_cp_eligible,
    ]
    for t in tests:
        t()
    print(f"\n全部测试通过：{len(tests)}/{len(tests)}。CP eligibility 修正正常。")
