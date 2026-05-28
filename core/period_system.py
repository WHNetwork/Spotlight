from __future__ import annotations

from typing import Any, Dict, List, Tuple
from core.models import GameState, SystemEvent


def default_period_state(enabled: bool = True, mode: str = "简化") -> Dict[str, Any]:
    return {
        "enabled": enabled,
        "mode": mode,  # 关闭 / 简化 / 极致
        "cycle_day": 8,
        "cycle_length": 28,
        "phase": "稳定期",
        "pain_level": 0,
        "flow_pressure": 0,
        "irregularity_risk": 5,
        "has_supplies": True,
        "told_manager": False,
        "told_teammate": False,
        "last_event_turn": -1,
    }


def _add(diff: Dict[str, int], key: str, value: int) -> None:
    diff[key] = diff.get(key, 0) + value


def _event(code: str, title: str, desc: str, severity: str = "info", diff: Dict[str, int] | None = None, flags: List[str] | None = None) -> SystemEvent:
    return SystemEvent(
        code=code,
        title=title,
        severity=severity,
        description=desc,
        source_system="period",
        suggested_diff=diff or {},
        new_flags=flags or [title],
        tags=["period", "body"],
    )


def phase_for_day(day: int, length: int) -> str:
    d = ((day - 1) % max(length, 21)) + 1
    if d in {1, 2}:
        return "生理期前段"
    if d in {3, 4, 5}:
        return "生理期后段"
    if d in {26, 27, 28} or d >= length - 2:
        return "经前期"
    if d in {6, 7, 8}:
        return "恢复期"
    return "稳定期"


