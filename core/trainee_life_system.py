from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from core.models import GameState, SystemEvent


def _event(
    code: str,
    title: str,
    desc: str,
    severity: str = "info",
    diff: Dict[str, int] | None = None,
    flags: List[str] | None = None,
    source_system: str = "trainee_life",
) -> SystemEvent:
    return SystemEvent(
        code=code,
        title=title,
        severity=severity,
        description=desc,
        source_system=source_system,
        suggested_diff=diff or {},
        new_flags=flags or [title],
        tags=[source_system],
    )


def ensure_trainee_life_state(state: GameState) -> None:
    if not isinstance(getattr(state, "trainee_life", None), dict):
        state.trainee_life = {}
    tl = state.trainee_life
    tl.setdefault("weekly_slots_total", 7)
    if state.is_trainee_stage():
        tl["slot_stage"] = "trainee"
        tl["mandatory_slots"] = 4
        tl["free_slots"] = 3
        tl["fixed_slot_plan"] = ["舞蹈课", "声乐课", "体能课", "形象/语言/团队课"]
    else:
        tl["slot_stage"] = "idol"
        tl["mandatory_slots"] = 2
        tl["free_slots"] = 5
        tl["fixed_slot_plan"] = ["职业状态维持", "公司/团队基础行程"]
    tl.setdefault("last_slot_usage", {})
    tl.setdefault("overbooked_weeks", 0)
    tl.setdefault("idol_overbooked_weeks", 0)
    tl.setdefault("practice_room_access", 50)
    tl.setdefault("dorm_friction", 20)
    tl.setdefault("bullying_pressure", 15)
    tl.setdefault("hidden_conflict", 0)
    tl.setdefault("protected_someone_memory", 0)
    tl.setdefault("recent_life_notes", [])


def _slot_usage(action: str) -> Dict[str, int]:
    usage = {"训练": 0, "恢复": 0, "社交": 0, "学校": 0, "创作": 0, "公司观察": 0, "公开行程": 0, "粉丝营业": 0, "商业资源": 0}
    if any(w in action for w in ["练", "训练", "舞蹈", "声乐", "RAP", "rap", "加练", "考核"]):
        usage["训练"] += 2 if any(w in action for w in ["加练", "通宵", "硬撑", "高强度"]) else 1
    if any(w in action for w in ["休息", "睡", "康复", "医院", "治疗", "心理咨询"]):
        usage["恢复"] += 1
    if any(w in action for w in ["队友", "同期", "聊天", "谈心", "陪", "宿舍", "社交"]):
        usage["社交"] += 1
    if any(w in action for w in ["学校", "作业", "考试", "补课", "请假"]):
        usage["学校"] += 1
    if any(w in action for w in ["作词", "作曲", "demo", "编舞", "创作"]):
        usage["创作"] += 1
    if any(w in action for w in ["观察公司", "公司会议", "经纪人", "主管", "老师", "PD"]):
        usage["公司观察"] += 1
    if any(w in action for w in ["打歌", "彩排", "录音", "MV", "拍摄", "采访", "综艺", "巡演", "舞台", "公开视频", "直播"]):
        usage["公开行程"] += 2 if any(w in action for w in ["打歌", "巡演", "MV", "拍摄"]) else 1
    if any(w in action for w in ["粉丝", "签售", "Bubble", "Weverse", "营业", "站姐", "直播"]):
        usage["粉丝营业"] += 1
    if any(w in action for w in ["品牌", "代言", "杂志", "广告", "商业", "封面", "奢侈品"]):
        usage["商业资源"] += 1
    return {k: v for k, v in usage.items() if v > 0}


def _explicit_weekly_plan_slots(action: str) -> tuple[int | None, str, str]:
    marker = "【本周安排】"
    if marker not in action:
        return None, action, ""
    before, after = action.split(marker, 1)
    match = re.search(r"自选\s*(\d+)\s*/\s*(\d+)\s*格", after)
    if not match:
        return None, before, after
    return int(match.group(1)), before, after


