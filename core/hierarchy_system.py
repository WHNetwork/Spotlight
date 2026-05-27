from __future__ import annotations

from typing import Any, Dict, List, Tuple
from core.models import GameState, SystemEvent


def default_hierarchy_context(social_context: Dict[str, Any]) -> Dict[str, Any]:
    overseas = bool(social_context.get("is_overseas", False))
    return {
        "honorific_adaptation": 45 if overseas else 65,
        "senior_relationship": 40,
        "etiquette_pressure": 35 if overseas else 25,
        "industry_reputation": 30,
        "senior_support": 15,
        "senior_pressure": 20,
        "backstage_protocol_familiarity": 35 if overseas else 55,
    }


def _event(code: str, title: str, desc: str, severity: str = "info", diff: Dict[str, int] | None = None, flags: List[str] | None = None) -> SystemEvent:
    return SystemEvent(
        code=code,
        title=title,
        severity=severity,
        description=desc,
        source_system="hierarchy",
        suggested_diff=diff or {},
        new_flags=flags or [title],
        tags=["hierarchy"],
    )


def _merge_event_diff(diff: Dict[str, int], event: SystemEvent) -> None:
    for key, value in event.suggested_diff.items():
        diff[key] = diff.get(key, 0) + value


def evaluate_hierarchy_system(state: GameState, action: str) -> Tuple[List[SystemEvent], Dict[str, int]]:
    events: List[SystemEvent] = []
    diff: Dict[str, int] = {}
    h = state.hierarchy

    etiquette = any(w in action for w in ["前辈", "敬语", "问候", "鞠躬", "后台", "礼仪", "半语", "让路", "拜访"])
    mistake = any(w in action for w in ["忘记问候", "说错敬语", "半语", "没鞠躬", "冒犯"])
    support = any(w in action for w in ["请教前辈", "前辈建议", "前辈照顾", "送饮料", "手写卡片"])

    if etiquette:
        h["etiquette_pressure"] = min(100, int(h.get("etiquette_pressure", 25)) + 2)
        h["backstage_protocol_familiarity"] = min(100, int(h.get("backstage_protocol_familiarity", 50)) + 3)
        events.append(_event(
            "hierarchy_etiquette_scene",
            "前后辈礼仪场景",
            "敬语、问候、后台礼仪和练习室秩序是职业环境的一部分。适应它会提高口碑，也会消耗精神。",
            "info",
            {"公司与合约.公司信任度": 1, "心理状态.精神压力": 1},
            ["前后辈礼仪场景"],
        ))

    if mistake:
        h["industry_reputation"] = max(0, int(h.get("industry_reputation", 30)) - 3)
        h["senior_pressure"] = min(100, int(h.get("senior_pressure", 20)) + 5)
        events.append(_event(
            "hierarchy_etiquette_mistake",
            "礼仪失误",
            "礼仪失误未必是道德问题，但在前后辈文化里会被放大。公司可能要求你补救。",
            "warning",
            {"心理状态.精神压力": 3, "公司与合约.危机关注度": 1},
            ["礼仪失误"],
        ))

    if support:
        h["senior_support"] = min(100, int(h.get("senior_support", 15)) + 5)
        h["senior_relationship"] = min(100, int(h.get("senior_relationship", 40)) + 4)
        events.append(_event(
            "hierarchy_senior_support",
            "前辈支持",
            "前辈的建议可能是职业资源，也可能带有压力。你需要区分支持、规训和越界要求。",
            "info",
            {"公司与合约.公司信任度": 1, "心理状态.自我认同": 1},
            ["前辈支持"],
        ))

    if h.get("etiquette_pressure", 0) > 75:
        events.append(_event(
            "hierarchy_pressure_high",
            "礼仪压力过高",
            "你对每个称呼、鞠躬和反应都绷得太紧。礼仪适应正在变成精神负担。",
            "warning",
            {"心理状态.精神压力": 2, "心理状态.边界感": -1},
            ["礼仪压力过高"],
        ))

    for _ev in events:
        _merge_event_diff(diff, _ev)
    return events, diff
