from __future__ import annotations

from typing import Dict, List
from core.models import GameState, SystemEvent


ABILITY_CATALOG: Dict[str, Dict[str, object]] = {
    "动作记忆": {
        "desc": "舞蹈训练更容易稳定吸收，但高强度连续训练时会积累疲劳。",
        "requires": {"career": {"舞蹈实力": 12}, "talents": {"舞蹈天赋": 65}},
    },
    "镜头捕捉": {
        "desc": "评估录像、公开视频或直拍中更容易被注意，同时黑粉和唯粉关注也会提高。",
        "requires": {"career": {"舞台感染力": 12}, "talents": {"镜头天赋": 65}},
    },
    "稳定音准": {
        "desc": "声乐考核稳定性提升，但连续声乐训练会更明显消耗嗓音状态。",
        "requires": {"career": {"声乐实力": 12}, "talents": {"声乐天赋": 65}},
    },
    "即兴接话": {
        "desc": "直播、采访、综艺中更容易接住冷场；精神压力高时失言风险仍会上升。",
        "requires": {"career": {"综艺感": 12}, "talents": {"综艺天赋": 65}},
    },
    "demo起步": {
        "desc": "可以提交练习用 demo。被否定会影响自我认同，被指导会提高创作能力。",
        "requires": {"career": {"创作能力": 10}, "talents": {"创作天赋": 60}},
    },
    "考核solo段": {
        "desc": "练习生阶段可以争取个人展示段落，但会提高同期竞争度。",
        "requires": {"career": {"舞台感染力": 14}, "talents": {"抗压天赋": 55}},
    },
    "概念表达权": {
        "desc": "可以在概念课或回归会议中提出更完整方向，但公司是否采纳取决于信任与阶段。",
        "requires": {"career": {"创作能力": 18}, "company": {"公司信任度": 55}},
    },
    "写进歌词": {
        "desc": "能把心事转化为歌词、日记或 demo，降低秘密重量，并小幅提高创作成长。",
        "requires": {"career": {"创作能力": 8}, "talents": {"创作天赋": 55}},
    },
    "制作参与者": {
        "desc": "可以影响收录曲、unit 或 solo 风格。该能力不应在练习生早期出现。",
        "requires": {"career": {"创作能力": 45, "制作人能力": 15}, "company": {"公司信任度": 60}},
    },
}


def _meets(state: GameState, req: Dict[str, Dict[str, int]]) -> bool:
    for group, conds in req.items():
        source = getattr(state, group, None)
        if not isinstance(source, dict):
            return False
        for key, threshold in conds.items():
            if int(source.get(key, 0)) < int(threshold):
                return False
    return True


def update_abilities(state: GameState) -> List[SystemEvent]:
    unlocked: List[SystemEvent] = []
    current = set(state.abilities)

    for name, spec in ABILITY_CATALOG.items():
        if name in current:
            continue
        if name == "制作参与者" and state.is_trainee_stage():
            continue
        if _meets(state, spec.get("requires", {})):
            state.abilities.append(name)
            unlocked.append(SystemEvent(
                code=f"ability_unlocked_{name}",
                title=f"能力解锁：{name}",
                severity="opportunity",
                source_system="abilities",
                description=str(spec.get("desc", "")),
                new_flags=[f"能力解锁：{name}"],
                tags=["ability"],
            ))

    return unlocked


def ability_passive_diff(state: GameState, action: str) -> Dict[str, int]:
    diff: Dict[str, int] = {}

    def add(key: str, v: int) -> None:
        diff[key] = diff.get(key, 0) + v

    abilities = set(state.abilities)

    if "动作记忆" in abilities and any(w in action for w in ["舞蹈", "练舞", "编舞"]):
        add("职业属性.舞蹈实力", 1)
        if "高强度" in action or "加练" in action:
            add("身体状态.肌肉疲劳", 1)

    if "稳定音准" in abilities and any(w in action for w in ["声乐", "唱", "练歌"]):
        add("职业属性.声乐实力", 1)
        add("身体状态.嗓音状态", -1)

    if "镜头捕捉" in abilities and any(w in action for w in ["评估录像", "考核", "公开视频", "镜头"]):
        add("市场.话题度", 1)
        add("粉丝与舆论.黑粉活跃度", 1)

    if "即兴接话" in abilities and any(w in action for w in ["直播", "综艺", "采访", "接话"]):
        add("粉丝与舆论.粉丝信任基础", 1)
        if state.mind.get("精神压力", 0) > 75:
            add("风险.公关危机风险", 2)

    if "考核solo段" in abilities and any(w in action for w in ["个人展示", "solo段", "展示段落", "考核"]):
        add("团队关系.队内竞争度", 2)
        add("市场.话题度", 1)

    if "写进歌词" in abilities and any(w in action for w in ["歌词", "写歌", "日记", "demo", "写下来"]):
        add("职业属性.创作能力", 1)
        add("心理状态.精神压力", -1)

    return diff
