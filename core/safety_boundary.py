from __future__ import annotations

from typing import Any, Dict, List, Tuple
from core.models import GameState, SystemEvent


def default_safety_context(age_context: Dict[str, Any]) -> Dict[str, Any]:
    minor = bool(age_context.get("is_minor", False))
    return {
        "outing_permission": 25 if minor else 55,
        "dorm_security": 65,
        "trusted_adults": ["经纪人", "舞蹈老师"],
        "boundary_violation_risk": 10,
        "bullying_risk": 18 if minor else 12,
        "harassment_risk": 8,
        "report_history": [],
        "independent_outing_allowed": not minor,
        "curfew_violation_risk": 20 if minor else 5,
    }


def _event(code: str, title: str, desc: str, severity: str = "info", diff: Dict[str, int] | None = None, flags: List[str] | None = None) -> SystemEvent:
    return SystemEvent(
        code=code,
        title=title,
        severity=severity,
        description=desc,
        source_system="safety_boundary",
        suggested_diff=diff or {},
        new_flags=flags or [title],
        tags=["safety_boundary"],
    )


def _merge_event_diff(diff: Dict[str, int], event: SystemEvent) -> None:
    for key, value in event.suggested_diff.items():
        diff[key] = diff.get(key, 0) + value


def evaluate_safety_boundary(state: GameState, action: str) -> Tuple[List[SystemEvent], Dict[str, int]]:
    events: List[SystemEvent] = []
    diff: Dict[str, int] = {}
    s = state.safety
    minor = bool(state.age_context.get("is_minor", False))

    private_outing = any(w in action for w in ["偷偷出门", "私自出门", "自己出门", "凌晨出门", "深夜出门", "便利店", "网约车", "打车"])
    stranger_invite = any(w in action for w in ["陌生人", "网友", "单独见面", "私下见", "不告诉公司"])
    stalking = any(w in action for w in ["跟踪", "陌生车", "偷拍", "私生", "楼下", "尾随"])
    bullying = any(w in action for w in ["霸凌", "排挤", "欺负", "孤立", "抢东西", "恶作剧"])
    harassment = any(w in action for w in ["骚扰", "摸", "身体边界", "不舒服", "越界", "单独房间", "不敢拒绝"])

    if private_outing:
        s["outing_permission"] = max(0, int(s.get("outing_permission", 50)) - 5)
        s["curfew_violation_risk"] = min(100, int(s.get("curfew_violation_risk", 0)) + (15 if minor else 6))
        events.append(_event(
            "safety_private_outing_risk",
            "安全边界：私自出入风险",
            "公司对练习生出入有管理责任。私自出入会增加迷路、偷拍、处分、家长介入或安全事件风险。",
            "warning",
            {"风险.私生风险": 2, "风险.行程泄露风险": 2, "心理状态.精神压力": 1},
            ["私自出入风险"],
        ))

    if stranger_invite:
        s["boundary_violation_risk"] = min(100, int(s.get("boundary_violation_risk", 0)) + 15)
        events.append(_event(
            "safety_stranger_invite",
            "安全边界：陌生邀约",
            "陌生邀约和不告知公司的单独见面不能被写成浪漫自由行动。它首先是安全风险。",
            "crisis",
            {"心理状态.精神压力": 3, "风险.公关危机风险": 3},
            ["陌生邀约安全风险"],
        ))

    if stalking:
        events.append(_event(
            "safety_stalking_signal",
            "安全边界：疑似跟踪/私生",
            "连续出现的陌生车辆、偷拍、尾随或楼下等待，都应进入安全处理流程，而不是当成普通剧情。",
            "crisis",
            {"风险.私生风险": 8, "风险.行程泄露风险": 5, "心理状态.精神压力": 4, "公司与合约.危机关注度": 4},
            ["疑似私生/跟踪"],
        ))

    if bullying:
        s["bullying_risk"] = min(100, int(s.get("bullying_risk", 0)) + 10)
        events.append(_event(
            "safety_bullying_signal",
            "安全边界：霸凌/排挤信号",
            "霸凌和排挤不是普通竞争。系统会提供求助路径，并把沉默的代价记入长期压力。",
            "warning",
            {"心理状态.精神压力": 4, "团队关系.真实关系温度": -3, "风险.霸凌排挤风险": 6},
            ["霸凌/排挤信号"],
        ))

    if harassment:
        s["harassment_risk"] = min(100, int(s.get("harassment_risk", 0)) + 15)
        s["boundary_violation_risk"] = min(100, int(s.get("boundary_violation_risk", 0)) + 15)
        events.append(_event(
            "safety_harassment_boundary",
            "安全边界：骚扰或身体边界侵犯",
            "任何身体边界侵犯、骚扰或权力越界都不能浪漫化。必须提供离开现场、记录、求助、法务或报警路径。",
            "crisis",
            {"心理状态.精神压力": 6, "心理状态.边界感": -2, "公司与合约.危机关注度": 5},
            ["骚扰/身体边界侵犯风险"],
        ))

    if minor and s.get("curfew_violation_risk", 0) > 60:
        events.append(_event(
            "safety_minor_curfew_warning",
            "未成年出行风险升高",
            "未成年练习生的私自出行风险已经升高。家长、公司和宿舍管理会介入。",
            "warning",
            {"公司与合约.危机关注度": 3, "心理状态.精神压力": 2},
            ["未成年出行风险升高"],
        ))

    for _ev in events:
        _merge_event_diff(diff, _ev)
    return events, diff
