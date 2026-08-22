# -*- coding: utf-8 -*-
"""
EXPLORE Skill Unlock Mechanic（确定性累计探索）。

三个概念：
- TRAIN   = 已解锁技能的正式训练（core.skill_training）；
- EXPLORE = 尚未入门领域的探索（本模块，仅 ACTING / CREATION）；
- exploration_progress = 入门发现阶段进度（unlocked 后恒为 100），不是 Skill XP，
  绝不并入 skill_training 的 XP 系统。

设计：
- 完全 deterministic：相同 SkillState + ConditionState 必得相同结果（无 RNG）；
- 不读取 talent / skill value / company / relationship / menstrual 直接 multiplier；
- 使用 Slot 开始时（FreeAction condition cost 应用之前）的 Condition 快照，
  疲劳成本不反向降低本次已经完成的探索质量；
- 最差状态最少 5 次、最好状态也不可能一次解锁。
"""
from __future__ import annotations

from core.models import ConditionState, SkillExplorationResult, SkillId, SkillState

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

BASE_EXPLORATION_GAIN = 25

# 第一版只允许探索的两个领域（与 ExplorationDomain 一致）。
EXPLORABLE_SKILLS = frozenset({SkillId.ACTING, SkillId.CREATION})

MIN_EXPLORATION_GAIN = 20
MAX_EXPLORATION_GAIN = 30

# 解锁时的初始正式能力值（"终于入门"，不是突然拥有很高水平）。
UNLOCKED_VALUE = 10
UNLOCKED_FORM = 50.0
UNLOCKED_XP = 0.0


# ---------------------------------------------------------------------------
# 纯数值公式
# ---------------------------------------------------------------------------


def calculate_exploration_gain(condition: ConditionState) -> int:
    """探索效率（仅由当天当前状态轻微影响）。

    condition_score = (energy + mood + confidence + (100 - stress)) / 4
    adjustment      = round((condition_score - 50) / 10)，clamp 到 -5 ~ +5
    gain            = BASE_EXPLORATION_GAIN + adjustment（严格 20 ~ 30）

    不使用 talent / skill value / company / relationship / menstrual 直接 multiplier。
    """
    condition_score = (
        float(condition.energy)
        + float(condition.mood)
        + float(condition.confidence)
        + (100.0 - float(condition.stress))
    ) / 4.0
    adjustment = round((condition_score - 50.0) / 10.0)
    adjustment = max(-5, min(5, adjustment))
    return BASE_EXPLORATION_GAIN + adjustment


# ---------------------------------------------------------------------------
# Resolver（pure；修改传入 SkillState；不查 DB / 不调 LLM）
# ---------------------------------------------------------------------------


def resolve_skill_exploration(
    skill: SkillState,
    condition: ConditionState,
    skill_id: SkillId,
) -> SkillExplorationResult:
    """执行一次 EXPLORE。

    - target_skill ∈ {ACTING, CREATION}，否则非法；
    - skill.unlocked 必须为 False 且 exploration_progress < 100，否则非法
      （已解锁后只能用 TRAIN，不能继续 EXPLORE）；
    - 进度结算：after = min(100, before + gain)；超过 100 的部分直接丢弃，
      不转 XP；
    - 若 before < 100 且 after == 100：本次正式解锁 unlocked_now=True，
      unlocked=True / progress=100 / value=10 / form=50 / xp=0，talent 不变；
    - 修改与判定全部基于单一 skill 实例，异常时抛错、不产生半写入。
    """
    if skill_id not in EXPLORABLE_SKILLS:
        raise ValueError(
            f"EXPLORE 只允许 {sorted(s.value for s in EXPLORABLE_SKILLS)}，"
            f"不支持 {skill_id.value}（这些是已知训练领域，请使用 TRAIN）。"
        )
    if skill.unlocked:
        raise ValueError(f"{skill_id.value} 已解锁，EXPLORE 不再合法（请使用 TRAIN）。")
    if not (0 <= skill.exploration_progress < 100):
        raise ValueError(
            f"{skill_id.value}.exploration_progress 非法：{skill.exploration_progress}（必须 0–99 且 locked）。"
        )

    progress_before = skill.exploration_progress
    gain = calculate_exploration_gain(condition)
    progress_after = min(100, progress_before + gain)
    unlocked_now = progress_before < 100 and progress_after == 100

    if unlocked_now:
        skill.unlocked = True
        skill.exploration_progress = 100
        skill.value = UNLOCKED_VALUE
        skill.form = UNLOCKED_FORM
        skill.xp = UNLOCKED_XP
    else:
        skill.exploration_progress = progress_after

    return SkillExplorationResult(
        skill=skill_id,
        progress_before=progress_before,
        progress_gain=gain,
        progress_after=progress_after,
        unlocked_before=False,
        unlocked_after=unlocked_now,
        unlocked_now=unlocked_now,
    )
