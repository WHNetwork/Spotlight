from __future__ import annotations

from typing import Dict, List, Tuple
from core.models import GameState, SystemEvent


CAREER_TO_SKILL = {
    "舞蹈实力": "dance",
    "声乐实力": "vocal",
    "RAP能力": "rap",
    "舞台感染力": "stage",
    "综艺感": "variety",
    "语言能力": "language",
    "形象指数": "image",
    "演技潜力": "acting",
    "创作能力": "creative",
    "制作人能力": "producer",
}

SKILL_TO_CAREER = {v: k for k, v in CAREER_TO_SKILL.items()}

ACTION_SKILL_WORDS = {
    "dance": ["舞蹈", "跳舞", "编舞", "热身", "练动作", "加练", "练舞", "彩排"],
    "vocal": ["声乐", "唱", "录音", "高音", "练歌", "live", "Live"],
    "rap": ["RAP", "rap", "说唱", "节奏训练"],
    "stage": ["舞台", "考核展示", "评估录像", "直拍", "打歌", "表情管理", "镜头"],
    "variety": ["综艺", "采访", "直播", "mc", "MC", "talk", "Talk"],
    "language": ["韩语", "日语", "英语", "语言", "敬语", "采访"],
    "acting": ["演技", "表演课", "演员", "台词"],
    "creative": ["作词", "作曲", "编曲", "demo", "Demo", "写歌", "修改demo", "创作"],
    "producer": ["制作会议", "概念会议", "收录曲署名", "制作人", "作品被采纳"],
}


def ensure_progression_state(state: GameState) -> None:
    if not isinstance(getattr(state, "progression", None), dict):
        state.progression = {}
    p = state.progression
    p.setdefault("skill_xp", {skill: 0 for skill in SKILL_TO_CAREER})
    p.setdefault("skill_total_xp", {skill: 0 for skill in SKILL_TO_CAREER})
    p.setdefault("growth_log", [])
    p.setdefault("last_growth_turn", {})

    # Backfill missing skills.
    for skill in SKILL_TO_CAREER:
        p["skill_xp"].setdefault(skill, 0)
        p["skill_total_xp"].setdefault(skill, 0)


def growth_threshold(value: int) -> int:
    value = int(value)
    if value <= 20:
        return 6
    if value <= 40:
        return 10
    if value <= 60:
        return 16
    if value <= 80:
        return 24
    return 36


def action_skills(action: str) -> List[str]:
    found: List[str] = []
    for skill, words in ACTION_SKILL_WORDS.items():
        if any(w in action for w in words):
            found.append(skill)
    return found


def _event(code: str, title: str, desc: str, severity: str = "info", diff: Dict[str, int] | None = None, flags: List[str] | None = None) -> SystemEvent:
    return SystemEvent(
        code=code,
        title=title,
        severity=severity,
        description=desc,
        source_system="progression",
        suggested_diff=diff or {},
        new_flags=flags or [title],
        tags=["progression"],
    )


def training_efficiency(state: GameState, skill: str, action: str) -> float:
    eff = 1.0
    body = state.body
    mind = state.mind
    talents = state.talents

    if body.get("体力", 100) < 40:
        eff *= 0.70
    if mind.get("精神压力", 0) > 75:
        eff *= 0.75
    if skill == "dance" and body.get("肌肉疲劳", 0) > 70:
        eff *= 0.65
    if skill == "vocal" and body.get("嗓音状态", 100) < 45:
        eff *= 0.60

    talent_key = {
        "dance": "舞蹈天赋",
        "vocal": "声乐天赋",
        "rap": "RAP天赋",
        "stage": "镜头天赋",
        "variety": "综艺天赋",
        "language": "语言天赋",
        "acting": "演技天赋",
        "creative": "创作天赋",
        "producer": "创作天赋",
    }.get(skill)
    if talent_key:
        talent = int(talents.get(talent_key, 50))
        if talent >= 75:
            eff *= 1.25
        elif talent >= 60:
            eff *= 1.12
        elif talent <= 30:
            eff *= 0.82

    if any(w in action for w in ["老师指导", "老师陪练", "一对一", "专项课", "PD指导"]):
        eff *= 1.20
    if any(w in action for w in ["高强度", "加练", "通宵", "熬夜"]):
        eff *= 1.15
    return max(0.25, min(1.75, eff))


