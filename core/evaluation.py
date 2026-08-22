from __future__ import annotations

import hashlib
from datetime import date
from typing import Dict, List, Tuple

from pydantic import BaseModel, Field, model_validator

from core.condition_resolution import skill_readiness
from core.models import CompanyState, GameState, SkillId


# ---------------------------------------------------------------------------
# Monthly Evaluation Core (Step 10)
#
# 制度性结算节点，不属于 Special Event Trigger Framework：
# - 不经过 Event Budget / Priority / RNG / LLM relevance / PendingEvent；
# - 只发生在：自然月末 + 当天 8 Slot 全部 COMPLETED + pending_event is None
#   + trainee_day >= 14；
# - 只评价六个核心技能（DANCE/VOCAL/RAP/STAGE/CAMERA/LANGUAGE）；
# - Performance = 0.80×Value + 0.12×Form + 0.08×ConditionReadiness；
# - 总体分 = Σ 归一化公司权重 × 单项 performance；
# - 不生成 grade / rank / trend；不推进日期；不建下一天；不写数据库；不调用 LLM。
# ---------------------------------------------------------------------------


MIN_EVALUATION_TENURE_DAYS = 14

EVALUATED_SKILLS: Tuple[SkillId, ...] = (
    SkillId.DANCE,
    SkillId.VOCAL,
    SkillId.RAP,
    SkillId.STAGE,
    SkillId.CAMERA,
    SkillId.LANGUAGE,
)

SKILL_VALUE_WEIGHT = 0.80
FORM_WEIGHT = 0.12
CONDITION_WEIGHT = 0.08

_COURSE_TO_WEIGHT_FIELD: Dict[SkillId, str] = {
    SkillId.DANCE: "dance",
    SkillId.VOCAL: "vocal",
    SkillId.RAP: "rap",
    SkillId.STAGE: "stage",
    SkillId.CAMERA: "camera",
    SkillId.LANGUAGE: "language",
}


class MonthlyEvaluationError(ValueError):
    """正式月度评价失败（不满足资格 / 状态异常 / 权重异常）。"""


class SkillEvaluationResult(BaseModel):
    """单项技能评价结果（可解释、不含隐藏成长信息）。"""

    skill: SkillId
    skill_value: float = Field(ge=0, le=100)
    form: float = Field(ge=0, le=100)
    condition_readiness: float = Field(ge=0, le=100)
    company_weight: float = Field(ge=0, le=1)
    performance_score: float = Field(ge=0, le=100)


class MonthlyEvaluationResult(BaseModel):
    """一次正式月度评价的结构化事实。"""

    evaluation_id: str
    evaluation_date: date
    year: int
    month: int
    trainee_day: int
    skill_results: List[SkillEvaluationResult]
    overall_score: float

    @model_validator(mode="after")
    def _validate_skill_results(self) -> "MonthlyEvaluationResult":
        skills = [r.skill for r in self.skill_results]
        if len(skills) != len(EVALUATED_SKILLS):
            raise ValueError(f"月度评价必须恰好包含 {len(EVALUATED_SKILLS)} 项技能（当前 {len(skills)} 项）。")
        if list(skills) != list(EVALUATED_SKILLS):
            raise ValueError("skill_results 必须恰好包含六个核心技能、每项唯一且顺序按 EVALUATED_SKILLS。")
        return self


def is_monthly_evaluation_eligible(game_state: GameState) -> bool:
    """正式月评资格：自然月末 + 当天完成 + 无 PendingEvent + trainee_day >= 14。

    纯判断，不读取数据库、不修改状态。
    """
    if not game_state.time.is_month_end:
        return False
    if not game_state.day.is_day_complete:
        return False
    if game_state.pending_event is not None:
        return False
    if game_state.time.trainee_day < MIN_EVALUATION_TENURE_DAYS:
        return False
    return True


