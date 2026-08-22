# -*- coding: utf-8 -*-
"""
NPC Character Facts / Character Bible 生成（LLM Layer 3）。

- 全部 Python deterministic：独立 per-NPC RNG namespace，绝不消耗
  npc-roster-bootstrap / Talent / Company 等既有随机序列；
- Character Facts 100% narrative-only：禁止任何 Simulation Core 读取它们
  作为 mechanics modifier；
- 不生成 MBTI / 心理诊断 / backstory / 年龄生日国籍。
"""
from __future__ import annotations

import hashlib
import random
from typing import Tuple

from core.models import (
    NPCBehaviorHabit,
    NPCCharacterFacts,
    NPCCharacterLevel,
    NPCRole,
    NPCSpeechVerbosity,
)

# 默认分布：大多数人中间，少部分明显偏低/偏高（避免全员极端人格）。
_LEVEL_POOL: Tuple[NPCCharacterLevel, ...] = (
    NPCCharacterLevel.LOW,
    NPCCharacterLevel.MEDIUM,
    NPCCharacterLevel.MEDIUM,
    NPCCharacterLevel.MEDIUM,
    NPCCharacterLevel.HIGH,
)

_HUMOR_POOL: Tuple[NPCCharacterLevel, ...] = (
    NPCCharacterLevel.LOW,
    NPCCharacterLevel.LOW,
    NPCCharacterLevel.MEDIUM,
    NPCCharacterLevel.MEDIUM,
    NPCCharacterLevel.HIGH,
)

_COMPETITIVE_POOL: Tuple[NPCCharacterLevel, ...] = (
    NPCCharacterLevel.LOW,
    NPCCharacterLevel.MEDIUM,
    NPCCharacterLevel.MEDIUM,
    NPCCharacterLevel.HIGH,
)

# speech verbosity 与 social_energy 弱相关（非绝对规则）。
_VERBOSITY_BY_SOCIAL = {
    NPCCharacterLevel.LOW: (NPCSpeechVerbosity.BRIEF, NPCSpeechVerbosity.BRIEF, NPCSpeechVerbosity.BALANCED),
    NPCCharacterLevel.MEDIUM: (NPCSpeechVerbosity.BRIEF, NPCSpeechVerbosity.BALANCED, NPCSpeechVerbosity.BALANCED, NPCSpeechVerbosity.TALKATIVE),
    NPCCharacterLevel.HIGH: (NPCSpeechVerbosity.BALANCED, NPCSpeechVerbosity.TALKATIVE, NPCSpeechVerbosity.TALKATIVE),
}

_HABIT_CATALOG: Tuple[NPCBehaviorHabit, ...] = tuple(NPCBehaviorHabit)


def build_npc_character_facts(
    rng_seed: int,
    npc_id: str,
    role: NPCRole,
) -> NPCCharacterFacts:
    """为新 NPC 生成一次稳定的 Character Facts（pure；同输入永远同输出）。

    只依赖 rng_seed + npc_id + role，与 roster 循环顺序/其他 NPC 无关；
    不接 GameState；不修改任何状态。
    """
    namespace = f"npc-character:{rng_seed}:{npc_id}"
    rng = random.Random(int(hashlib.sha256(namespace.encode("utf-8")).hexdigest()[:8], 16))

    social_energy = rng.choice(_LEVEL_POOL)
    facts = NPCCharacterFacts(
        social_energy=social_energy,
        warmth=rng.choice(_LEVEL_POOL),
        directness=rng.choice(_LEVEL_POOL),
        expressiveness=rng.choice(_LEVEL_POOL),
        conscientiousness=rng.choice(_LEVEL_POOL),
        humor_tendency=rng.choice(_HUMOR_POOL),
        competitive_drive=rng.choice(_COMPETITIVE_POOL) if role == NPCRole.TRAINEE else None,
        speech_verbosity=rng.choice(_VERBOSITY_BY_SOCIAL[social_energy]),
        habits=tuple(rng.sample(_HABIT_CATALOG, 2)),
    )
    return facts
