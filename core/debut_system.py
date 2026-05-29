from __future__ import annotations

import random
from typing import Dict, List, Tuple
from core.models import GameState, SystemEvent


def ensure_debut_state(state: GameState) -> None:
    if not isinstance(getattr(state, "debut", None), dict):
        state.debut = {}
    d = state.debut
    d.setdefault("status", "not_candidate")
    d.setdefault("readiness", 0)
    d.setdefault("probability", 0)
    d.setdefault("window_turns_left", 0)
    d.setdefault("last_evaluation_turn", -1)
    d.setdefault("candidate_attempts", 0)
    d.setdefault("last_result", "")
    d.setdefault("history", [])


def _event(code: str, title: str, desc: str, severity: str = "info", diff: Dict[str, int] | None = None, flags: List[str] | None = None) -> SystemEvent:
    return SystemEvent(
        code=code,
        title=title,
        severity=severity,
        description=desc,
        source_system="debut",
        suggested_diff=diff or {},
        new_flags=flags or [title],
        tags=["debut"],
    )


def _avg(*values: int) -> float:
    nums = [int(v) for v in values]
    return sum(nums) / len(nums) if nums else 0


def hard_gate_passed(state: GameState) -> Tuple[bool, List[str]]:
    c = state.career
    b = state.body
    m = state.mind
    comp = state.company

    core = [c.get("舞蹈实力", 0), c.get("声乐实力", 0), c.get("舞台感染力", 0)]
    reasons: List[str] = []
    if sum(1 for x in core if int(x) >= 35) < 2:
        reasons.append("舞蹈/声乐/舞台感染力至少两项需要达到 35。")
    if b.get("体力", 0) < 35:
        reasons.append("体力低于 35。")
    if b.get("伤病风险", 100) > 65:
        reasons.append("伤病风险高于 65。")
    if m.get("精神压力", 100) > 80:
        reasons.append("精神压力高于 80。")
    if comp.get("公司信任度", 0) < 35:
        reasons.append("公司信任度低于 35。")
    if any(getattr(c, "stage", "") not in {"closed", "converted"} for c in getattr(state, "active_crises", []) or []):
        reasons.append("存在未解决重大危机。")
    if "强制休养" in getattr(state, "status_effects", {}):
        reasons.append("处于强制休养。")
    return not reasons, reasons


