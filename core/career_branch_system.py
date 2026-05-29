from __future__ import annotations

from typing import Any, Dict, List, Tuple

from core.models import GameState, SystemEvent


def _event(
    code: str,
    title: str,
    desc: str,
    severity: str = "info",
    diff: Dict[str, int] | None = None,
    flags: List[str] | None = None,
) -> SystemEvent:
    return SystemEvent(
        code=code,
        title=title,
        severity=severity,
        description=desc,
        source_system="career_branch",
        suggested_diff=diff or {},
        new_flags=flags or [title],
        tags=["career_branch"],
    )


def ensure_career_branch_state(state: GameState) -> None:
    if not isinstance(getattr(state, "career_branches", None), dict):
        state.career_branches = {}
    cb = state.career_branches
    cb.setdefault("acting_path_stage", "未开启")
    cb.setdefault("solo_path_stage", "未开启")
    cb.setdefault("unit_path_stage", "未开启")
    cb.setdefault("creative_path_stage", "未开启")
    cb.setdefault("rights_path_stage", "未开启")
    cb.setdefault("branch_opportunities", [])
    cb.setdefault("branch_history", [])


def _remember(state: GameState, opportunity: str) -> None:
    cb = state.career_branches
    opportunities: List[str] = list(cb.get("branch_opportunities", []))
    if opportunity not in opportunities:
        opportunities.append(opportunity)
    cb["branch_opportunities"] = opportunities[-10:]
    history: List[Dict[str, Any]] = list(cb.get("branch_history", []))
    history.append({"turn": state.turn + 1, "opportunity": opportunity})
    cb["branch_history"] = history[-12:]


def evaluate_career_branch_system(state: GameState, action: str) -> Tuple[List[SystemEvent], Dict[str, int]]:
    ensure_career_branch_state(state)
    events: List[SystemEvent] = []
    diff: Dict[str, int] = {}
    if state.is_trainee_stage():
        return events, diff

    cb = state.career_branches
    c = state.career
    m = state.market
    fans = state.fans
    comp = state.company
    mind = state.mind
    market_scores = getattr(state, "market_scores", {}) if isinstance(getattr(state, "market_scores", None), dict) else {}

    acting_score = int(c.get("演技潜力", 0)) + int(c.get("形象指数", 0)) + int(m.get("品牌价值", 0))
    solo_score = int(fans.get("个人粉丝数", 0)) // 2500 + int(comp.get("主推指数", 0)) + int(market_scores.get("直拍传播力", 0))
    creative_score = int(c.get("创作能力", 0)) + int(c.get("制作人能力", 0)) + int(mind.get("自我认同", 0)) // 2
    rights_pressure = int(mind.get("职业倦怠", 0)) + int(state.risks.get("私生风险", 0)) + int(state.risks.get("霸凌排挤风险", 0))

    if acting_score >= 115 or any(w in action for w in ["试镜", "演员", "网剧", "短剧", "客串"]):
        cb["acting_path_stage"] = "客串/试镜观察"
        _remember(state, "演员路线测试")
        events.append(_event(
            "career_branch_acting_test",
            "职业分岔：演员路线测试",
            "演员路线开始出现，但它会挤压团体训练和队内资源平衡。不能直接跳到转型成功。",
            "info",
            {"市场.品牌价值": 2, "团队关系.队内资源平衡": -1},
            ["演员路线测试"],
        ))

    if solo_score >= 105 or any(w in action for w in ["solo", "Solo", "个人曲", "个人舞台", "小分队", "unit", "Unit"]):
        if any(w in action for w in ["小分队", "unit", "Unit"]):
            cb["unit_path_stage"] = "小分队测试"
            opportunity = "Unit路线测试"
        else:
            cb["solo_path_stage"] = "个人活动测试"
            opportunity = "Solo路线测试"
        _remember(state, opportunity)
        events.append(_event(
            "career_branch_solo_unit_test",
            f"职业分岔：{opportunity}",
            "个人或小分队活动会测试市场，但也会带来唯粉、团粉和队友资源落差问题。",
            "warning",
            {"粉丝与舆论.唯粉攻击性": 2, "团队关系.队内竞争度": 2, "公司与合约.个人议价权": 1},
            [opportunity],
        ))

    if creative_score >= 95 or any(w in action for w in ["投稿", "作词", "作曲", "编舞", "制作", "署名", "概念提案"]):
        cb["creative_path_stage"] = "提案/署名观察"
        _remember(state, "创作路线测试")
        events.append(_event(
            "career_branch_creative_test",
            "职业分岔：创作路线测试",
            "创作表达权开始进入公司视野。被否定也会积累经验、伏笔和自我认同变化。",
            "info",
            {"职业属性.创作能力": 1, "心理状态.自我认同": 1, "公司与合约.公司信任度": -1},
            ["创作路线测试"],
        ))

    if rights_pressure >= 150 or any(w in action for w in ["维权", "暂停活动", "休养", "解约", "退团", "退圈", "换公司", "谈判"]):
        cb["rights_path_stage"] = "谈判/保护自己观察"
        _remember(state, "暂停或维权路线观察")
        events.append(_event(
            "career_branch_rights_path",
            "职业分岔：保护自己路线",
            "暂停、维权、换公司或退出不是自动失败。系统会看证据、健康、合同、粉丝支持、公司态度和队友配合。",
            "crisis",
            {"公司与合约.危机关注度": 3, "心理状态.精神压力": 2, "公司与合约.个人议价权": 1},
            ["保护自己路线观察"],
        ))

    for ev in events:
        for key, value in ev.suggested_diff.items():
            diff[key] = diff.get(key, 0) + value
    return events, diff
