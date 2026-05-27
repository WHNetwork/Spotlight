from __future__ import annotations

from typing import Any, Dict, List, Tuple
from core.models import GameState, RouteInfo, SystemEvent


STAGE_PROFILES: Dict[str, Dict[str, int]] = {
    "trainee": {
        "训练": 62,
        "学校生活": 16,
        "公司考察": 10,
        "公开曝光": 2,
        "恢复休息": 10,
    },
    "debut_prep": {
        "编舞声乐录音": 42,
        "造型拍摄会议": 20,
        "团队磨合": 14,
        "公司评估": 12,
        "恢复休息": 12,
    },
    "idol_comeback": {
        "录音MV拍摄": 24,
        "打歌舞台彩排": 32,
        "采访综艺直播": 16,
        "粉丝营业": 10,
        "训练维持": 10,
        "恢复休息": 8,
    },
    "idol_offseason": {
        "个人资源": 24,
        "维持训练": 22,
        "创作语言演技": 18,
        "粉丝营业": 8,
        "恢复休息": 20,
        "其他工作": 8,
    },
    "tour": {
        "演出移动": 50,
        "舞台维护训练": 15,
        "恢复治疗": 18,
        "粉丝互动": 10,
        "其他工作": 7,
    },
}


def ensure_schedule_state(state: GameState) -> None:
    if not isinstance(getattr(state, "schedule_profile", None), dict):
        state.schedule_profile = {}
    sp = state.schedule_profile
    sp.setdefault("stage_mode", detect_schedule_mode(state))
    sp.setdefault("current_profile", STAGE_PROFILES.get(sp["stage_mode"], STAGE_PROFILES["trainee"]).copy())
    sp.setdefault("last_action_type", "none")
    sp.setdefault("practice_quota_need", 0)
    sp.setdefault("workload_pressure", 0)
    sp.setdefault("recent_schedule_notes", [])


def _event(code: str, title: str, desc: str, severity: str = "info", diff: Dict[str, int] | None = None, flags: List[str] | None = None) -> SystemEvent:
    return SystemEvent(
        code=code,
        title=title,
        severity=severity,
        description=desc,
        source_system="schedule",
        suggested_diff=diff or {},
        new_flags=flags or [title],
        tags=["schedule"],
    )


def _merge_event_diff(diff: Dict[str, int], event: SystemEvent) -> None:
    for key, value in event.suggested_diff.items():
        diff[key] = diff.get(key, 0) + value


def detect_schedule_mode(state: GameState) -> str:
    text = f"{state.current_stage} {state.current_mainline} {state.current_schedule}".lower()
    if "巡演" in text or "tour" in text:
        return "tour"
    if "出道准备" in text or "出道组" in text or "debut" in text:
        return "debut_prep"
    if any(w in text for w in ["回归", "打歌", "comeback", "mv", "录音"]):
        return "idol_comeback"
    if any(w in text for w in ["爱豆", "出道", "续约", "solo", "团体活动", "空窗"]):
        return "idol_offseason"
    return "trainee"


def action_type(action: str) -> str:
    text = action.lower()
    if any(w in action for w in ["练舞", "舞蹈", "声乐", "练歌", "rap", "RAP", "说唱", "训练", "加练", "编舞课", "声乐课"]):
        return "training"
    if any(w in action for w in ["回归", "打歌", "彩排", "录音", "MV", "拍摄", "综艺", "采访", "直播", "签售", "巡演", "舞台"]):
        return "idol_work"
    if any(w in action for w in ["学校", "上学", "考试", "作业", "补课", "请假"]):
        return "school"
    if any(w in action for w in ["休息", "睡", "康复", "医院", "治疗", "放松"]):
        return "recovery"
    if any(w in action for w in ["公司", "经纪人", "老师", "PD", "会议", "考核", "评估"]):
        return "company"
    return "life"


def evaluate_schedule_system(state: GameState, action: str, route_info: RouteInfo | None = None) -> Tuple[List[SystemEvent], Dict[str, int]]:
    ensure_schedule_state(state)
    events: List[SystemEvent] = []
    diff: Dict[str, int] = {}

    mode = detect_schedule_mode(state)
    old_mode = str(state.schedule_profile.get("stage_mode", ""))
    state.schedule_profile["stage_mode"] = mode
    state.schedule_profile["current_profile"] = STAGE_PROFILES.get(mode, STAGE_PROFILES["trainee"]).copy()

    act_type = action_type(action)
    state.schedule_profile["last_action_type"] = act_type

    notes: List[str] = list(state.schedule_profile.get("recent_schedule_notes", []))

    if old_mode and old_mode != mode:
        events.append(_event(
            "schedule_mode_changed",
            "日程结构调整",
            f"当前阶段从 {old_mode} 切换为 {mode}。训练、工作、恢复和公开曝光的时间占比随之变化。",
            "info",
            {},
            [f"日程结构：{mode}"],
        ))

    if mode == "trainee":
        if act_type == "training":
            state.schedule_profile["practice_quota_need"] = max(0, int(state.schedule_profile.get("practice_quota_need", 0)) - 8)
            notes.append("练习生阶段以训练和考核准备为主。")
        elif act_type == "idol_work":
            events.append(_event(
                "schedule_trainee_work_mismatch",
                "阶段日程不匹配",
                "练习生阶段公开工作和镜头资源很有限。该行动会被理解为争取展示机会，而不是正式爱豆工作。",
                "warning",
                {"公司与合约.公司信任度": -1, "心理状态.精神压力": 1},
                ["练习生阶段公开工作受限"],
            ))
        elif act_type == "recovery":
            state.schedule_profile["practice_quota_need"] = min(100, int(state.schedule_profile.get("practice_quota_need", 0)) + 3)

    else:
        if act_type == "idol_work":
            state.schedule_profile["workload_pressure"] = min(100, int(state.schedule_profile.get("workload_pressure", 0)) + 5)
            state.schedule_profile["practice_quota_need"] = min(100, int(state.schedule_profile.get("practice_quota_need", 0)) + 4)
            events.append(_event(
                "schedule_idol_workload",
                "爱豆行程负荷",
                "出道后工作本身会占据大量时间。训练从主日程变成维持职业状态的基础项。",
                "info",
                {"身体状态.体力": -2, "心理状态.职业倦怠": 1},
                ["爱豆工作负荷上升"],
            ))
        elif act_type == "training":
            state.schedule_profile["practice_quota_need"] = max(0, int(state.schedule_profile.get("practice_quota_need", 0)) - 10)
            events.append(_event(
                "schedule_idol_training_maintenance",
                "职业状态维持训练",
                "出道后训练不再是唯一主线，但长期缺席训练会影响手感、声带状态和舞台稳定性。",
                "info",
                {"身体状态.肌肉疲劳": 1},
                ["爱豆维持训练"],
            ))
        elif act_type == "recovery":
            state.schedule_profile["workload_pressure"] = max(0, int(state.schedule_profile.get("workload_pressure", 0)) - 6)

        if int(state.schedule_profile.get("practice_quota_need", 0)) >= 45:
            events.append(_event(
                "schedule_practice_quota_high",
                "维持训练不足",
                "近期工作行程挤占了训练时间。继续忽视维持训练会触发手感下滑。",
                "warning",
                {"心理状态.精神压力": 1},
                ["维持训练不足"],
            ))

    state.schedule_profile["recent_schedule_notes"] = notes[-8:]

    for ev in events:
        _merge_event_diff(diff, ev)
    return events, diff
