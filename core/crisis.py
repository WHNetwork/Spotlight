from __future__ import annotations

from typing import Dict, List, Tuple
from core.models import GameState, SystemEvent, ActiveCrisis
from core.rules import _add


def _crisis_event(code: str, title: str, desc: str, severity: str = "warning", diff: Dict[str, int] | None = None) -> SystemEvent:
    return SystemEvent(
        code=code,
        title=title,
        severity=severity,
        description=desc,
        source_system="crisis_lifecycle",
        suggested_diff=diff or {},
        new_flags=[title],
        tags=["crisis"],
    )


def _get_crisis(state: GameState, crisis_type: str) -> ActiveCrisis | None:
    for c in state.active_crises:
        if c.crisis_type == crisis_type and c.stage not in {"closed", "converted"}:
            return c
    return None


def _open_crisis(state: GameState, crisis_type: str, title: str, failure_flag: str, heat: int = 55) -> ActiveCrisis:
    existing = _get_crisis(state, crisis_type)
    if existing:
        existing.heat = min(100, existing.heat + 8)
        return existing
    crisis = ActiveCrisis(
        crisis_id=f"{crisis_type}_{state.turn}",
        crisis_type=crisis_type,
        title=title,
        stage="response_window",
        heat=heat,
        duration=0,
        failure_flag=failure_flag,
        exit_condition="热度低于 25 或进入余波后持续 2 回合",
    )
    state.active_crises.append(crisis)
    return crisis


def update_crises(state: GameState, action: str, system_events: List[SystemEvent]) -> Tuple[List[SystemEvent], Dict[str, int]]:
    events: List[SystemEvent] = []
    diff: Dict[str, int] = {}
    text = action.lower()

    codes = {e.code for e in system_events}
    if "pr_response_window" in codes:
        _open_crisis(state, "public_relations", "舆论回应窗口", "舆论处理留下长期阴影", heat=55)
    if "health_injury_warning" in codes:
        _open_crisis(state, "health", "伤病危机窗口", "伤病债转为长期负担", heat=50)
    if "sasaeng_security_warning" in codes:
        _open_crisis(state, "safety", "私生安全危机", "私生安全阴影", heat=65)
    if "lens_harmony_crack" in codes:
        _open_crisis(state, "team_pr", "队内不和舆论窗口", "队内不和阴影", heat=60)

    for crisis in list(state.active_crises):
        if crisis.stage in {"closed", "converted"}:
            continue

        crisis.duration += 1

        respond_words = ["回应", "澄清", "声明", "道歉", "公司处理", "法律", "证据", "解释"]
        rest_words = ["休息", "康复", "医院", "医生", "物理治疗", "睡觉"]
        ignore_words = ["沉默", "不回应", "算了", "装没事", "硬撑"]

        if crisis.crisis_type in {"public_relations", "team_pr"}:
            if any(w in action for w in ignore_words):
                crisis.heat = min(100, crisis.heat + 10)
                _add(diff, "风险.公关危机风险", 4)
                _add(diff, "心理状态.精神压力", 3)
            elif any(w in action for w in respond_words):
                crisis.heat = max(0, crisis.heat - 18)
                crisis.company_involvement = min(100, crisis.company_involvement + 15)
                crisis.player_response = "已回应"
                crisis.stage = "aftermath" if crisis.heat < 45 else "response_window"
                _add(diff, "粉丝与舆论.粉丝信任基础", 3)
                _add(diff, "风险.公关危机风险", -6)
            else:
                crisis.heat = max(0, crisis.heat - 3)

        elif crisis.crisis_type == "health":
            if any(w in action for w in rest_words):
                crisis.heat = max(0, crisis.heat - 20)
                crisis.stage = "aftermath" if crisis.heat < 45 else "response_window"
                _add(diff, "身体状态.伤病风险", -8)
                _add(diff, "身体状态.体力", 8)
            elif any(w in action for w in ["高强度", "练舞", "加练", "硬撑"]):
                crisis.heat = min(100, crisis.heat + 15)
                _add(diff, "身体状态.伤病风险", 8)
                _add(diff, "风险.伤病爆发风险", 8)
            else:
                crisis.heat = max(0, crisis.heat - 2)

            if crisis.heat > 85:
                events.append(_crisis_event(
                    "health_collapse_forced_rest",
                    "健康危机：强制休养",
                    "伤病和疲劳已经超过可硬撑的范围。系统强制进入休养状态，部分高强度行动会被锁定。",
                    severity="crisis",
                    diff={"身体状态.体力": -5, "公司与合约.危机关注度": 8, "心理状态.精神压力": 5},
                ))
                state.status_effects["强制休养"] = max(state.status_effects.get("强制休养", 0), 2)

        elif crisis.crisis_type == "safety":
            if any(w in action for w in ["报警", "安保", "换宿舍", "换路线", "告诉经纪人", "公司处理"]):
                crisis.heat = max(0, crisis.heat - 18)
                _add(diff, "风险.私生风险", -8)
                _add(diff, "风险.行程泄露风险", -5)
            elif any(w in action for w in ["直播", "发定位", "晒", "公开行程"]):
                crisis.heat = min(100, crisis.heat + 12)
                _add(diff, "风险.私生风险", 6)
            else:
                crisis.heat = max(0, crisis.heat - 2)

        if crisis.heat < 25 and crisis.duration >= 2:
            crisis.stage = "closed"
            events.append(_crisis_event(
                f"crisis_closed_{crisis.crisis_type}",
                f"危机关闭：{crisis.title}",
                f"{crisis.title} 的热度已经下降，进入关闭状态。但相关记忆可能会在后续以余波形式回流。",
                severity="info",
                diff={"心理状态.精神压力": -3},
            ))
            if crisis.title not in state.resolved_flags:
                state.resolved_flags.append(crisis.title)

        elif crisis.duration >= 5 and crisis.heat >= 50:
            crisis.stage = "converted"
            if crisis.failure_flag and crisis.failure_flag not in state.flags:
                state.flags.append(crisis.failure_flag)
            events.append(_crisis_event(
                f"crisis_converted_{crisis.crisis_type}",
                f"危机转为长期后果：{crisis.title}",
                f"{crisis.title} 没有被有效处理，转化为长期标签或隐藏风险：{crisis.failure_flag}",
                severity="warning",
                diff={"心理状态.职业倦怠": 4, "粉丝与舆论.黑粉活跃度": 3},
            ))

    # 状态效果倒计时
    expired = []
    for key, turns in state.status_effects.items():
        if turns <= 1:
            expired.append(key)
        else:
            state.status_effects[key] = turns - 1
    for key in expired:
        del state.status_effects[key]
        events.append(_crisis_event(
            f"status_effect_expired_{key}",
            f"状态解除：{key}",
            f"{key} 的强制效果结束，但后续仍需要注意恢复。",
            severity="info",
        ))

    return events, diff
