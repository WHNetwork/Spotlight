from __future__ import annotations

import random
from typing import Dict, List, Tuple
from core.models import GameState, SystemEvent


def ensure_ending_state(state: GameState) -> None:
    if not isinstance(getattr(state, "ending", None), dict):
        state.ending = {}
    e = state.ending
    e.setdefault("status", "ongoing")
    e.setdefault("window", "closed")
    e.setdefault("candidate_endings", [])
    e.setdefault("last_evaluation_turn", -1)
    e.setdefault("final_result", "")
    e.setdefault("history", [])


def _event(code: str, title: str, desc: str, severity: str = "info", diff: Dict[str, int] | None = None, flags: List[str] | None = None) -> SystemEvent:
    return SystemEvent(
        code=code,
        title=title,
        severity=severity,
        description=desc,
        source_system="ending",
        suggested_diff=diff or {},
        new_flags=flags or [title],
        tags=["ending"],
    )


def is_idol_stage(state: GameState) -> bool:
    text = f"{state.current_stage} {state.current_mainline} {state.current_schedule}".lower()
    return any(w in text for w in ["爱豆", "出道", "回归", "打歌", "巡演", "续约", "solo", "团体活动"]) and not state.is_trainee_stage()


def should_evaluate_ending(state: GameState, action: str) -> bool:
    if not is_idol_stage(state):
        return False
    if any(w in action for w in ["续约", "不续约", "退团", "转型", "solo", "演员", "制作人", "暂停活动", "结局"]):
        return True
    # Rough long-play windows: every 52 turns after debut, plus contract-like periods.
    return int(state.turn) >= 156 and int(state.turn) % 26 == 0


def route_scores(state: GameState) -> Dict[str, int]:
    c = state.career
    comp = state.company
    team = state.team
    fans = state.fans
    market = state.market
    risks = state.risks
    body = state.body
    mind = state.mind

    health_penalty = int(body.get("伤病风险", 0)) * 0.18 + max(0, int(mind.get("职业倦怠", 0)) - 60) * 0.20
    crisis_penalty = int(risks.get("公关危机风险", 0)) * 0.15 + int(risks.get("队内不和曝光风险", 0)) * 0.12

    return {
        "顶级团队核心": int(0.22*c.get("舞台感染力", 0) + 0.18*c.get("舞蹈实力", 0) + 0.15*c.get("声乐实力", 0) + 0.15*team.get("团队默契度", team.get("团队默契", 45)) + 0.12*comp.get("主推指数", 0) + 0.10*fans.get("团粉稳定度", 50) - crisis_penalty),
        "稳定团体成员": int(0.18*team.get("队内信任度", 45) + 0.16*c.get("舞台感染力", 0) + 0.14*c.get("声乐实力", 0) + 0.14*c.get("舞蹈实力", 0) + 0.10*body.get("体力", 50) - health_penalty*0.5),
        "Solo 成功": int(0.22*c.get("舞台感染力", 0) + 0.18*fans.get("个人粉丝数", 0)/2000 + 0.16*comp.get("个人议价权", 0) + 0.12*market.get("品牌价值", 0) + 0.10*c.get("声乐实力", 0) - crisis_penalty),
        "演员转型": int(0.28*c.get("演技潜力", 0) + 0.18*c.get("形象指数", 0) + 0.14*fans.get("路人好感", 40) + 0.10*market.get("品牌价值", 0) - crisis_penalty*0.6),
        "制作人/创作者": int(0.30*c.get("创作能力", 0) + 0.25*c.get("制作人能力", 0) + 0.14*comp.get("个人议价权", 0) + 0.10*market.get("音源潜力", 30)),
        "海外市场突破": int(0.16*c.get("语言能力", 0) + 0.14*market.get("中国市场影响力", 0) + 0.14*market.get("日本市场影响力", 0) + 0.14*market.get("东南亚市场影响力", 0) + 0.14*market.get("欧美市场影响力", 0) + 0.12*fans.get("粉丝信任基础", 50)),
        "健康休养": int(0.35*body.get("伤病风险", 0) + 0.20*mind.get("职业倦怠", 0) + 0.10*risks.get("伤病爆发风险", 0)),
        "合约到期不续": int(0.22*(100-comp.get("续约倾向", 50)) + 0.16*(100-comp.get("合约稳定度", 70)) + 0.10*mind.get("职业倦怠", 0) + 0.10*comp.get("个人议价权", 0)),
        "争议后重建": int(0.20*risks.get("公关危机风险", 0) + 0.16*fans.get("粉丝信任基础", 50) + 0.12*comp.get("危机关注度", 0)),
    }


def evaluate_ending_system(state: GameState, action: str) -> Tuple[List[SystemEvent], Dict[str, int]]:
    ensure_ending_state(state)
    events: List[SystemEvent] = []
    diff: Dict[str, int] = {}

    if not should_evaluate_ending(state, action):
        return events, diff

    scores = route_scores(state)
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    state.ending["candidate_endings"] = [{"name": name, "score": score} for name, score in ranked[:5]]
    state.ending["last_evaluation_turn"] = int(state.turn)

    top_name, top_score = ranked[0]
    if top_score < 45:
        state.ending["window"] = "closed"
        events.append(_event(
            "ending_not_ready",
            "结局评估：仍在路上",
            "当前路线尚未形成稳定结局。继续推进职业、关系、公司和健康状态后，系统会重新评估。",
            "info",
            {},
            ["结局评估：仍在路上"],
        ))
        return events, diff

    state.ending["window"] = "open"
    seed = f"{state.save_name}-{state.turn}-{top_name}-{top_score}"
    roll = random.Random(seed).randint(1, 100)
    probability = min(85, max(25, top_score))
    if roll <= probability and any(w in action for w in ["续约", "不续约", "退团", "转型", "暂停活动", "结局"]):
        state.ending["status"] = "resolved"
        state.ending["final_result"] = top_name
        events.append(_event(
            "ending_resolved",
            f"路线结局：{top_name}",
            f"路线评分 {top_score}，概率 {probability}%。本次关键选择让职业线进入阶段性结局。",
            "crisis",
            {},
            [f"路线结局：{top_name}"],
        ))
        result = "resolved"
    else:
        events.append(_event(
            "ending_window_open",
            f"结局窗口：{top_name}",
            f"当前最强路线为 {top_name}，评分 {top_score}。这只是候选窗口，不会自动结束；关键选择会影响最终结局。",
            "warning",
            {},
            [f"结局候选：{top_name}"],
        ))
        result = "window_open"

    state.ending["history"].append({"turn": state.turn + 1, "top": top_name, "score": top_score, "probability": probability, "roll": roll, "result": result})
    return events, diff
