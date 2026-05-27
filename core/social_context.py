from __future__ import annotations

from typing import Any, Dict, List, Tuple
from core.models import GameState, SystemEvent


def default_social_context(character: Dict[str, Any]) -> Dict[str, Any]:
    nationality = str(character.get("国籍", "") or "未填写")
    is_korean = any(w in nationality for w in ["韩国", "Korea", "korea", "韩"])
    is_chinese = any(w in nationality for w in ["中国", "China", "china", "中"])
    is_japanese = any(w in nationality for w in ["日本", "Japan", "japan", "日"])
    is_overseas = bool(nationality and not is_korean and nationality != "未填写")

    language_barrier = 15 if is_korean else 45
    cultural_adaptation = 60 if is_korean else 35
    visa_pressure = 0 if is_korean else 35
    family_distance = 20 if is_korean else 70

    market_link = "韩国本土"
    if is_chinese:
        market_link = "中国市场"
    elif is_japanese:
        market_link = "日本市场"
    elif is_overseas:
        market_link = "海外市场"

    return {
        "nationality": nationality,
        "is_overseas": is_overseas,
        "language_barrier": language_barrier,
        "cultural_adaptation": cultural_adaptation,
        "visa_pressure": visa_pressure,
        "family_distance": family_distance,
        "overseas_market_link": market_link,
        "holiday_homesick_risk": 20 if is_korean else 55,
        "cultural_misread_risk": 10 if is_korean else 35,
    }


def _event(code: str, title: str, desc: str, severity: str = "info", diff: Dict[str, int] | None = None, flags: List[str] | None = None) -> SystemEvent:
    return SystemEvent(
        code=code,
        title=title,
        severity=severity,
        description=desc,
        source_system="social_context",
        suggested_diff=diff or {},
        new_flags=flags or [title],
        tags=["social_context"],
    )


def _merge_event_diff(diff: Dict[str, int], event: SystemEvent) -> None:
    for key, value in event.suggested_diff.items():
        diff[key] = diff.get(key, 0) + value


def evaluate_social_context(state: GameState, action: str) -> Tuple[List[SystemEvent], Dict[str, int]]:
    events: List[SystemEvent] = []
    diff: Dict[str, int] = {}
    sc = state.social_context

    if sc.get("is_overseas") and any(w in action for w in ["听不懂", "韩语", "敬语", "翻译", "语言", "采访"]):
        events.append(_event(
            "social_language_pressure",
            "海外练习生：语言压力",
            "语言不是单词表，而是反应速度、敬语、玩笑和误解成本。你需要更多时间适应公司里的沟通节奏。",
            "warning",
            {"心理状态.精神压力": 2, "职业属性.语言能力": 1},
            ["语言适应压力"],
        ))
        sc["language_barrier"] = max(0, int(sc.get("language_barrier", 45)) - 1)

    if sc.get("is_overseas") and any(w in action for w in ["想家", "家里", "父母", "节日", "生日", "打电话"]):
        events.append(_event(
            "social_homesick",
            "海外练习生：想家",
            "距离让家庭支持变得不那么即时。你可以打电话，也可以把想家写进日记或歌词。",
            "info",
            {"心理状态.孤独感": 3, "心理状态.精神压力": 1},
            ["海外想家"],
        ))

    if sc.get("visa_pressure", 0) > 60:
        events.append(_event(
            "social_visa_pressure",
            "签证压力上升",
            "签证、合同和出入境安排开始成为职业压力的一部分。公司处理效率会影响安全感。",
            "warning",
            {"心理状态.精神压力": 2, "公司与合约.危机关注度": 1},
            ["签证压力上升"],
        ))

    for _ev in events:
        _merge_event_diff(diff, _ev)
    return events, diff
