from __future__ import annotations

from core.models import GameState
from core.time_system import compute_age_group
from core.relationship_system import (
    cp_age_gap_limit,
    is_cp_eligible,
    is_near_age,
    relationship_ui_summary,
    ensure_default_relationships,
)


def ok(name: str):
    print(f"[PASS] {name}")


def make_state(age: int, stage: str = "练习生阶段", mainline: str = "初入公司"):
    state = GameState(current_stage=stage, current_mainline=mainline, current_schedule="普通行程")
    state.age_context = compute_age_group(age)
    ensure_default_relationships(state)
    return state


def peer(name: str, age: int, role: str = "爱豆"):
    return {
        "name": name,
        "role": role,
        "age": age,
        "friendship": 20,
        "trust": 20,
        "player_crush": 0,
        "ambiguity": 0,
        "business_cp_level": 0,
        "cp_fandom_pressure": 0,
    }


def test_trainee_gap_limit_3():
    state = make_state(18, "练习生阶段", "初入公司")
    assert cp_age_gap_limit(state) == 3
    assert is_cp_eligible(peer("A", 21, "练习生"), state) is True
    assert is_cp_eligible(peer("B", 22, "练习生"), state) is False
    ok("练习生阶段 CP 年龄差上限为 3 岁")


def test_idol_gap_limit_5():
    state = make_state(22, "正式爱豆阶段", "回归准备")
    assert cp_age_gap_limit(state) == 5
    assert is_cp_eligible(peer("A", 27, "爱豆"), state) is True
    assert is_cp_eligible(peer("B", 28, "爱豆"), state) is False
    ok("爱豆阶段 CP 年龄差上限为 5 岁")


def test_minor_adult_blocked_even_within_gap():
    state = make_state(17, "练习生阶段", "初入公司")
    assert is_near_age(peer("Adult", 18, "练习生"), state, max_gap=3) is False
    assert is_cp_eligible(peer("Adult", 18, "练习生"), state) is False
    ok("未成年与成年人不能进入 CP，即使年龄差在阈值内")


def test_same_minor_allowed_within_gap():
    state = make_state(16, "练习生阶段", "初入公司")
    assert is_cp_eligible(peer("MinorPeer", 17, "练习生"), state) is True
    assert is_cp_eligible(peer("TooFarMinor", 13, "练习生"), state) is True  # gap=3, both minors
    assert is_cp_eligible(peer("FarMinor", 12, "练习生"), state) is False
    ok("同为未成年且年龄差不超过 3 可以进入同龄练习生 CP 系统")


def test_staff_never_cp_even_same_age():
    state = make_state(18, "练习生阶段", "初入公司")
    staff = peer("Stylist", 18, "同龄造型助理")
    assert is_cp_eligible(staff, state) is False
    summary = relationship_ui_summary("Stylist", staff, state)
    assert "CP" not in summary
    ok("同龄工作人员仍不进入 CP 系统")


if __name__ == "__main__":
    tests = [
        test_trainee_gap_limit_3,
        test_idol_gap_limit_5,
        test_minor_adult_blocked_even_within_gap,
        test_same_minor_allowed_within_gap,
        test_staff_never_cp_even_same_age,
    ]
    for t in tests:
        t()
    print(f"\n全部测试通过：{len(tests)}/{len(tests)}。阶段化年龄差 CP 规则正常。")
