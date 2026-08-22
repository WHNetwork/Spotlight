# -*- coding: utf-8 -*-
"""
NPC Writing Context（LLM Layer 3）。

把持久化 NPCCharacterFacts + RelationshipState 转成模型可读的自然语义指导：
- Character Guidance 是 Writer Guidance，不是玩家已知心理诊断；
- Relationship 距离继续使用 NarrativeBand；
- pure function，不接 GameState、不查 DB。
"""
from __future__ import annotations

from core.models import (
    NPCBehaviorHabit,
    NPCCharacterLevel,
    NPCProfile,
    NPCSpeechVerbosity,
    RelationshipState,
)
from orchestration.writing_context_models import NPCWritingContext, band_for

# ---------------------------------------------------------------------------
# 稳定自然语义标签（enum token 绝不直接进入玩家正文）
# ---------------------------------------------------------------------------

_SOCIAL_ENERGY_LABELS = {
    NPCCharacterLevel.LOW: "更倾向先观察，不会自动加入所有交流",
    NPCCharacterLevel.MEDIUM: "社交参与程度自然、适中",
    NPCCharacterLevel.HIGH: "比较容易主动加入交流",
}

_WARMTH_LABELS = {
    NPCCharacterLevel.LOW: "人际表达较克制，但不代表不友好",
    NPCCharacterLevel.MEDIUM: "表达温度适中",
    NPCCharacterLevel.HIGH: "比较容易通过小动作表现友善",
}

_DIRECTNESS_LABELS = {
    NPCCharacterLevel.LOW: "表达更委婉",
    NPCCharacterLevel.MEDIUM: "直接程度适中",
    NPCCharacterLevel.HIGH: "倾向把意思说得比较直接，但不等于失礼",
}

_EXPRESSIVENESS_LABELS = {
    NPCCharacterLevel.LOW: "外在反应较少",
    NPCCharacterLevel.MEDIUM: "情绪表达适中",
    NPCCharacterLevel.HIGH: "反应较容易被看出来，但不过度戏剧化",
}

_CONSCIENTIOUSNESS_LABELS = {
    NPCCharacterLevel.LOW: "处理细节相对随性",
    NPCCharacterLevel.MEDIUM: "做事稳定",
    NPCCharacterLevel.HIGH: "做事比较认真、细致",
}

_HUMOR_LABELS = {
    NPCCharacterLevel.LOW: "很少主动用玩笑表达",
    NPCCharacterLevel.MEDIUM: "偶尔会有轻松的表达",
    NPCCharacterLevel.HIGH: "比较容易用一点玩笑缓和交流，但不是每句话都搞笑",
}

_COMPETITIVE_LABELS = {
    NPCCharacterLevel.LOW: "不太以比较为中心",
    NPCCharacterLevel.MEDIUM: "会正常关注竞争和表现",
    NPCCharacterLevel.HIGH: "竞争意识较强，但不代表敌意",
}

_VERBOSITY_LABELS = {
    NPCSpeechVerbosity.BRIEF: "通常说得比较简短",
    NPCSpeechVerbosity.BALANCED: "说话长度自然、适中",
    NPCSpeechVerbosity.TALKATIVE: "熟悉或情境合适时更容易多说几句（仍受关系距离约束）",
}

_HABIT_LABELS = {
    NPCBehaviorHabit.TAKES_NOTES: "空下来时有记东西的习惯",
    NPCBehaviorHabit.KEEPS_DRINK_NEARBY: "手边常放着水或饮料",
    NPCBehaviorHabit.TIDIES_SMALL_ITEMS: "会把零碎东西随手归位",
    NPCBehaviorHabit.CHECKS_PHONE_DURING_BREAKS: "休息时会看手机",
    NPCBehaviorHabit.ARRIVES_A_LITTLE_EARLY: "习惯比约定时间早到一点",
    NPCBehaviorHabit.TAPS_RHYTHM_WHEN_IDLE: "等着的时候偶尔会跟着节奏轻敲",
    NPCBehaviorHabit.HUMS_WHEN_FOCUSED: "专注时会不自觉地哼一点调子",
    NPCBehaviorHabit.STRETCHES_WHILE_WAITING: "等待时会习惯性活动身体",
    NPCBehaviorHabit.WATCHES_BEFORE_JOINING: "加入前会先观察一下",
    NPCBehaviorHabit.PLAYS_WITH_PEN_OR_BOTTLE_CAP: "手里有笔或瓶盖时会不自觉地转",
    NPCBehaviorHabit.RUBS_NECK_WHEN_TIRED: "累了的时候会揉脖子",
    NPCBehaviorHabit.PACKS_THINGS_CAREFULLY: "收东西时很仔细",
}

_LABEL_MAP = {
    "social_energy": _SOCIAL_ENERGY_LABELS,
    "warmth": _WARMTH_LABELS,
    "directness": _DIRECTNESS_LABELS,
    "expressiveness": _EXPRESSIVENESS_LABELS,
    "conscientiousness": _CONSCIENTIOUSNESS_LABELS,
    "humor_tendency": _HUMOR_LABELS,
    "competitive_drive": _COMPETITIVE_LABELS,
}


def build_npc_writing_context(
    npc_profile: NPCProfile,
    relationship: RelationshipState,
) -> NPCWritingContext:
    """把 NPC 身份 + 当前关系 + 稳定 Character Facts 转成写作上下文（pure）。"""
    facts = npc_profile.character_facts

    guidance: dict = {}
    for field, level in (
        ("social_energy", facts.social_energy),
        ("warmth", facts.warmth),
        ("directness", facts.directness),
        ("expressiveness", facts.expressiveness),
        ("conscientiousness", facts.conscientiousness),
        ("humor_tendency", facts.humor_tendency),
    ):
        guidance[field] = _LABEL_MAP[field][level]
    if facts.competitive_drive is not None:
        guidance["competitive_drive"] = _COMPETITIVE_LABELS[facts.competitive_drive]
    else:
        guidance["competitive_drive"] = None
    guidance["speech_verbosity"] = _VERBOSITY_LABELS[facts.speech_verbosity]
    guidance["habits"] = [_HABIT_LABELS[h] for h in facts.habits]

    return NPCWritingContext(
        npc_id=npc_profile.npc_id,
        name=npc_profile.name,
        role=npc_profile.role.value,
        specialty=npc_profile.specialty.value if npc_profile.specialty else None,
        relationship={
            "familiarity": band_for(relationship.familiarity),
            "closeness": band_for(relationship.closeness),
            "trust": band_for(relationship.trust),
            "tension": band_for(relationship.tension),
        },
        character_guidance=guidance,
    )