def _evaluation_id(rng_seed: int, evaluation_date: date) -> str:
    """稳定 evaluation_id：同一存档同一自然月相同，不同月份/不同存档不同。

    不修改 rng_seed。
    """
    namespace = f"monthly-evaluation:{rng_seed}:{evaluation_date.year}-{evaluation_date.month:02d}"
    return hashlib.sha256(namespace.encode("utf-8")).hexdigest()


def _normalized_company_weights(company: CompanyState) -> Dict[SkillId, float]:
    """取六项核心课程的 training_weights 并重新归一化（FITNESS 权重被移除）。

    权重异常（缺失 / 负值 / raw_sum <= 0）时明确失败，不做 equal-weights fallback。
    """
    if company.training_weights is None:
        raise MonthlyEvaluationError("company.training_weights 未初始化，无法进行月评。")
    raw: Dict[SkillId, float] = {}
    raw_sum = 0.0
    for skill in EVALUATED_SKILLS:
        value = float(getattr(company.training_weights, _COURSE_TO_WEIGHT_FIELD[skill]))
        if value < 0.0:
            raise MonthlyEvaluationError(f"公司课程权重不能为负：{skill.value}={value}。")
        raw[skill] = value
        raw_sum += value
    if raw_sum <= 0.0:
        raise MonthlyEvaluationError("公司六项核心课程权重之和必须 > 0（当前 0 或负）。")
    return {skill: raw[skill] / raw_sum for skill in EVALUATED_SKILLS}


def resolve_monthly_evaluation(game_state: GameState) -> Tuple[GameState, MonthlyEvaluationResult]:
    """执行正式月度评价。

    - deep-copy 输入，原 GameState 不被修改；
    - 不访问 SQLite、不调用 LLM、不推进 current_date、不创建下一天、不触发 Event；
    - 不满足资格时抛 MonthlyEvaluationError（不跳过、不返回 None、不强评）；
    - 成功只更新 working_state.trainee.latest_evaluation_score / date。
    """
    if not is_monthly_evaluation_eligible(game_state):
        raise MonthlyEvaluationError(
            "当前不满足正式月评条件（需要：自然月末 + 当天 8 Slot 全部完成 + "
            "无 PendingEvent + trainee_day >= 14）。"
        )

    working_state = game_state.model_copy(deep=True)
    weights = _normalized_company_weights(working_state.company)

    skill_results: List[SkillEvaluationResult] = []
    for skill in EVALUATED_SKILLS:
        skill_state = getattr(working_state.skills, skill.value)
        if not skill_state.unlocked or skill_state.value is None or skill_state.form is None:
            raise MonthlyEvaluationError(
                f"评价技能 {skill.value} 状态异常（unlocked / value / form 不完整），不能评价。"
            )
        readiness = skill_readiness(working_state.condition, skill)
        performance = (
            SKILL_VALUE_WEIGHT * float(skill_state.value)
            + FORM_WEIGHT * float(skill_state.form)
            + CONDITION_WEIGHT * readiness
        )
        performance = max(0.0, min(100.0, performance))
        skill_results.append(
            SkillEvaluationResult(
                skill=skill,
                skill_value=float(skill_state.value),
                form=float(skill_state.form),
                condition_readiness=readiness,
                company_weight=weights[skill],
                performance_score=performance,
            )
        )

    overall_score = sum(r.performance_score * r.company_weight for r in skill_results)

    result = MonthlyEvaluationResult(
        evaluation_id=_evaluation_id(working_state.meta.rng_seed, working_state.time.current_date),
        evaluation_date=working_state.time.current_date,
        year=working_state.time.year,
        month=working_state.time.month,
        trainee_day=working_state.time.trainee_day,
        skill_results=skill_results,
        overall_score=overall_score,
    )

    working_state.trainee.latest_evaluation_score = result.overall_score
    working_state.trainee.latest_evaluation_date = result.evaluation_date

    return working_state, result
