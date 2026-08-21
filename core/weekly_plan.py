from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from core.models import GameState
from core.trainee_life_system import ensure_trainee_life_state


@dataclass(frozen=True)
class WeeklyPlanOption:
    key: str
    label: str
    action_text: str
    category: str
    icon_name: str


TRAINEE_OPTIONS: list[WeeklyPlanOption] = [
    WeeklyPlanOption("dance_extra", "舞蹈加练", "自选安排舞蹈加练", "训练", "dance"),
    WeeklyPlanOption("vocal_extra", "声乐加练", "自选安排声乐加练", "训练", "vocal"),
    WeeklyPlanOption("rap_extra", "RAP/节奏", "自选安排RAP和节奏训练", "训练", "rap"),
    WeeklyPlanOption("creative_demo", "创作 demo", "自选安排作词作曲训练和demo创作", "创作", "comeback"),
    WeeklyPlanOption("peer_social", "同期社交", "自选安排和同期队友谈心社交", "社交", "friendship"),
    WeeklyPlanOption("company_observe", "公司观察", "自选安排观察公司、找老师或经纪人沟通", "公司观察", "contract"),
    WeeklyPlanOption("school_work", "学校/作业", "自选安排学校、作业或考试准备", "学校", "school"),
    WeeklyPlanOption("recovery", "恢复休息", "自选安排休息、睡眠和康复", "恢复", "health"),
]


IDOL_OPTIONS: list[WeeklyPlanOption] = [
    WeeklyPlanOption("comeback_stage", "打歌/彩排", "自选安排打歌舞台和彩排", "公开行程", "stage"),
    WeeklyPlanOption("recording_mv", "录音/MV", "自选安排录音、MV或拍摄", "公开行程", "camera"),
    WeeklyPlanOption("fan_work", "粉丝营业", "自选安排直播、签售或粉丝营业", "粉丝营业", "fans"),
    WeeklyPlanOption("brand_magazine", "品牌/杂志", "自选安排品牌、广告、杂志或商业会议", "商业资源", "market"),
    WeeklyPlanOption("maintenance_training", "维持训练", "自选安排舞蹈声乐维持训练", "训练", "training"),
    WeeklyPlanOption("creative_work", "创作会议", "自选安排demo创作、概念会议或制作讨论", "创作", "comeback"),
    WeeklyPlanOption("variety_interview", "综艺/采访", "自选安排综艺、采访或公开视频", "公开行程", "diary"),
    WeeklyPlanOption("recovery", "恢复治疗", "自选安排休息、睡眠、治疗和康复", "恢复", "health"),
]


def weekly_plan_context(state: GameState) -> dict:
    ensure_trainee_life_state(state)
    tl = state.trainee_life
    return {
        "slot_stage": tl.get("slot_stage", "trainee"),
        "weekly_slots_total": int(tl.get("weekly_slots_total", 7)),
        "mandatory_slots": int(tl.get("mandatory_slots", 4)),
        "free_slots": int(tl.get("free_slots", 3)),
        "fixed_slot_plan": list(tl.get("fixed_slot_plan", [])),
    }


def weekly_plan_options(state: GameState) -> list[WeeklyPlanOption]:
    ensure_trainee_life_state(state)
    return IDOL_OPTIONS if str(state.trainee_life.get("slot_stage")) == "idol" else TRAINEE_OPTIONS


def normalize_weekly_plan_keys(state: GameState, keys: Iterable[str]) -> list[str]:
    allowed = {option.key for option in weekly_plan_options(state)}
    result: list[str] = []
    for key in keys:
        text = str(key or "").strip()
        if text in allowed and text not in result:
            result.append(text)
    limit = weekly_plan_context(state)["free_slots"]
    return result[:limit]


def weekly_plan_selected_options(state: GameState, keys: Iterable[str]) -> list[WeeklyPlanOption]:
    selected = set(normalize_weekly_plan_keys(state, keys))
    return [option for option in weekly_plan_options(state) if option.key in selected]


def weekly_plan_summary(state: GameState, keys: Iterable[str]) -> str:
    context = weekly_plan_context(state)
    selected = weekly_plan_selected_options(state, keys)
    fixed = "、".join(str(item) for item in context["fixed_slot_plan"])
    free = "、".join(option.label for option in selected) if selected else "未选择自选安排"
    return (
        f"本周七格安排：固定{context['mandatory_slots']}格（{fixed}）；"
        f"自选{len(selected)}/{context['free_slots']}格（{free}）。"
    )


def compose_action_with_weekly_plan(action: str, state: GameState, keys: Iterable[str]) -> str:
    selected = weekly_plan_selected_options(state, keys)
    base = str(action or "").strip()
    if not selected:
        return base
    plan_text = "；".join(option.action_text for option in selected)
    return f"{base}\n\n【本周安排】{weekly_plan_summary(state, keys)} 具体自选：{plan_text}。"
