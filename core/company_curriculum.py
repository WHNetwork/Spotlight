from __future__ import annotations

import hashlib
from datetime import date, timedelta
from typing import Dict, List, Optional

from core.models import (
    CompanyCourse,
    CompanyState,
    DayState,
    EducationStatus,
    SlotKind,
    TimeSlotState,
    TrainingStyle,
    TrainingWeights,
)


# ---------------------------------------------------------------------------
# 培养风格 → 官方基础权重模板
# ---------------------------------------------------------------------------

TRAINING_WEIGHTS_BY_STYLE: Dict[TrainingStyle, TrainingWeights] = {
    TrainingStyle.BALANCED: TrainingWeights(
        dance=0.22, vocal=0.22, rap=0.12, stage=0.16, camera=0.10, language=0.10, fitness=0.08,
    ),
    TrainingStyle.PERFORMANCE: TrainingWeights(
        dance=0.30, vocal=0.16, rap=0.10, stage=0.22, camera=0.08, language=0.06, fitness=0.08,
    ),
    TrainingStyle.VOCAL: TrainingWeights(
        dance=0.16, vocal=0.32, rap=0.08, stage=0.18, camera=0.08, language=0.10, fitness=0.08,
    ),
    TrainingStyle.HIPHOP: TrainingWeights(
        dance=0.22, vocal=0.12, rap=0.28, stage=0.20, camera=0.06, language=0.06, fitness=0.06,
    ),
    TrainingStyle.GLOBAL: TrainingWeights(
        dance=0.18, vocal=0.18, rap=0.08, stage=0.16, camera=0.18, language=0.16, fitness=0.06,
    ),
}

_COURSES: List[CompanyCourse] = [
    CompanyCourse.DANCE, CompanyCourse.VOCAL, CompanyCourse.RAP,
    CompanyCourse.STAGE, CompanyCourse.CAMERA, CompanyCourse.LANGUAGE,
    CompanyCourse.FITNESS,
]

_COURSE_FIELD: Dict[CompanyCourse, str] = {
    CompanyCourse.DANCE: "dance",
    CompanyCourse.VOCAL: "vocal",
    CompanyCourse.RAP: "rap",
    CompanyCourse.STAGE: "stage",
    CompanyCourse.CAMERA: "camera",
    CompanyCourse.LANGUAGE: "language",
    CompanyCourse.FITNESS: "fitness",
}

# 每周核心课程最低保障：DANCE ×2 + VOCAL ×2 + STAGE ×1（共 5 格）。
_MINIMUM_GUARANTEED: Dict[CompanyCourse, int] = {
    CompanyCourse.DANCE: 2,
    CompanyCourse.VOCAL: 2,
    CompanyCourse.STAGE: 1,
}

_MAX_PER_COURSE_PER_WEEK = 5


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------


def week_start_of(current_date: date) -> date:
    """当前日期所在自然周的周一（Monday → Sunday）。"""
    return current_date - timedelta(days=current_date.weekday())


def company_slots_per_day(education_status: EducationStatus) -> Optional[int]:
    """工作日每天 COMPANY Slot 数量：在学 2 / 非在学 3 / 未指定 None。"""
    if education_status == EducationStatus.ENROLLED:
        return 2
    if education_status == EducationStatus.NOT_ENROLLED:
        return 3
    return None


def _week_seed(rng_seed: int, week_start: date) -> int:
    """稳定周种子：同一存档同一自然周固定，下一周变化。"""
    namespace = f"weekly-curriculum:{rng_seed}:{week_start.isoformat()}"
    return int(hashlib.sha256(namespace.encode("utf-8")).hexdigest()[:8], 16)


def _rotated_order(seed: int) -> List[CompanyCourse]:
    """按稳定 seed 轮转的课程顺序，用于平局裁决，保证每周排列不同。"""
    offset = seed % len(_COURSES)
    return _COURSES[offset:] + _COURSES[:offset]


# ---------------------------------------------------------------------------
# 每周课程数量（纯派生、确定性）
# ---------------------------------------------------------------------------