def advance_period(state: GameState, days: int = 1) -> None:
    p = state.period
    if not p.get("enabled", False) or p.get("mode") == "关闭":
        return

    length = int(p.get("cycle_length", 28) or 28)
    day = int(p.get("cycle_day", 1) or 1)
    for _ in range(max(1, int(days))):
        day = (day % length) + 1
    p["cycle_day"] = day
    phase = phase_for_day(day, length)
    p["phase"] = phase

    pressure = int(p.get("irregularity_risk", 5))
    if phase == "经前期":
        p["pain_level"] = max(0, min(100, 10 + pressure // 4))
        p["flow_pressure"] = 0
    elif phase == "生理期前段":
        p["pain_level"] = max(0, min(100, 35 + pressure // 3))
        p["flow_pressure"] = max(0, min(100, 45 + pressure // 4))
    elif phase == "生理期后段":
        p["pain_level"] = max(0, min(100, 18 + pressure // 5))
        p["flow_pressure"] = max(0, min(100, 22 + pressure // 6))
    elif phase == "恢复期":
        p["pain_level"] = max(0, int(p.get("pain_level", 0)) - 12)
        p["flow_pressure"] = max(0, int(p.get("flow_pressure", 0)) - 18)
    else:
        p["pain_level"] = max(0, int(p.get("pain_level", 0)) - 8)
        p["flow_pressure"] = max(0, int(p.get("flow_pressure", 0)) - 10)


def evaluate_period_system(state: GameState, action: str) -> Tuple[List[SystemEvent], Dict[str, int]]:
    events: List[SystemEvent] = []
    diff: Dict[str, int] = {}
    p = state.period

    if not p.get("enabled", False) or p.get("mode") == "关闭":
        return events, diff

    text = action.lower()
    detail_mode = str(p.get("mode", "简化")) in {"极致", "细致", "开启"}
    phase = str(p.get("phase", "稳定期"))
    pain = int(p.get("pain_level", 0))
    flow = int(p.get("flow_pressure", 0))

    high_intensity = any(w in action for w in ["高强度", "加练", "继续练", "硬撑", "练舞", "考核"])
    pale_clothes = any(w in action for w in ["浅色", "白色", "服装", "裙子", "评估录像", "拍摄"])
    asks_help = any(w in action for w in ["告诉经纪人", "告诉老师", "申请调整", "说明身体"])
    asks_teammate = any(w in action for w in ["问队友", "告诉队友", "借", "应急用品", "止痛", "热水", "暖宝宝"])
    hides = any(w in action for w in ["隐瞒", "不说", "装没事", "硬撑"])

    if asks_help:
        p["told_manager"] = True
        _add(diff, "心理状态.边界感", 2)
        _add(diff, "公司与合约.危机关注度", 1)
        events.append(_event(
            "period_told_manager",
            "生理期：告知经纪人",
            "你选择向经纪人说明身体状态。它可能换来动作调整、服装准备或行程协调，也可能让你面对公司现实的效率逻辑。",
            "info",
            {"心理状态.精神压力": -2},
            ["已向经纪人说明生理期状态"],
        ))

    if asks_teammate:
        p["told_teammate"] = True
        p["has_supplies"] = True
        _add(diff, "团队关系.真实关系温度", 2)
        _add(diff, "心理状态.孤独感", -2)
        events.append(_event(
            "period_teammate_support",
            "生理期：向队友求助",
            "你把不适说给队友听。她的反应会影响你对宿舍和团队的安全感。",
            "info",
            {"团队关系.宿舍安全感": 2},
            ["向队友求助过生理期用品"],
        ))

    if hides and phase in {"经前期", "生理期前段", "生理期后段"}:
        _add(diff, "心理状态.精神压力", 3)
        _add(diff, "身体状态.体力", -2)
        _add(diff, "身体状态.肌肉疲劳", 2)
        events.append(_event(
            "period_hidden_pressure",
            "生理期：隐瞒状态",
            "你选择不说。短期内行程不会被打断，但身体负担和秘密重量都会上升。",
            "warning",
            {"心理状态.自我认同": -1},
            ["隐瞒生理期不适"],
        ))

    if phase == "经前期":
        _add(diff, "身体状态.睡眠质量", -1)
        _add(diff, "身体状态.体重管理压力", 1)
        events.append(_event(
            "period_pms",
            "经前期波动",
            "身体进入经前期。疲劳、睡眠和身体自我意识更容易被放大。",
            "info",
            {"心理状态.心情": -1},
            ["经前期波动"],
        ))

    if phase == "生理期前段":
        _add(diff, "身体状态.体力", -4)
        _add(diff, "身体状态.肌肉疲劳", 2)
        _add(diff, "身体状态.睡眠质量", -2)
        events.append(_event(
            "period_day1_2",
            "生理期前段",
            "身体处在生理期前段。腹部坠痛、腰酸、睡眠和训练效率都会受到影响。",
            "warning",
            {"心理状态.精神压力": 2},
            ["生理期前段"],
        ))

    if phase == "生理期后段":
        _add(diff, "身体状态.体力", -2)
        events.append(_event(
            "period_late",
            "生理期后段",
            "痛感下降，但体力还没有完全恢复。你需要把训练强度重新调回安全范围。",
            "info",
            {},
            ["生理期后段"],
        ))

    if high_intensity and pain >= 25:
        _add(diff, "身体状态.伤病风险", 3)
        _add(diff, "身体状态.肌肉疲劳", 3)
        _add(diff, "身体状态.体力", -3)
        events.append(_event(
            "period_high_intensity_risk",
            "生理期高强度训练风险",
            "在疼痛和疲劳存在时继续高强度训练，会提高伤病风险和考核失误概率。",
            "warning",
            {"风险.伤病爆发风险": 3},
            ["生理期高强度训练风险"],
        ))

    if detail_mode and pale_clothes and flow >= 30:
        _add(diff, "心理状态.精神压力", 3)
        _add(diff, "心理状态.自我认同", -1)
        if hasattr(state, "inner_life"):
            state.inner_life["身体自我意识"] = min(100, int(state.inner_life.get("身体自我意识", 30)) + 5)
        events.append(_event(
            "period_clothing_anxiety",
            "生理期服装焦虑",
            "浅色服装、评估录像和身体不适叠在一起，让你更在意自己的身体边界和镜头安全感。",
            "warning",
            {"风险.公关危机风险": 1},
            ["生理期服装焦虑"],
        ))

    if state.mind.get("精神压力", 0) > 75 or state.body.get("体重管理压力", 0) > 70 or state.body.get("睡眠质量", 100) < 35:
        p["irregularity_risk"] = min(100, int(p.get("irregularity_risk", 5)) + 2)
    else:
        p["irregularity_risk"] = max(0, int(p.get("irregularity_risk", 5)) - 1)

    if detail_mode and p["irregularity_risk"] > 60:
        events.append(_event(
            "period_irregularity_warning",
            "周期不规律风险上升",
            "长期压力、睡眠不足和体重管理压力正在影响身体周期。它需要休息、营养和更稳定的作息。",
            "warning",
            {"身体状态.免疫状态": -2, "心理状态.精神压力": 1},
            ["周期不规律风险上升"],
        ))

    return events, diff