def evaluate_trainee_life_system(state: GameState, action: str) -> Tuple[List[SystemEvent], Dict[str, int]]:
    ensure_trainee_life_state(state)
    events: List[SystemEvent] = []
    diff: Dict[str, int] = {}

    tl = state.trainee_life
    explicit_slots, base_action, plan_action = _explicit_weekly_plan_slots(action)
    usage = _slot_usage(action)
    tl["last_slot_usage"] = usage
    if explicit_slots is None:
        used_slots = sum(usage.values())
    else:
        # UI-selected weekly plans count each selected free slot exactly once.
        # Extra prose outside the plan can still consume additional slots.
        used_slots = explicit_slots + sum(_slot_usage(base_action).values())
    free_slots = int(tl.get("free_slots", 3))
    notes: List[str] = list(tl.get("recent_life_notes", []))

    if used_slots > free_slots:
        if state.is_trainee_stage():
            tl["overbooked_weeks"] = int(tl.get("overbooked_weeks", 0)) + 1
            events.append(_event(
                "trainee_week_overbooked",
                "练习生周时间格超载",
                "本周自由时间格被训练、社交、学校、创作或公司观察挤满。系统会把收益和代价一起结算，而不是允许所有目标同时满收益。",
                "warning",
                {"身体状态.体力": -4, "身体状态.睡眠质量": -3, "身体状态.伤病风险": 2, "心理状态.精神压力": 2},
                ["本周时间格超载"],
                "trainee_life",
            ))
        else:
            tl["idol_overbooked_weeks"] = int(tl.get("idol_overbooked_weeks", 0)) + 1
            events.append(_event(
                "idol_week_overbooked",
                "出道后周时间格超载",
                "出道后每回合仍是七格安排，但固定职业维护和团队基础行程占 2 格，自选只有 5 格。公开行程、粉丝营业、商业、创作、训练和恢复不能全部满收益。",
                "warning",
                {"身体状态.体力": -4, "身体状态.睡眠质量": -2, "心理状态.职业倦怠": 3, "风险.私生风险": 1},
                ["出道后时间格超载"],
                "time_slots",
            ))
        notes.append(f"自由时间格 {free_slots}，本回合使用 {used_slots}。")

    if not state.is_trainee_stage():
        if used_slots <= free_slots and any(w in action for w in ["打歌", "品牌", "杂志", "训练", "休息", "创作", "直播"]):
            notes.append(f"出道后固定 2 格，自选 5 格；本回合自选使用 {used_slots} 格。")
        tl["recent_life_notes"] = notes[-8:]
        for ev in events:
            for key, value in ev.suggested_diff.items():
                diff[key] = diff.get(key, 0) + value
        return events, diff

    competition = int(state.team.get("队内竞争度", 35))
    warmth = int(state.team.get("真实关系温度", 45))
    dorm_safety = int(state.team.get("宿舍安全感", 55))
    resource_pool = int(state.company.get("资源池", 50))
    launch_pressure = int(state.company.get("出道窗口压力", 45))
    pressure = (
        0.30 * competition
        + 0.22 * launch_pressure
        + 0.18 * (100 - resource_pool)
        + 0.16 * (100 - warmth)
        + 0.14 * (100 - dorm_safety)
    )
    tl["bullying_pressure"] = max(0, min(100, int(round(pressure))))

    if tl["bullying_pressure"] >= 68 and any(w in action for w in ["宿舍", "分组", "练习室", "队友", "同期", "沉默", "忍", "杂事", "排挤", "霸凌", "冷处理"]):
        tl["hidden_conflict"] = min(100, int(tl.get("hidden_conflict", 0)) + 6)
        events.append(_event(
            "trainee_bullying_pressure_high",
            "排挤与冷处理风险上升",
            "竞争、资源不足、出道压力和宿舍密闭环境正在推高冷处理风险。它不一定是单一恶意，但会留下长期关系痕迹。",
            "warning",
            {"风险.霸凌排挤风险": 4, "团队关系.真实关系温度": -2, "心理状态.孤独感": 3},
            ["练习生排挤风险上升"],
        ))

    if any(w in action for w in ["求助", "报告", "找经纪人", "找老师", "保留证据"]):
        tl["hidden_conflict"] = max(0, int(tl.get("hidden_conflict", 0)) - 4)
        events.append(_event(
            "trainee_conflict_help_seeking",
            "练习生冲突进入求助路径",
            "求助会让冲突变得可见。结果取决于可信 NPC、证据、公司态度和既有关系，而不是自动解决。",
            "info",
            {"公司与合约.危机关注度": 1, "心理状态.精神压力": -1},
            ["练习生冲突求助"],
        ))

    if any(w in action for w in ["保护", "替她解释", "帮她作证", "挡下", "陪她去找"]):
        tl["protected_someone_memory"] = min(100, int(tl.get("protected_someone_memory", 0)) + 8)
        events.append(_event(
            "trainee_protected_someone",
            "关键记忆：保护被排挤的人",
            "这次保护会进入长期记忆。未来危机里，对方可能提供证词、照顾或反向压力。",
            "info",
            {"团队关系.队内信任度": 2, "团队关系.真实关系温度": 2},
            ["保护被排挤者记忆"],
        ))

    tl["recent_life_notes"] = notes[-8:]
    for ev in events:
        for key, value in ev.suggested_diff.items():
            diff[key] = diff.get(key, 0) + value
    return events, diff
