from __future__ import annotations

from typing import Dict, List, Tuple

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
        source_system="brand_contract",
        suggested_diff=diff or {},
        new_flags=flags or [title],
        tags=["brand_contract"],
    )


def clamp(v: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(v)))


def ensure_brand_contract_state(state: GameState) -> None:
    if not isinstance(getattr(state, "commercial", None), dict):
        state.commercial = {}
    commercial = state.commercial
    commercial.setdefault("商业安全度", 70)
    commercial.setdefault("品牌适配度", 45)
    commercial.setdefault("代言数量", 0)
    commercial.setdefault("杂志资源", 0)
    commercial.setdefault("奢侈品关系", 0)
    commercial.setdefault("个人收入", 0)
    commercial.setdefault("公司分成比例", 70)
    commercial.setdefault("粉丝购买力", 0)
    commercial.setdefault("争议商业风险", 10)
    commercial.setdefault("last_commercial_note", "")

    if not isinstance(getattr(state, "contract_terms", None), dict):
        state.contract_terms = {}
    contract = state.contract_terms
    contract.setdefault("合约剩余月数", 84)
    contract.setdefault("玩家续约意愿", 50)
    contract.setdefault("队友续约意向", 50)
    contract.setdefault("分成比例", int(commercial.get("公司分成比例", 70)))
    contract.setdefault("solo权限", 10)
    contract.setdefault("演员约权限", 10)
    contract.setdefault("创作署名权", 5)
    contract.setdefault("休假保障", 25)
    contract.setdefault("健康保障", 35)
    contract.setdefault("工作室可能性", 0)
    contract.setdefault("团体存续概率", 65)
    contract.setdefault("last_contract_note", "")


def _recalculate_commercial_baseline(state: GameState) -> None:
    commercial = state.commercial
    image = int(state.career.get("形象指数", 0))
    brand = int(state.market.get("品牌价值", 0))
    public_goodwill = int(state.fans.get("路人好感", 40))
    risk = int(state.risks.get("公关危机风险", 0)) + int(state.risks.get("恋爱风险", 0)) + int(state.risks.get("霸凌排挤风险", 0))
    fan_power = int(state.fans.get("个人粉丝数", 0)) // 3000 + int(state.fans.get("唯粉规模", 0)) * 2

    commercial["商业安全度"] = clamp(55 + public_goodwill // 3 + brand // 4 - risk // 5)
    commercial["品牌适配度"] = clamp(20 + image // 2 + brand // 2)
    commercial["粉丝购买力"] = clamp(fan_power)
    commercial["争议商业风险"] = clamp(risk // 3)


def _recalculate_bargaining_power(state: GameState) -> None:
    commercial = state.commercial
    contract = state.contract_terms
    market_scores = getattr(state, "market_scores", {}) if isinstance(getattr(state, "market_scores", None), dict) else {}
    score = (
        int(state.market.get("品牌价值", 0))
        + int(commercial.get("商业安全度", 0)) // 2
        + int(commercial.get("粉丝购买力", 0)) // 2
        + int(state.company.get("主推指数", 0)) // 2
        + int(market_scores.get("年度奖项积分", 0)) // 2
        - int(commercial.get("争议商业风险", 0)) // 2
        - int(state.body.get("伤病风险", 0)) // 4
    )
    state.company["个人议价权"] = clamp(score)
    contract["团体存续概率"] = clamp(45 + int(state.team.get("团队默契度", 45)) // 3 + int(state.fans.get("团粉稳定度", 50)) // 4 - int(state.team.get("队内竞争度", 35)) // 4)


def evaluate_brand_contract_system(state: GameState, action: str) -> Tuple[List[SystemEvent], Dict[str, int]]:
    ensure_brand_contract_state(state)
    events: List[SystemEvent] = []
    diff: Dict[str, int] = {}
    if state.is_trainee_stage():
        return events, diff

    _recalculate_commercial_baseline(state)
    _recalculate_bargaining_power(state)

    commercial = state.commercial
    contract = state.contract_terms
    brand_action = any(w in action for w in ["品牌", "广告", "代言", "杂志", "奢侈品", "商业", "直播带货", "封面", "美妆", "时尚"])
    contract_action = any(w in action for w in ["续约", "合同", "分成", "谈判", "工作室", "健康保障", "休假", "署名权", "solo权限", "演员约"])

    if brand_action:
        if int(commercial.get("商业安全度", 0)) < 45:
            events.append(_event(
                "brand_safety_low",
                "品牌方进入观望",
                "当前商业安全度偏低。品牌合作会变得保守，叙事中应体现法务条款、临时取消或品牌方等待舆论稳定。",
                "warning",
                {"市场.品牌价值": -2, "公司与合约.危机关注度": 2},
                ["品牌方观望"],
            ))
        else:
            commercial["代言数量"] = min(99, int(commercial.get("代言数量", 0)) + 1)
            commercial["个人收入"] = int(commercial.get("个人收入", 0)) + max(1, int(state.market.get("品牌价值", 0)) * 3)
            commercial["last_commercial_note"] = "新增商业接触或合作机会"
            events.append(_event(
                "brand_opportunity_opened",
                "商业资源机会打开",
                "品牌、杂志或广告机会进入视野。它会提高品牌价值和收入，但也会挤压休息并增加公开审视。",
                "info",
                {"市场.品牌价值": 3, "风险.私生风险": 1, "身体状态.体力": -1},
                ["商业资源机会"],
            ))

    if contract_action:
        bargaining = int(state.company.get("个人议价权", 0))
        if bargaining >= 65:
            contract["solo权限"] = clamp(int(contract.get("solo权限", 0)) + 8)
            contract["演员约权限"] = clamp(int(contract.get("演员约权限", 0)) + 6)
            contract["创作署名权"] = clamp(int(contract.get("创作署名权", 0)) + 6)
            contract["休假保障"] = clamp(int(contract.get("休假保障", 0)) + 5)
            contract["健康保障"] = clamp(int(contract.get("健康保障", 0)) + 5)
            contract["last_contract_note"] = "议价权足以提出实质条款"
            events.append(_event(
                "contract_bargaining_strong",
                "续约谈判：议价权较强",
                "玩家已有足够成绩、商业价值或公司依赖度提出条款。公司不一定全答应，但不能按无条件续约处理。",
                "crisis",
                {"公司与合约.续约倾向": 2, "团队关系.队内竞争度": 1},
                ["续约议价权较强"],
            ))
        else:
            contract["last_contract_note"] = "议价权不足，谈判会付出代价"
            events.append(_event(
                "contract_bargaining_weak",
                "续约谈判：议价权不足",
                "当前个人议价权不足。强行谈判可能争取保护条款，但会增加公司审视和路线不稳定。",
                "warning",
                {"公司与合约.公司满意度": -2, "心理状态.精神压力": 2},
                ["续约议价权不足"],
            ))

    for ev in events:
        for key, value in ev.suggested_diff.items():
            diff[key] = diff.get(key, 0) + value
    return events, diff
