from __future__ import annotations

from typing import Dict, List, Tuple
from core.models import GameState, SystemEvent
from core.progression_system import SKILL_TO_CAREER, action_skills


DEFAULT_PROFICIENCY = {
    "dance": 70,
    "vocal": 70,
    "rap": 65,
    "stage": 68,
    "variety": 60,
    "language": 60,
    "acting": 55,
    "creative": 60,
    "producer": 50,
}

# Idol work can maintain related skills even when the player did not select "training".
WORK_MAINTENANCE_WORDS = {
    "dance": ["彩排", "打歌", "舞台", "巡演", "编舞", "直拍"],
    "vocal": ["录音", "演唱会", "live", "Live", "打歌", "唱"],
    "stage": ["舞台", "打歌", "彩排", "直拍", "巡演"],
    "variety": ["综艺", "采访", "直播", "MC", "mc"],
    "language": ["采访", "海外", "韩语", "英语", "日语"],
    "creative": ["作词", "作曲", "demo", "Demo", "编曲", "概念会议"],
}


def ensure_skill_decay_state(state: GameState) -> None:
    if not isinstance(getattr(state, "skill_proficiency", None), dict):
        state.skill_proficiency = {}
    if not isinstance(getattr(state, "skill_last_practiced", None), dict):
        state.skill_last_practiced = {}
    if not isinstance(getattr(state, "skill_decay_log", None), list):
        state.skill_decay_log = []
    for skill, default in DEFAULT_PROFICIENCY.items():
        state.skill_proficiency.setdefault(skill, default)
        state.skill_last_practiced.setdefault(skill, int(state.turn))


def _event(code: str, title: str, desc: str, severity: str = "info", diff: Dict[str, int] | None = None, flags: List[str] | None = None) -> SystemEvent:
    return SystemEvent(
        code=code,
        title=title,
        severity=severity,
        description=desc,
        source_system="skill_decay",
        suggested_diff=diff or {},
        new_flags=flags or [title],
        tags=["skill_decay"],
    )


def maintained_skills_from_action(action: str) -> List[str]:
    found = set(action_skills(action))
    for skill, words in WORK_MAINTENANCE_WORDS.items():
        if any(w in action for w in words):
            found.add(skill)
    return list(found)


def evaluate_skill_decay_system(state: GameState, action: str) -> Tuple[List[SystemEvent], Dict[str, int]]:
    ensure_skill_decay_state(state)
    events: List[SystemEvent] = []
    diff: Dict[str, int] = {}

    maintained = set(maintained_skills_from_action(action))
    for skill in maintained:
        state.skill_last_practiced[skill] = int(state.turn)
        old = int(state.skill_proficiency.get(skill, DEFAULT_PROFICIENCY.get(skill, 60)))
        state.skill_proficiency[skill] = min(100, old + 2)

    # Decay is assessed in turn counts, not days, because one player choice is the smallest simulation step.
    for skill, career_name in SKILL_TO_CAREER.items():
        last = int(state.skill_last_practiced.get(skill, int(state.turn)))
        gap = int(state.turn) - last
        if gap < 4:
            continue

        old_prof = int(state.skill_proficiency.get(skill, DEFAULT_PROFICIENCY.get(skill, 60)))
        if gap >= 12:
            loss = 6
        elif gap >= 8:
            loss = 4
        else:
            loss = 2

        new_prof = max(0, old_prof - loss)
        if new_prof != old_prof:
            state.skill_proficiency[skill] = new_prof
            events.append(_event(
                "skill_proficiency_decay",
                f"手感下滑：{career_name}",
                f"{career_name} 已有 {gap} 回合没有得到训练或工作维持，先表现为手感和状态下滑。",
                "warning" if gap >= 8 else "info",
                {},
                [f"{career_name}手感下滑"],
            ))
            state.skill_decay_log.append({"turn": state.turn + 1, "skill": skill, "gap": gap, "proficiency": new_prof})

        # Actual long-term stat decay is rare and only hits weaker skills.
        if gap >= 12 and int(state.career.get(career_name, 0)) < 60:
            key = f"职业属性.{career_name}"
            diff[key] = diff.get(key, 0) - 1
            events.append(_event(
                "skill_long_term_decay",
                f"长期退化：{career_name} -1",
                f"{career_name} 长期缺少维持训练，且基础值尚未稳定，出现了实际能力退化。",
                "warning",
                {key: -1},
                [f"{career_name}长期退化"],
            ))
            # Reset last practiced marker to avoid losing one point every future turn.
            state.skill_last_practiced[skill] = int(state.turn)

    return events, diff