def debut_readiness_score(state: GameState) -> int:
    c = state.career
    b = state.body
    team = state.team
    comp = state.company
    fans = state.fans
    risks = state.risks

    health_stability = max(0, min(100, int(b.get("体力", 50)) - int(b.get("伤病风险", 0)) // 2 + int(b.get("嗓音状态", 50)) // 4))
    fan_base = min(100, int(fans.get("个人粉丝数", 0)) // 2000 + int(fans.get("粉丝信任基础", 50)) // 2)
    risk_penalty = (
        int(risks.get("公关危机风险", 0)) * 0.08
        + int(risks.get("伤病爆发风险", 0)) * 0.08
        + int(risks.get("霸凌排挤风险", 0)) * 0.04
        + int(risks.get("队内不和曝光风险", 0)) * 0.06
    )

    score = (
        0.18 * int(c.get("舞蹈实力", 0))
        + 0.18 * int(c.get("声乐实力", 0))
        + 0.10 * int(c.get("RAP能力", 0))
        + 0.14 * int(c.get("舞台感染力", 0))
        + 0.08 * int(c.get("形象指数", 0))
        + 0.08 * int(c.get("语言能力", 0))
        + 0.08 * int(team.get("团队默契度", team.get("团队默契", 45)))
        + 0.08 * int(comp.get("公司信任度", 0))
        + 0.04 * fan_base
        + 0.04 * health_stability
        - risk_penalty
    )

    # Company resource and concept fit modifiers.
    resource_pool = int(comp.get("资源池", 50))
    launch_pressure = int(comp.get("出道窗口压力", 45))
    score += (int(comp.get("资源倾斜度", 30)) - 30) * 0.04
    score += (resource_pool - 50) * 0.05
    score += (launch_pressure - 45) * 0.03
    if "出道概念适配" in " ".join(getattr(state, "flags", []) or []):
        score += 5
    return max(0, min(100, int(round(score))))


def readiness_to_probability(readiness: int) -> int:
    if readiness < 50:
        return 0
    if readiness <= 59:
        return 18
    if readiness <= 69:
        return 35
    if readiness <= 79:
        return 58
    if readiness <= 89:
        return 78
    return 90


def should_evaluate_debut(state: GameState, action: str) -> bool:
    if not state.is_trainee_stage():
        return False
    if any(w in action for w in ["出道", "候选", "公司会议", "出道组", "月末考核", "季度评估"]):
        return True
    return int(state.turn) > 0 and int(state.turn) % 24 == 0


def evaluate_debut_system(state: GameState, action: str) -> Tuple[List[SystemEvent], Dict[str, int]]:
    ensure_debut_state(state)
    events: List[SystemEvent] = []
    diff: Dict[str, int] = {}

    if not should_evaluate_debut(state, action):
        if int(state.debut.get("window_turns_left", 0)) > 0:
            state.debut["window_turns_left"] = max(0, int(state.debut["window_turns_left"]) - 1)
        return events, diff

    passed, reasons = hard_gate_passed(state)
    readiness = debut_readiness_score(state)
    probability = readiness_to_probability(readiness) if passed else 0
    state.debut["readiness"] = readiness
    state.debut["probability"] = probability
    state.debut["last_evaluation_turn"] = int(state.turn)

    if not passed or readiness < 50:
        state.debut["status"] = "not_ready"
        state.debut["last_result"] = "未进入出道候选窗口"
        events.append(_event(
            "debut_not_ready",
            "出道评估：暂未进入候选窗口",
            "能力、健康、公司信任或危机状态仍未达到出道候选门槛。能力到了也不会自动出道，公司会综合判断。",
            "info",
            {},
            ["出道评估未通过"],
        ))
        state.debut["history"].append({"turn": state.turn + 1, "readiness": readiness, "probability": probability, "result": "not_ready", "reasons": reasons})
        return events, diff

    state.debut["candidate_attempts"] = int(state.debut.get("candidate_attempts", 0)) + 1
    state.debut["window_turns_left"] = 8
    seed_text = f"{state.save_name}-{state.turn}-{readiness}-{state.debut['candidate_attempts']}"
    roll = random.Random(seed_text).randint(1, 100)

    if roll <= probability:
        state.debut["status"] = "confirmed"
        state.debut["last_result"] = "进入出道准备"
        state.current_stage = "出道准备期"
        state.current_mainline = "出道组确认与正式准备"
        state.current_schedule = "出道准备会议"
        diff["公司与合约.主推指数"] = diff.get("公司与合约.主推指数", 0) + 8
        diff["市场.话题度"] = diff.get("市场.话题度", 0) + 5
        events.append(_event(
            "debut_confirmed",
            "重大节点：进入出道准备",
            f"出道准备度 {readiness}，系统概率 {probability}%，本次内部判断通过。公司开始把你放进出道准备流程。",
            "crisis",
            diff.copy(),
            ["进入出道准备期", "出道候选通过"],
        ))
        result = "confirmed"
    else:
        state.debut["status"] = "candidate_deferred"
        state.debut["last_result"] = "候选但延期"
        diff["心理状态.精神压力"] = diff.get("心理状态.精神压力", 0) + 3
        diff["公司与合约.公司信任度"] = diff.get("公司与合约.公司信任度", 0) + 1
        events.append(_event(
            "debut_deferred",
            "出道评估：候选但延期",
            f"出道准备度 {readiness}，系统概率 {probability}%，本次内部判断未通过。原因可能是公司资源、组合概念、市场时机或同期竞争。",
            "warning",
            diff.copy(),
            ["出道候选延期"],
        ))
        result = "deferred"

    state.debut["history"].append({"turn": state.turn + 1, "readiness": readiness, "probability": probability, "roll": roll, "result": result})
    return events, diff