def weekly_course_counts(
    company: CompanyState,
    education_status: EducationStatus,
    rng_seed: int,
    week_start: date,
) -> Dict[CompanyCourse, int]:
    """生成整周（周一～周五）的公司课程数量。

    步骤：先锁定最低保障 DANCE×2 + VOCAL×2 + STAGE×1，
    剩余 Slot 按 training_weights 使用 Largest Remainder 整数配额分配，
    最后守住“单课程每周最多 5 节”的上限。
    """
    slots_per_day = company_slots_per_day(education_status)
    if slots_per_day is None:
        raise ValueError("education_status 未确定（UNSPECIFIED）：无法生成每周课程，不猜测在学状态。")
    if company.training_style is None or company.training_weights is None:
        raise ValueError("公司培养画像尚未初始化（training_style / training_weights 为 None），无法生成课程。")

    weights = company.training_weights
    total_weight = sum(getattr(weights, _COURSE_FIELD[c]) for c in _COURSES)
    if abs(total_weight - 1.0) > 1e-6:
        raise ValueError(f"training_weights 总和必须为 1.0（当前 {total_weight}）。")

    seed = _week_seed(rng_seed, week_start)
    total = slots_per_day * 5
    counts: Dict[CompanyCourse, int] = dict(_MINIMUM_GUARANTEED)
    for course in _COURSES:
        counts.setdefault(course, 0)

    remaining = total - 5
    if remaining > 0:
        quotas = {c: remaining * getattr(weights, _COURSE_FIELD[c]) for c in _COURSES}
        floor = {c: int(quotas[c]) for c in _COURSES}
        used = sum(floor.values())
        order = _rotated_order(seed)
        ranked = sorted(
            _COURSES,
            key=lambda c: (-(quotas[c] - floor[c]), order.index(c)),
        )
        for course in ranked[: remaining - used]:
            floor[course] += 1
        for course in _COURSES:
            counts[course] += floor[course]

    _enforce_per_course_cap(counts, weights, seed)
    return counts


def _enforce_per_course_cap(
    counts: Dict[CompanyCourse, int],
    weights: TrainingWeights,
    seed: int,
) -> None:
    """单课程每周最多 5 节：超过部分按剩余权重优先顺序重分配给未满课程。"""
    order = _rotated_order(seed)

    def priority(course: CompanyCourse) -> tuple[float, int]:
        return (getattr(weights, _COURSE_FIELD[course]), -order.index(course))

    for _ in range(64):
        over = [c for c in _COURSES if counts[c] > _MAX_PER_COURSE_PER_WEEK]
        if not over:
            return
        over.sort(key=priority, reverse=True)
        under = [c for c in _COURSES if counts[c] < _MAX_PER_COURSE_PER_WEEK]
        under.sort(key=priority, reverse=True)
        if not under:
            raise ValueError("课程总数超出每周容量，无法将超额课程重新分配。")
        source = over[0]
        target = under[0]
        move = min(counts[source] - _MAX_PER_COURSE_PER_WEEK, _MAX_PER_COURSE_PER_WEEK - counts[target])
        counts[source] -= move
        counts[target] += move
    raise ValueError("课程数量超出每周容量，无法在限制次数内完成重新分配。")


# ---------------------------------------------------------------------------
# 整周课程编排：分散到周一～周五
# ---------------------------------------------------------------------------


def weekly_curriculum(
    company: CompanyState,
    education_status: EducationStatus,
    rng_seed: int,
    week_start: date,
) -> Dict[date, List[CompanyCourse]]:
    """整周课程表：周一～周五每天恰好 slots_per_day 节，周六周日无课程。

    同一天内课程不重复；同一种课程尽量跨日期分散；结果完全确定。
    """
    counts = weekly_course_counts(company, education_status, rng_seed, week_start)
    slots_per_day = company_slots_per_day(education_status)
    assert slots_per_day is not None
    placement = _spread_placement(counts, slots_per_day, _week_seed(rng_seed, week_start))
    days = [week_start + timedelta(days=i) for i in range(5)]
    return {day: list(courses) for day, courses in zip(days, placement)}


def courses_for_date(
    company: CompanyState,
    education_status: EducationStatus,
    rng_seed: int,
    current_date: date,
) -> List[CompanyCourse]:
    """指定日期当天应上的公司课程；周六周日返回空列表。"""
    if current_date.weekday() >= 5:
        return []
    week_start = week_start_of(current_date)
    return weekly_curriculum(company, education_status, rng_seed, week_start)[current_date]


