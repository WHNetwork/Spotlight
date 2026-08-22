from __future__ import annotations

from datetime import date
from typing import List

from core.models import (
    DayState,
    EducationStatus,
    SlotKind,
    SlotStatus,
    TimeSlotState,
    TimeState,
)


class EducationStatusUnspecifiedError(RuntimeError):
    """education_status 为 UNSPECIFIED 时无法生成完整基础日程。

    不允许把 UNSPECIFIED 默认当作 ENROLLED 之类的猜测；
    角色是否继续上学由玩家在创建角色时决定。
    """


def build_base_day_slots(day: date, education_status: EducationStatus) -> List[TimeSlotState]:
    """根据真实星期和角色是否在学，构造当天基础 8 Slot 模板。

    周末（周六 / 周日，真实日期推导）：
        FREE ×6 + REST ×2（周末没有普通固定公司课程）

    工作日 + ENROLLED：
        SCHOOL ×2 + COMPANY ×2 + FREE ×2 + REST ×2

    工作日 + NOT_ENROLLED：
        COMPANY ×3 + FREE ×3 + REST ×2

    工作日 + UNSPECIFIED：抛 EducationStatusUnspecifiedError，不擅自假定。

    只生成结构模板：COMPANY / FREE 的具体内容（company_course / free_action）
    由后续模块分别填入；不涉及公司课程内容、玩家行动、数值效果或特殊事件。
    """
    if day.weekday() >= 5:
        template = [SlotKind.FREE] * 6 + [SlotKind.REST] * 2
    elif education_status == EducationStatus.ENROLLED:
        template = [
            SlotKind.SCHOOL, SlotKind.SCHOOL,
            SlotKind.COMPANY, SlotKind.COMPANY,
            SlotKind.FREE, SlotKind.FREE,
            SlotKind.REST, SlotKind.REST,
        ]
    elif education_status == EducationStatus.NOT_ENROLLED:
        template = [SlotKind.COMPANY] * 3 + [SlotKind.FREE] * 3 + [SlotKind.REST] * 2
    else:
        raise EducationStatusUnspecifiedError(
            f"education_status={education_status!r}：无法生成基础日程，请先由玩家明确是否在学。"
        )

    return [
        TimeSlotState(index=index, kind=kind, status=SlotStatus.PENDING)
        for index, kind in enumerate(template)
    ]


def build_base_day(time_state: TimeState, education_status: EducationStatus) -> DayState:
    """便捷入口：读取 TimeState.current_date（唯一权威日期来源）生成当日基础日程。"""
    return DayState(slots=build_base_day_slots(time_state.current_date, education_status))