def xp_from_action_and_delta(state: GameState, skill: str, action: str, raw_delta: int) -> int:
    base = 0
    if skill in action_skills(action):
        base += 2
    if raw_delta > 0:
        base += min(5, 2 * abs(int(raw_delta)))
    if any(w in action for w in ["高强度", "加练", "通宵", "熬夜"]):
        base += 2
    if any(w in action for w in ["老师指导", "一对一", "专项课", "PD指导"]):
        base += 1
    if base <= 0:
        base = 1 if raw_delta > 0 else 0
    return max(0, int(round(base * training_efficiency(state, skill, action))))


def convert_growth_diff_to_progression(state: GameState, action: str, diff: Dict[str, int], source: str = "python") -> Tuple[Dict[str, int], List[SystemEvent], Dict[str, int]]:
    """Convert direct career-stat gains into hidden XP and slow level-ups.

    Non-career diffs pass through. Career diffs become XP; only when XP reaches
    the threshold is an actual +1 career diff returned.
    """
    ensure_progression_state(state)
    new_diff: Dict[str, int] = {}
    system_diff: Dict[str, int] = {}
    events: List[SystemEvent] = []
    xp_gain_by_skill: Dict[str, int] = {}
    skills_from_career_diff: set[str] = set()

    # First pass: convert all positive career deltas into XP.
    for key, value in diff.items():
        if not isinstance(value, int):
            continue
        if "." not in key:
            continue
        category, name = key.split(".", 1)
        if category == "职业属性" and name in CAREER_TO_SKILL and value > 0:
            skill = CAREER_TO_SKILL[name]
            skills_from_career_diff.add(skill)
            xp = xp_from_action_and_delta(state, skill, action, value)
            if xp > 0:
                xp_gain_by_skill[skill] = xp_gain_by_skill.get(skill, 0) + xp
            continue
        new_diff[key] = value

    # Extra XP for explicit practice terms only when the base/model diff did not already cover that skill.
    # This prevents a normal one-skill training action from immediately leveling up just because the keyword
    # and the direct career diff were counted twice.
    for skill in action_skills(action):
        if skill not in skills_from_career_diff:
            xp_gain_by_skill[skill] = xp_gain_by_skill.get(skill, 0) + xp_from_action_and_delta(state, skill, action, 0)

    xp_state = state.progression["skill_xp"]
    total_state = state.progression["skill_total_xp"]

    for skill, xp in xp_gain_by_skill.items():
        if xp <= 0:
            continue
        career_name = SKILL_TO_CAREER.get(skill)
        if not career_name:
            continue
        old_xp = int(xp_state.get(skill, 0))
        xp_state[skill] = old_xp + xp
        total_state[skill] = int(total_state.get(skill, 0)) + xp
        # Record practice for decay system.
        if not isinstance(getattr(state, "skill_last_practiced", None), dict):
            state.skill_last_practiced = {}
        state.skill_last_practiced[skill] = int(state.turn)

        current_value = int(state.career.get(career_name, 0))
        threshold = growth_threshold(current_value)
        level_ups = 0
        while xp_state[skill] >= threshold and current_value + level_ups < 100:
            xp_state[skill] -= threshold
            level_ups += 1
            # Recompute threshold after potential level-up. High levels become slower.
            threshold = growth_threshold(current_value + level_ups)

        if level_ups > 0:
            key = f"职业属性.{career_name}"
            system_diff[key] = system_diff.get(key, 0) + level_ups
            events.append(_event(
                "progression_skill_level_up",
                f"能力成长：{career_name} +{level_ups}",
                f"{career_name} 的训练经验累计到了阶段阈值。本回合发生实际成长；平时训练会先积累经验，不再每回合直接涨属性。",
                "info",
                {key: level_ups},
                [f"{career_name}成长+{level_ups}"],
            ))
            state.progression["growth_log"].append({
                "turn": state.turn + 1,
                "skill": skill,
                "career_name": career_name,
                "level_ups": level_ups,
                "source": source,
            })
        else:
            events.append(_event(
                "progression_xp_gain",
                f"训练积累：{career_name} +{xp}xp",
                f"{career_name} 获得 {xp} 点成长经验。当前经验 {xp_state[skill]}/{growth_threshold(current_value)}。",
                "info",
                {},
                [],
            ))

    return new_diff, events, system_diff
