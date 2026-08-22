from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field

from core.models import (
    EventCategory,
    EventDomainAction,
    EventInteractionMode,
    EventTier,
    EventTriggerMode,
)


# ---------------------------------------------------------------------------
# 跨模块共享的纯 Event 类型（不含 callable）。
# 依赖方向：event_models → core.models（models 不 import event_models，无循环）。
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EventChoiceDefinition:
    """静态 Choice 定义。

    只表达“玩家可以做出哪个决定”（非空、稳定的 choice_id + 语义 brief）
    以及该 Choice 的预定义机械 Effects（effects 可为空）。
    不包含对白 / 数值 / prompt。
    """

    choice_id: str
    director_brief: str
    effects: Tuple[EventDomainAction, ...] = ()


class EventSoftScore(BaseModel):
    """LLM 对单个候选事件的结构化 Soft Judgment。"""

    event_id: str
    relevance: float = Field(ge=0.0, le=1.0)
    reason_tags: List[str] = Field(default_factory=list)


class EventSoftJudgment(BaseModel):
    """LLM 对当前整批 eligible LLM_ASSISTED 候选的结构化 Soft Judgment。"""

    should_trigger_any: bool
    scores: List[EventSoftScore] = Field(default_factory=list)


class EventTriggerDecision(BaseModel):
    """一次事件评估的最终触发裁决（不代表事件已被解决）。"""

    event_id: str
    category: EventCategory
    trigger_mode: EventTriggerMode
    tier: EventTier
    interaction_mode: EventInteractionMode
    priority: int
    base_probability: float
    soft_relevance: Optional[float] = None
    effective_probability: float
    triggered: bool
    slot_index: int
    game_date: date
    context_npc_id: Optional[str] = None
