from __future__ import annotations

from core.models import GameState
from core.time_system import compute_age_group
from core.relationship_system import (
    ensure_default_relationships,
    evaluate_relationship_system,
    is_cp_eligible,
    is_same_age_staff_crush_allowed,
    professional_romance_policy,
    relationship_ui_summary,
)
from core.action_validator import validate_action, ActionBlockedError


def ok(name: str):
    print(f"[PASS] {name}")


def make_state(age=18):
    state = GameState(current_stage="练习生阶段", current_mainline="初入公司")
    state.age_context = compute_age_group(age)
    ensure_default_relationships(state)
    return state


def test_staff_roles_are_distinct():
    state = make_state(18)
    assert state.relationships["韩室长"]["professional_role_category"] == "manager"
    assert state.relationships["尹老师"]["professional_role_category"] == "teacher"
    assert state.relationships["宋夏"]["professional_role_category"] == "styling"
    assert state.relationships["崔PD"]["professional_role_category"] == "production"
    assert "管理责任" in state.relationships["韩室长"]["role_viewpoint"]
    assert "评价权" in state.relationships["尹老师"]["role_viewpoint"]
    assert "后台照顾" in state.relationships["宋夏"]["role_viewpoint"]
    assert "资源权" in state.relationships["崔PD"]["role_viewpoint"]
    ok("工作人员按经纪人/老师/造型助理/PD 区分角色视角")


def test_cp_only_for_peer():
    state = make_state(18)
    assert is_cp_eligible(state.relationships["裴智秀"], state) is True
    for name in ["韩室长", "尹老师", "宋夏", "崔PD"]:
        assert is_cp_eligible(state.relationships[name], state) is False
        assert "CP" not in relationship_ui_summary(name, state.relationships[name], state)
    ok("CP 只出现在同龄练习生/爱豆关系，不出现在工作人员身上")


def test_same_age_staff_crush_allowed_but_costly():
    state = make_state(18)
    rel = state.relationships["宋夏"]
    assert is_same_age_staff_crush_allowed(rel, state) is True
    assert professional_romance_policy(rel, state) == "same_age_staff_high_risk"

    events, diff = evaluate_relationship_system(state, "我发现自己很喜欢同龄造型助理宋夏，很在意她帮我整理服装时的眼神")
    rel = state.relationships["宋夏"]
    assert rel["player_crush"] > 0
    assert rel["professional_boundary_pressure"] > 0
    assert rel["relationship_risk"] > 0
    assert rel["private_relation_state"] in {"职业边界下的单方面心动", "职业边界暧昧风险", "普通同期", "朋友"}
    assert any(e.code == "rel_same_age_staff_crush_risk" for e in events)
    assert diff["风险.恋爱风险"] > 0
    ok("同龄工作人员可以被喜欢，但会进入职业边界风险并付出代价")


def test_manager_teacher_pd_high_power_blocked_in_validator():
    state = make_state(18)
    for action in ["我想向经纪人表白，确认关系", "我想向尹老师表白，确认关系", "我想向崔PD表白，确认关系"]:
        try:
            validate_action(state, action)
            raise AssertionError(f"should block: {action}")
        except ActionBlockedError:
            pass
    ok("经纪人/老师/PD 的正式恋爱推进仍被行动闸门阻止")


def test_low_power_staff_confirmation_not_blocked_but_warned():
    state = make_state(18)
    result = validate_action(state, "我想向同龄造型助理宋夏表白，确认关系")
    assert result.allowed is True
    assert any(e.code == "staff_romance_boundary_warning" for e in result.system_events)
    ok("低权力同龄工作人员表白不硬阻止，但先给边界代价警告")


def test_business_cp_guard_for_staff_still_works():
    state = make_state(18)
    events, diff = evaluate_relationship_system(state, "公司安排我和宋夏在镜头前营业CP互动给粉丝看")
    rel = state.relationships["宋夏"]
    assert rel["business_cp_level"] == 0
    assert rel["cp_fandom_pressure"] == 0
    assert any(e.code == "rel_cp_ineligible_boundary" for e in events)
    assert "CP" not in relationship_ui_summary("宋夏", rel, state)
    ok("同龄工作人员也不能进入营业 CP 系统")


def test_peer_romance_still_normal():
    state = make_state(18)
    events, diff = evaluate_relationship_system(state, "我发现自己很在意裴智秀看我的眼神，好像有一点心动")
    rel = state.relationships["裴智秀"]
    assert rel["player_crush"] > 0
    assert any(e.code == "rel_romance_signal_player_side" for e in events)
    ok("同龄练习生的玩家心动仍走普通 peer 路线")


if __name__ == "__main__":
    tests = [
        test_staff_roles_are_distinct,
        test_cp_only_for_peer,
        test_same_age_staff_crush_allowed_but_costly,
        test_manager_teacher_pd_high_power_blocked_in_validator,
        test_low_power_staff_confirmation_not_blocked_but_warned,
        test_business_cp_guard_for_staff_still_works,
        test_peer_romance_still_normal,
    ]
    for t in tests:
        t()
    print(f"\n全部测试通过：{len(tests)}/{len(tests)}。工作人员关系分层与同龄工作人员高风险心动路线正常。")
