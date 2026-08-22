from __future__ import annotations

from typing import Mapping, Optional

from core.models import (
    DayState,
    FreeAction,
    FreeActionKind,
    NPCProfile,
    SkillId,
    SkillsState,
    SlotKind,
)
from core.skill_exploration import EXPLORABLE_SKILLS


class FreeActionError(ValueError):
    """自由行动分配失败（非法状态 / 非法 Action / 非法前置条件）。"""


def assign_free_action(
    day_state: DayState,
    skills_state: SkillsState,
    action: FreeAction,
    npc_profiles: Mapping[str, NPCProfile],
) -> None:
    """把玩家选择的 Action 写入当前 PENDING FREE Slot。

    只负责：选择 → 验证 → 写入 free_action。
    不结算任何效果（Skill / Condition / Relationship / Event），
    不改变 Slot 的 status（Action 已选择 ≠ Action 已完成）。

    前置条件依次检查：
    1. DayState 已初始化（slots 非空）；
    2. 当天尚未结束（is_day_complete 为 False）；
    3. 存在当前第一个 PENDING Slot（current_slot）；
    4. 当前 Slot 的 kind 必须是 FREE（SCHOOL / COMPANY / REST 时明确失败，
       禁止跳转到未来 FREE Slot）；
    5. 当前 FREE Slot 尚未安排 Action（不允许覆盖 / 重复分配）。

    额外合法性：
    - TRAIN：对应 SkillState.unlocked 必须为 True；
    - EXPLORE：对应方向（acting / creation）必须仍未 unlocked；
    - SOCIAL：target_npc_id 必须存在于 npc_profiles 且该 NPC active == True
      （不允许写入“以后再猜是谁”的无效 target）。
    """
    if not day_state.slots:
        raise FreeActionError("DayState 尚未初始化（slots 为空），无法安排行动。")
    if day_state.is_day_complete:
        raise FreeActionError("当天 8 个 Slot 已全部完成，无法安排行动。")

    current_index = day_state.current_slot
    if current_index is None:
        raise FreeActionError("当前没有可行动的 Slot。")

    current_slot = next((s for s in day_state.slots if s.index == current_index), None)
    if current_slot is None:
        raise FreeActionError(f"找不到当前 Slot（index={current_index}）。")
    if current_slot.kind != SlotKind.FREE:
        raise FreeActionError(
            f"当前 Slot（index={current_index}，kind={current_slot.kind.value}）不是 FREE，"
            "不能安排自由行动，也不能跳过它去安排未来的 FREE Slot。"
        )
    if current_slot.free_action is not None:
        raise FreeActionError(f"当前 FREE Slot（index={current_index}）已经安排了行动，不能重复分配。")

    if action.kind == FreeActionKind.TRAIN:
        skill = _skill_by_id(skills_state, action.skill)
        if not skill.unlocked:
            raise FreeActionError(f"技能 {action.skill.value} 尚未解锁，不能 TRAIN。")
    elif action.kind == FreeActionKind.EXPLORE:
        if action.exploration_domain is None:
            raise FreeActionError("EXPLORE 必须携带 exploration_domain。")
        skill_id = SkillId(action.exploration_domain.value)
        if skill_id not in EXPLORABLE_SKILLS:
            raise FreeActionError(
                f"EXPLORE 只允许 {sorted(s.value for s in EXPLORABLE_SKILLS)}，"
                f"不支持 {action.exploration_domain.value}。"
            )
        skill = _skill_by_id(skills_state, skill_id)
        if skill.unlocked:
            raise FreeActionError(
                f"{action.exploration_domain.value} 已经解锁，不能 EXPLORE，应改用 TRAIN。"
            )
        if not (0 <= skill.exploration_progress < 100):
            raise FreeActionError(
                f"{action.exploration_domain.value}.exploration_progress 状态非法："
                f"{skill.exploration_progress}（locked 技能必须 0–99）。"
            )
    elif action.kind == FreeActionKind.SOCIAL:
        target = action.target_npc_id
        profile = npc_profiles.get(target) if target is not None else None
        if profile is None:
            raise FreeActionError(f"SOCIAL target 不是有效 NPC：{target}。")
        if not profile.active:
            raise FreeActionError(f"SOCIAL target 已无效（active=False）：{target}。")

    current_slot.free_action = action


def _skill_by_id(skills_state: SkillsState, skill_id: Optional[SkillId]):
    if skill_id is None:
        raise FreeActionError("缺少技能标识。")
    return getattr(skills_state, skill_id.value)
