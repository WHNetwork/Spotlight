from __future__ import annotations

from typing import Dict, Tuple, List
from core.models import GameState

CATEGORY_MAP = {
    "职业属性": "career",
    "身体状态": "body",
    "心理状态": "mind",
    "公司与合约": "company",
    "公司状态": "company",
    "团队关系": "team",
    "团队状态": "team",
    "粉丝与舆论": "fans",
    "粉丝状态": "fans",
    "市场": "market",
    "市场状态": "market",
    "风险": "risks",
    "风险状态": "risks",
    "回归": "comeback",
    "回归状态": "comeback",
    "练习生日常": "trainee_life",
    "练习生状态": "trainee_life",
    "市场成绩": "market_scores",
    "成绩状态": "market_scores",
    "商业资源": "commercial",
    "商业状态": "commercial",
    "合约条款": "contract_terms",
    "续约状态": "contract_terms",
}

def clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(value)))

def _add(diff: Dict[str, int], key: str, value: int) -> None:
    diff[key] = diff.get(key, 0) + value

def base_diff_for_action(action: str, state: GameState) -> Dict[str, int]:
    text = action.lower()
    diff: Dict[str, int] = {}

    if any(word in action for word in ["舞蹈", "跳舞", "编舞", "热身", "练动作", "练习", "加练", "练舞", "排练", "彩排"]):
        _add(diff, "职业属性.舞蹈实力", 1)
        _add(diff, "身体状态.体力", -8)
        _add(diff, "身体状态.肌肉疲劳", 5)
        _add(diff, "风险.伤病爆发风险", 2)

    if any(word in action for word in ["声乐", "唱", "录音", "高音", "练歌"]):
        _add(diff, "职业属性.声乐实力", 1)
        _add(diff, "身体状态.体力", -5)
        _add(diff, "身体状态.嗓音状态", -4)

    if any(word in text for word in ["rap", "说唱"]) or "节奏训练" in action:
        _add(diff, "职业属性.RAP能力", 1)
        _add(diff, "身体状态.体力", -4)

    # 创作能力只来自实际训练/实作，不来自单纯表达想法。
    if any(word in action for word in ["作词训练", "作曲训练", "编曲", "写demo", "写一个练习用 demo", "修改demo", "PD指导", "编舞课"]):
        _add(diff, "职业属性.创作能力", 1)
        _add(diff, "身体状态.体力", -3)

    # 制作人能力需要创作能力与实际项目门槛。
    if state.career.get("创作能力", 0) >= 45 and any(word in action for word in ["作品被采纳", "参与概念会议", "收录曲署名", "制作会议"]):
        _add(diff, "职业属性.制作人能力", 1)

    if any(word in action for word in ["休息", "睡", "早点回去", "不练了", "放松"]):
        _add(diff, "身体状态.体力", 12)
        _add(diff, "身体状态.睡眠质量", 6)
        _add(diff, "心理状态.精神压力", -4)
        _add(diff, "身体状态.肌肉疲劳", -5)

    if any(word in action for word in ["物理治疗", "康复", "医院", "医生", "冰敷", "护具"]):
        _add(diff, "身体状态.伤病风险", -8)
        _add(diff, "身体状态.旧伤负担", -3)
        _add(diff, "身体状态.肌肉疲劳", -4)
        _add(diff, "公司与合约.公司满意度", -1)

    if any(word in action for word in ["打招呼", "聊天", "谈心", "队友", "沟通", "陪", "一起"]):
        _add(diff, "团队关系.真实关系温度", 3)
        _add(diff, "团队关系.队内信任度", 2)
        _add(diff, "心理状态.孤独感", -3)

    if any(word in action for word in ["经纪人", "公司", "老师", "PD", "制作人", "主管"]):
        _add(diff, "公司与合约.公司信任度", 1)
        _add(diff, "公司与合约.公司满意度", 1)

    if any(word in action for word in ["SNS", "Bubble", "Weverse", "直播", "发文", "回复粉丝"]):
        _add(diff, "粉丝与舆论.粉丝信任基础", 2)
        _add(diff, "市场.话题度", 1)
        _add(diff, "风险.私生风险", 1)

    if any(word in action for word in ["沉默", "不回应", "忍", "算了", "装没事"]):
        _add(diff, "心理状态.精神压力", 2)
        _add(diff, "心理状态.自我认同", -1)

    if any(word in action for word in ["回应", "澄清", "声明", "道歉", "公关"]):
        _add(diff, "风险.公关危机风险", -3)
        _add(diff, "公司与合约.危机关注度", 2)

    # 表达制作意向只影响认同和 flag，不直接加制作人能力。
    if any(word in action for word in ["我想参与制作", "自己想法", "表达权", "回归风格", "概念方向"]):
        _add(diff, "心理状态.自我认同", 2)
        _add(diff, "公司与合约.公司信任度", -1)

    if any(word in action for word in ["月末考核展示", "评估录像", "展示段落", "考核曲"]):
        _add(diff, "公司与合约.公司信任度", 1)
        _add(diff, "团队关系.队内竞争度", 1)

    return diff

def sanitize_suggested_diff(state: GameState, diff: Dict[str, int], action: str) -> Dict[str, int]:
    """限制模型把不合理属性加上去。"""
    clean = dict(diff)
    # 如果不是实际制作项目，不允许模型给制作人能力。
    if "职业属性.制作人能力" in clean:
        allowed = state.career.get("创作能力", 0) >= 45 and any(
            word in action for word in ["作品被采纳", "参与概念会议", "收录曲署名", "制作会议"]
        )
        if not allowed:
            clean.pop("职业属性.制作人能力", None)
    return clean

def apply_diff(state: GameState, diff: Dict[str, int], max_abs_delta: int = 8) -> Dict[str, Tuple[int, int]]:
    applied: Dict[str, Tuple[int, int]] = {}
    for raw_key, raw_delta in diff.items():
        if not isinstance(raw_delta, int):
            continue
        delta = max(-max_abs_delta, min(max_abs_delta, raw_delta))
        if "." not in raw_key:
            continue
        category, name = raw_key.split(".", 1)
        attr_name = CATEGORY_MAP.get(category)
        if not attr_name:
            continue
        target = getattr(state, attr_name, None)
        if not isinstance(target, dict):
            continue
        if name not in target or not isinstance(target[name], int):
            continue
        old = int(target[name])
        new = clamp(old + delta)
        target[name] = new
        if old != new:
            applied[raw_key] = (old, new)
    return applied

def threshold_warnings(state: GameState) -> List[str]:
    warnings: List[str] = []
    if state.body.get("体力", 100) < 40:
        warnings.append("体力低于 40：训练收益下降，疲劳相关事件概率上升。")
    if state.body.get("体力", 100) < 20:
        warnings.append("体力低于 20：高强度训练被锁定，必须先恢复或处理健康。")
    if state.body.get("睡眠质量", 100) < 40:
        warnings.append("睡眠质量低于 40：免疫下降、注意力波动、生病风险上升。")
    if state.body.get("伤病风险", 0) > 75:
        warnings.append("伤病风险高于 75：下回合必须优先考虑休息、康复或降低训练强度。")
    if state.mind.get("心情", 100) < 30:
        warnings.append("心情低于 30：综艺事故、队友误会、职业倦怠事件概率上升。")
    if state.mind.get("精神压力", 0) > 90:
        warnings.append("精神压力高于 90：公开回应、直播、综艺和高压考核会被限制。")
    if state.company.get("公司满意度", 100) < 35:
        warnings.append("公司满意度低于 35：资源减少、谈话警告、定位调整概率上升。")
    return warnings
