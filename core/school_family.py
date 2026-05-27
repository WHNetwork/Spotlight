from __future__ import annotations

from typing import Any, Dict, List, Tuple
from core.models import GameState, SystemEvent


def default_school_context(age_context: Dict[str, Any], character: Dict[str, Any]) -> Dict[str, Any]:
    age = age_context.get("age")
    is_minor = bool(age_context.get("is_minor", False))
    enrolled = bool(is_minor or (isinstance(age, int) and age <= 19))
    school_type = "普通学校"
    if "艺高" in str(character.get("学校", "")) or "艺术" in str(character.get("学校", "")):
        school_type = "艺高"
    return {
        "enrolled": enrolled,
        "school_type": school_type if enrolled else "非在学",
        "attendance_pressure": 35 if enrolled else 0,
        "exam_pressure": 25 if enrolled else 0,
        "homework_pressure": 25 if enrolled else 0,
        "classmate_relationship": 45 if enrolled else 0,
        "leave_risk": 10 if enrolled else 0,
    }


def default_family_context(age_context: Dict[str, Any], character: Dict[str, Any], social_context: Dict[str, Any]) -> Dict[str, Any]:
    family_text = str(character.get("家庭状况", "") or "")
    supportive = any(w in family_text for w in ["支持", "理解", "鼓励"])
    oppose = any(w in family_text for w in ["反对", "不同意", "吵", "控制", "不理解"])
    economic = any(w in family_text for w in ["困难", "欠债", "压力", "省钱"])

    emotional = 65 if supportive else 45
    understanding = 60 if supportive else 35
    control = 55 if oppose else 30
    conflict = 45 if oppose else 20
    financial = 35 if economic else 60
    if age_context.get("is_minor"):
        control += 10
    return {
        "emotional_support": max(0, min(100, emotional)),
        "financial_support": max(0, min(100, financial)),
        "career_understanding": max(0, min(100, understanding)),
        "control_level": max(0, min(100, control)),
        "conflict_level": max(0, min(100, conflict)),
        "distance_from_home": social_context.get("family_distance", 30),
        "guardian_trust_company": 45 if age_context.get("is_minor") else 55,
        "last_contact_days": 7,
    }


def _event(code: str, title: str, desc: str, severity: str = "info", diff: Dict[str, int] | None = None, flags: List[str] | None = None) -> SystemEvent:
    return SystemEvent(
        code=code,
        title=title,
        severity=severity,
        description=desc,
        source_system="school_family",
        suggested_diff=diff or {},
        new_flags=flags or [title],
        tags=["school_family"],
    )


def _merge_event_diff(diff: Dict[str, int], event: SystemEvent) -> None:
    for key, value in event.suggested_diff.items():
        diff[key] = diff.get(key, 0) + value


def evaluate_school_family(state: GameState, action: str) -> Tuple[List[SystemEvent], Dict[str, int]]:
    events: List[SystemEvent] = []
    diff: Dict[str, int] = {}

    school = state.school
    family = state.family
    time_days = int(state.time.get("turn_duration_days", 0))

    if school.get("enrolled"):
        if time_days >= 7 and any(w in action for w in ["高强度", "加练", "每天练", "熬夜", "继续练"]):
            school["attendance_pressure"] = min(100, int(school.get("attendance_pressure", 0)) + 5)
            school["homework_pressure"] = min(100, int(school.get("homework_pressure", 0)) + 4)
            events.append(_event(
                "school_training_conflict",
                "学校与训练冲突",
                "训练占掉了一部分学校和作业时间。未成年练习生的生活不是只有练习室，学校压力也会回流。",
                "warning",
                {"心理状态.精神压力": 2},
                ["学校与训练冲突"],
            ))

        if any(w in action for w in ["上学", "考试", "作业", "补课", "请假"]):
            school["attendance_pressure"] = max(0, int(school.get("attendance_pressure", 0)) - 4)
            events.append(_event(
                "school_attention",
                "学校事务处理",
                "你把学校事务纳入安排。短期训练时间减少，但长期会降低家长和学校压力。",
                "info",
                {"心理状态.精神压力": -1, "公司与合约.公司满意度": -1},
                ["处理学校事务"],
            ))

        if school.get("attendance_pressure", 0) > 70:
            events.append(_event(
                "school_attendance_warning",
                "出勤压力过高",
                "学校出勤压力已经很高。老师、家长或公司可能要求你调整训练安排。",
                "warning",
                {"心理状态.精神压力": 2, "公司与合约.危机关注度": 1},
                ["出勤压力过高"],
            ))

    # 家庭联系与冲突
    family["last_contact_days"] = int(family.get("last_contact_days", 7)) + max(1, time_days)
    if any(w in action for w in ["父母", "妈妈", "爸爸", "家里", "打电话", "视频"]):
        family["last_contact_days"] = 0
        if family.get("career_understanding", 0) < 40:
            family["conflict_level"] = min(100, int(family.get("conflict_level", 0)) + 3)
            events.append(_event(
                "family_misunderstanding",
                "家庭沟通：理解落差",
                "家人关心你，但不一定理解练习生生活。关心和控制有时会混在一起。",
                "warning",
                {"心理状态.精神压力": 2, "心理状态.孤独感": 1},
                ["家庭理解落差"],
            ))
        else:
            events.append(_event(
                "family_support_contact",
                "家庭联系：获得支持",
                "你和家里联系了一次。支持不能解决所有问题，但能让你知道自己不是完全孤身一人。",
                "info",
                {"心理状态.孤独感": -3, "心理状态.心情": 2},
                ["联系家人获得支持"],
            ))

    if family.get("last_contact_days", 0) > 30 and family.get("emotional_support", 0) >= 50:
        events.append(_event(
            "family_contact_overdue",
            "很久没有联系家里",
            "你已经很久没认真和家里说话。不是每一次想家都会爆发，但它会慢慢增加孤独感。",
            "info",
            {"心理状态.孤独感": 2},
            ["长时间未联系家人"],
        ))

    if family.get("conflict_level", 0) > 70:
        events.append(_event(
            "family_conflict_high",
            "家庭冲突升高",
            "家庭冲突已经开始影响你的训练稳定性。继续回避会让它转成长期压力。",
            "warning",
            {"心理状态.精神压力": 3, "心理状态.自我认同": -1},
            ["家庭冲突升高"],
        ))

    for _ev in events:
        _merge_event_diff(diff, _ev)
    return events, diff
