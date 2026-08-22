# -*- coding: utf-8 -*-
"""
共享 writing context 模型（LLM Layer 3）。

NarrativeBand / band_for / NPCWritingContext 被 daily_context 与
npc_writing_context 共用；独立成模块避免相互循环依赖。
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class NarrativeBand(str, Enum):
    """统一叙事档位（Python deterministic；不把连续浮点 severity 给 LLM）。"""

    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


_BAND_EDGES = (
    (20.0, NarrativeBand.VERY_LOW),
    (40.0, NarrativeBand.LOW),
    (60.0, NarrativeBand.MODERATE),
    (80.0, NarrativeBand.HIGH),
    (101.0, NarrativeBand.VERY_HIGH),
)


def band_for(value: Optional[float]) -> str:
    """0–19 VERY_LOW / 20–39 LOW / 40–59 MODERATE / 60–79 HIGH / 80–100 VERY_HIGH。"""
    if value is None:
        return "UNKNOWN"
    v = max(0.0, min(100.0, float(value)))
    for edge, band in _BAND_EDGES:
        if v < edge:
            return band.value
    return NarrativeBand.VERY_HIGH.value


class NPCWritingContext(BaseModel):
    """单个 NPC 的写作上下文：身份 + 当前关系距离 + 稳定 Character Guidance。

    只用于叙事（Daily Narrative / Diary / Event Scene / 未来 NPC Dialogue），
    永不作为 mechanics modifier。
    """

    npc_id: str
    name: str
    role: str
    specialty: Optional[str] = None
    relationship: Dict[str, str] = Field(default_factory=dict)
    character_guidance: Dict[str, object] = Field(default_factory=dict)


class PlayerTextGenerationStatus(str, Enum):
    """玩家可见文本生成状态（transient，不持久化；三个写作任务共用）。"""

    SUCCESS = "SUCCESS"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    INVALID_OUTPUT = "INVALID_OUTPUT"
