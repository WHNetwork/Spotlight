from __future__ import annotations

from datetime import date
from typing import Mapping, MutableMapping, Tuple

from core.models import (
    NPCProfile,
    RelationshipDevelopmentResult,
    RelationshipInteractionResult,
    RelationshipSignal,
    RelationshipState,
    GameState,
)

# ---------------------------------------------------------------------------
# Relationship Core (Step 9 + Step 13)
#
# 领域边界：
# - 只负责 NPC 注册与结构化关系经历的机械结算；
# - 不实现 NPC AI / schedule / 关系衰减 / 关系阶段 / 恋爱系统 /
#   Relationship Event / LLM / 数据库 / Slot completion；
# - 普通 FREE SOCIAL = CASUAL_CONTACT：只确定性提升 familiarity；
#   closeness / trust / tension 只通过明确 RelationshipSignal 变化；
# - Signal 数学对所有 NPC / Role / Company 使用同一套公式（无隐藏 modifier）；
# - 未来 Event Effect 只能引用 RelationshipSignal，
#   禁止 Event / LLM / UI 直接传任意 delta。
# ---------------------------------------------------------------------------


BASE_FAMILIARITY_GAIN = 12.0


class RelationshipResolutionError(ValueError):
    """关系经历结算失败（NPC 缺失 / inactive / Relationship 缺失 / 非法输入）。"""


def register_npc(game_state: GameState, profile: NPCProfile) -> None:
    """把新 NPC 正式加入玩家关系网络。

    同时建立 NPCProfile（npcs）与对应初始 RelationshipState（relationships），
    保证两边永远同步；npc_id 已存在时明确失败（稳定世界事实，不允许覆盖 / 重置）。
    不生成随机数、不创建历史、不调用 LLM。
    """
    if profile.npc_id in game_state.npcs:
        raise ValueError(f"NPC 已存在：{profile.npc_id}（npc_id 是稳定世界事实，不允许覆盖或重置）。")
    game_state.npcs[profile.npc_id] = profile
    game_state.relationships[profile.npc_id] = RelationshipState()


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def _signal_math(
    signal: RelationshipSignal,
    familiarity_before: float,
    closeness_before: float,
    trust_before: float,
    tension_before: float,
) -> Tuple[float, float, float, float]:
    """单个 Signal 的机械数学（全部基于 before 快照；familiarity 永不下降）。"""
    f0, c0, t0, s0 = familiarity_before, closeness_before, trust_before, tension_before
    f1, c1, t1, s1 = f0, c0, t0, s0

    if signal == RelationshipSignal.CASUAL_CONTACT:
        f1 = _clamp(f0 + BASE_FAMILIARITY_GAIN * (1.0 - f0 / 100.0))
    elif signal == RelationshipSignal.SHARED_POSITIVE_EXPERIENCE:
        f1 = _clamp(f0 + 4.0 * (1.0 - f0 / 100.0))
        cf = 0.25 + 0.75 * (f0 / 100.0)  # 使用 familiarity_before
        c1 = _clamp(c0 + 8.0 * cf * (1.0 - c0 / 100.0))
    elif signal == RelationshipSignal.RELIABILITY_CONFIRMED:
        f1 = _clamp(f0 + 3.0 * (1.0 - f0 / 100.0))
        tf = 0.35 + 0.65 * (f0 / 100.0)  # 使用 familiarity_before
        t1 = _clamp(t0 + 10.0 * tf * (1.0 - t0 / 100.0))
    elif signal == RelationshipSignal.FRICTION:
        s1 = _clamp(s0 + 12.0 * (1.0 - s0 / 100.0))
    elif signal == RelationshipSignal.TRUST_BREACH:
        t1 = _clamp(t0 * 0.75)  # 比例损失
        s1 = _clamp(s0 + 18.0 * (1.0 - s0 / 100.0))
    elif signal == RelationshipSignal.REPAIR:
        s1 = _clamp(s0 * 0.70)
    elif signal == RelationshipSignal.DISTANCING:
        c1 = _clamp(c0 * 0.85)

    return f1, c1, t1, s1


def resolve_relationship_signal(
    npc_profiles: Mapping[str, NPCProfile],
    relationships: MutableMapping[str, RelationshipState],
    npc_id: str,
    interaction_date: date,
    signal: RelationshipSignal,
) -> RelationshipDevelopmentResult:
    """结算一次结构化关系经历（RelationshipSignal）。

    - 只修改目标 NPC 的 RelationshipState 与 last_interaction_date；
    - 不接收 GameState：不访问 SQLite / Event / LLM / Narrative；
    - 先验证 → 读取 before 快照 → 计算全部 after → 一次写回；
    - 所有 Signal 都更新 last_interaction_date（每种都表示一次真实关系经历）。

    未来可被 Event Effect / Relationship-specific mechanics 调用。
    """
    if not npc_id or not str(npc_id).strip():
        raise RelationshipResolutionError("npc_id 必须非空。")
    profile = npc_profiles.get(npc_id)
    if profile is None:
        raise RelationshipResolutionError(f"NPC 不存在：{npc_id}。")
    if not profile.active:
        raise RelationshipResolutionError(f"NPC 已无效（active=False）：{npc_id}。")
    relationship = relationships.get(npc_id)
    if relationship is None:
        raise RelationshipResolutionError(f"缺少 NPC 的 RelationshipState：{npc_id}（状态不一致，明确失败）。")

    familiarity_before = relationship.familiarity
    closeness_before = relationship.closeness
    trust_before = relationship.trust
    tension_before = relationship.tension

    familiarity_after, closeness_after, trust_after, tension_after = _signal_math(
        signal, familiarity_before, closeness_before, trust_before, tension_before
    )

    relationship.familiarity = familiarity_after
    relationship.closeness = closeness_after
    relationship.trust = trust_after
    relationship.tension = tension_after
    relationship.last_interaction_date = interaction_date

    return RelationshipDevelopmentResult(
        npc_id=npc_id,
        interaction_date=interaction_date,
        signal=signal,
        familiarity_before=familiarity_before,
        familiarity_after=familiarity_after,
        closeness_before=closeness_before,
        closeness_after=closeness_after,
        trust_before=trust_before,
        trust_after=trust_after,
        tension_before=tension_before,
        tension_after=tension_after,
    )


def resolve_social_interaction(
    npc_profiles: Mapping[str, NPCProfile],
    relationships: MutableMapping[str, RelationshipState],
    npc_id: str,
    interaction_date: date,
) -> RelationshipInteractionResult:
    """完成一次 FREE SOCIAL interaction 的机械结算（Step 9 协议）。

    语义 = CASUAL_CONTACT：只增加 familiarity（复用统一 Signal 数学），
    closeness / trust / tension 保持不变；仍更新 last_interaction_date。

    结果映射为既有 RelationshipInteractionResult（SOCIAL Slot 历史协议），
    保证 SlotResolutionResult.relationship_result 类型与持久化 schema 不变。
    """
    development = resolve_relationship_signal(
        npc_profiles, relationships, npc_id, interaction_date,
        RelationshipSignal.CASUAL_CONTACT,
    )
    return RelationshipInteractionResult(
        npc_id=development.npc_id,
        interaction_date=development.interaction_date,
        familiarity_before=development.familiarity_before,
        familiarity_after=development.familiarity_after,
        familiarity_gain=development.familiarity_after - development.familiarity_before,
        closeness_before=development.closeness_before,
        closeness_after=development.closeness_after,
        trust_before=development.trust_before,
        trust_after=development.trust_after,
        tension_before=development.tension_before,
        tension_after=development.tension_after,
    )