def _spread_placement(
    counts: Dict[CompanyCourse, int],
    slots_per_day: int,
    seed: int,
) -> List[List[CompanyCourse]]:
    """把整周课程摊到 5 个工作日（周一→周五，索引 0–4）。

    规则：每天恰好 slots_per_day 节；同日不重复；同一种课程尽量隔日分散；
    使用“最少负载 + 最大间隔 + 周种子轮转”的确定性贪心，必要时做平衡移动
    （每次移动使总失衡严格下降，保证终止），最终做防御性校验。
    """
    day_offset = seed % 5

    def day_rank(day: int) -> int:
        return (day - day_offset) % 5

    ordered = sorted(_COURSES, key=lambda c: (-counts[c], _COURSES.index(c)))
    days: List[List[CompanyCourse]] = [[] for _ in range(5)]
    last_day: Dict[CompanyCourse, int] = {c: -10 for c in _COURSES}

    for course in ordered:
        for _ in range(counts[course]):
            candidates = [d for d in range(5) if course not in days[d]]
            best = min(
                candidates,
                key=lambda d: (len(days[d]), -((d - last_day[course]) % 5), day_rank(d)),
            )
            days[best].append(course)
            last_day[course] = best

    _rebalance_days(days, slots_per_day)

    for day in range(5):
        if len(days[day]) != slots_per_day:
            raise ValueError(f"课程编排失败：第 {day} 天课程数为 {len(days[day])}，应为 {slots_per_day}。")
        if len(set(days[day])) != len(days[day]):
            raise ValueError(f"课程编排失败：第 {day} 天出现重复课程。")
    return days


def _rebalance_days(days: List[List[CompanyCourse]], slots_per_day: int) -> None:
    """把超载日的课程移动到欠载日，直到每天恰好 slots_per_day 节。

    每次移动必须满足目标日不含该课程（不会产生同日重复）；
    移动使总失衡严格单调下降，因此必然终止。
    """
    for _ in range(128):
        heavy = [d for d in range(5) if len(days[d]) > slots_per_day]
        light = [d for d in range(5) if len(days[d]) < slots_per_day]
        if not heavy and not light:
            return
        source = heavy[0]
        target = light[0]
        movable = [c for c in days[source] if c not in days[target]]
        if not movable:
            raise ValueError("课程编排失败：超载日的课程全部已存在于欠载日。")
        course = min(movable, key=lambda c: _COURSES.index(c))
        days[source].remove(course)
        days[target].append(course)
    raise ValueError("课程编排失败：无法在限制次数内平衡每日课程数。")


# ---------------------------------------------------------------------------
# 把当天课程填入基础日程的 COMPANY Slot
# ---------------------------------------------------------------------------


def fill_company_courses(day_state: DayState, courses: List[CompanyCourse]) -> DayState:
    """把某一天的课程写入 day_state 中 kind == COMPANY 的 Slot.company_course。

    只修改 COMPANY Slot 的 company_course（直接保存 CompanyCourse 枚举）；
    完整保留每个 Slot 的 index / kind / status / free_action；
    不改变 SlotKind / SlotStatus / index / 数量 / 顺序。
    当天没有 COMPANY Slot（周末）且 courses 为空时保持 DayState 原样；
    课程数与 COMPANY Slot 数量不匹配时抛错。
    """
    company_indexes = [slot.index for slot in day_state.slots if slot.kind == SlotKind.COMPANY]
    if not company_indexes:
        if courses:
            raise ValueError(f"当天没有 COMPANY Slot，但提供了 {len(courses)} 节课。")
        return day_state
    if len(company_indexes) != len(courses):
        raise ValueError(f"课程数量（{len(courses)}）与 COMPANY Slot 数量（{len(company_indexes)}）不匹配。")

    new_slots = [
        TimeSlotState(
            index=slot.index,
            kind=slot.kind,
            status=slot.status,
            company_course=slot.company_course,
            free_action=slot.free_action,
        )
        for slot in day_state.slots
    ]
    for slot, course in zip((s for s in new_slots if s.kind == SlotKind.COMPANY), courses):
        slot.company_course = course
    return DayState(slots=new_slots)


def build_day_with_courses(
    day_state: DayState,
    company: CompanyState,
    education_status: EducationStatus,
    rng_seed: int,
    current_date: date,
) -> DayState:
    """基础日程 + 本周课程 → 填入 COMPANY company_course 的当日 DayState。

    周六周日课程为空，DayState 保持原样（FREE ×6 + REST ×2）。
    月末评估不在此处理：即使 is_month_end 为真，仍只生成普通公司课程。
    """
    courses = courses_for_date(company, education_status, rng_seed, current_date)
    return fill_company_courses(day_state, courses)
