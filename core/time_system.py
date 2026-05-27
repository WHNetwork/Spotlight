from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Tuple
from core.models import GameState, RouteInfo, SystemEvent


def compute_age_group(age: int | None) -> Dict[str, Any]:
    if age is None:
        return {
            "age": None,
            "age_group": "未知",
            "is_minor": False,
            "guardian_required": False,
            "romance_allowed": True,
            "curfew_level": "普通",
            "allowed_independent_outing": True,
        }
    if age <= 14:
        group = "未成年早期"
        minor = True
        curfew = "严格"
        outing = False
    elif age <= 17:
        group = "未成年中后期"
        minor = True
        curfew = "较严格"
        outing = False
    elif age <= 20:
        group = "成年初期"
        minor = False
        curfew = "普通"
        outing = True
    elif age <= 24:
        group = "成熟新人"
        minor = False
        curfew = "普通"
        outing = True
    else:
        group = "成熟职业期"
        minor = False
        curfew = "普通"
        outing = True
    return {
        "age": age,
        "age_group": group,
        "is_minor": minor,
        "guardian_required": minor,
        "romance_allowed": not minor,
        "curfew_level": curfew,
        "allowed_independent_outing": outing,
    }


def default_time_context(age: int | None = None, start_date: str = "2026-01-01") -> Dict[str, Any]:
    age_months = None if age is None else int(age) * 12
    return {
        "current_date": start_date,
        "age_years": age,
        "age_months": age_months,
        "days_elapsed": 0,
        "turn_duration_days": 0,
        "trainee_month": 1,
        "next_evaluation_days": 28,
        "last_turn_kind": "none",
        "last_time_note": "角色创建",
    }


def _parse_date(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except Exception:
        return date(2026, 1, 1)


def determine_turn_duration_days(route: RouteInfo, action: str) -> int:
    if any(w in action for w in ["快进三个月", "季度总结", "跳过三个月"]):
        return 90
    if any(w in action for w in ["快进一个月", "月度总结", "跳过一个月"]):
        return 30
    if any(w in action for w in ["快进一周", "周总结"]):
        return 7
    if route.turn_kind == "crisis":
        return 1
    if route.turn_kind == "focus":
        return 3
    if route.turn_kind == "mainline":
        return 7
    return 7


def _event(code: str, title: str, desc: str, severity: str = "info", diff: Dict[str, int] | None = None, flags: List[str] | None = None) -> SystemEvent:
    return SystemEvent(
        code=code,
        title=title,
        severity=severity,
        description=desc,
        source_system="time",
        suggested_diff=diff or {},
        new_flags=flags or [title],
        tags=["time"],
    )


def _merge_event_diff(diff: Dict[str, int], event: SystemEvent) -> None:
    for key, value in event.suggested_diff.items():
        diff[key] = diff.get(key, 0) + value


def advance_time(state: GameState, route: RouteInfo, action: str) -> Tuple[List[SystemEvent], Dict[str, int], int]:
    events: List[SystemEvent] = []
    diff: Dict[str, int] = {}

    duration = determine_turn_duration_days(route, action)
    t = state.time
    old_date = _parse_date(str(t.get("current_date", "2026-01-01")))
    new_date = old_date + timedelta(days=duration)

    t["current_date"] = new_date.isoformat()
    t["turn_duration_days"] = duration
    t["days_elapsed"] = int(t.get("days_elapsed", 0)) + duration
    t["last_turn_kind"] = route.turn_kind
    t["last_time_note"] = f"{route.turn_kind} 回合推进 {duration} 天"

    if t.get("age_months") is not None:
        # 近似按 30 天算月龄，足够支撑游戏逻辑。
        old_months = int(t["age_months"])
        new_months = old_months + duration // 30
        t["age_months"] = new_months
        t["age_years"] = new_months // 12
        state.age_context.update(compute_age_group(t["age_years"]))

    t["trainee_month"] = max(1, int(t.get("days_elapsed", 0)) // 30 + 1)

    remaining = int(t.get("next_evaluation_days", 28)) - duration
    if state.is_trainee_stage():
        if remaining <= 0:
            events.append(_event(
                "time_monthly_evaluation_due",
                "时间节点：月末考核到来",
                "练习生阶段的月末考核到了。训练、身体状态、老师评价、队内关系都会进入评估。",
                "warning",
                {"公司与合约.危机关注度": 1},
                ["月末考核到来"],
            ))
            # 保留余数，避免快进 90 天只触发一次后立刻回到 28。
            t["next_evaluation_days"] = 28 + remaining
        else:
            t["next_evaluation_days"] = remaining

    events.append(_event(
        "time_advanced",
        "时间推进",
        f"本回合推进 {duration} 天。当前日期：{t['current_date']}；练习生第 {t['trainee_month']} 月。",
        "info",
        {},
        [],
    ))

    for _ev in events:
        _merge_event_diff(diff, _ev)
    return events, diff, duration
