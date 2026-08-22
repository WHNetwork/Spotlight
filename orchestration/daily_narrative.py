# -*- coding: utf-8 -*-
"""
Daily Narrative（LLM Layer 2B）。

玩家完成一天后阅读的“这一天发生了什么”的主游戏正文：
- 与 Diary 完全独立（各自独立 LLM call；都不读取对方文本）；
- 只消费 canonical DailyWritingContext；
- 强制经过 Global Writing Constitution + Provider Adapter（generate_player_text）；
- 不查 DB、不改 GameState、不触发 Event、不调用 Event Director、不 retry。
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from core.llm import BaseProvider
from orchestration.daily_context import DailyWritingContext
from orchestration.writing.prompt_builder import generate_player_text
from orchestration.writing_context_models import PlayerTextGenerationStatus


DAILY_NARRATIVE_TASK_INSTRUCTIONS: str = """【Daily Narrative 任务】
把当天已经发生的事实写成玩家阅读的主游戏正文。

1. 视角：第二人称有限视角（“你”）。只写角色能够感知到的世界；禁止全知旁白，
   禁止“与此同时，另一间练习室里……”，禁止“她不知道的是……”。
2. 组织：保持这一天自然的连续性，但绝不是 8 个时间格的逐项流水账；
   普通时间段可以压缩；训练表现、身体状态、重要互动、特殊事件、月评等才适当展开。
3. 场景数量不固定：事实少允许短；事实多选择性展开；不要为了字数补剧情。
4. 纯正文：不加标题、不加日期、不加“Day 27”“今日总结”，不使用 Markdown 或列表。
5. 对白：只允许非常少、低风险、用于呈现已发生互动的自然对白；
   不得通过虚构对白新增承诺、秘密、长期计划、重大关系事实、公司信息或新事件。
6. 关系边界：只写轻微即时感受；禁止“从今天开始你们成了真正的朋友”这类结论。
   不得根据一次行为自行推断 Character Guidance 未提供的稳定人格；
   已有 Character Guidance 必须保持连续。
7. 不要输出任何内部术语：NarrativeBand、Signal、SymptomLevel、EventTier、
   slot_type、band 名称等都不准出现在正文中。
8. 身体状态用行为表现；生理期只有对当天体验确实有意义时才提，绝不每次必写。
9. 月评：如当天有正式月评，可写“今天有月度评价”及大体感受，不要强行报精确分数。
10. 不提前知道第二天：正文可以自然结束在洗漱、回宿舍、准备睡觉等，但不得提及
    明天的安排、明天的身体状态或任何 settlement 之后的事实。"""


class DailyNarrativeGenerationResult(BaseModel):
    status: PlayerTextGenerationStatus
    text: Optional[str] = None
    provider_name: str
    error_message: Optional[str] = None


def generate_daily_narrative(
    context: DailyWritingContext,
    provider_name: str,
    provider: Optional[BaseProvider] = None,
) -> DailyNarrativeGenerationResult:
    """生成当天 Daily Narrative（一次调用，无 retry / 无 provider fallback）。"""
    try:
        text = generate_player_text(
            provider_name=provider_name,
            task_name="daily_narrative",
            task_instructions=DAILY_NARRATIVE_TASK_INSTRUCTIONS,
            fact_context=context.model_dump(mode="json"),
            provider=provider,
            json_mode=False,
        )
    except Exception as exc:
        return DailyNarrativeGenerationResult(
            status=PlayerTextGenerationStatus.PROVIDER_ERROR,
            provider_name=provider_name,
            error_message=f"{type(exc).__name__}: {exc}",
        )

    if not isinstance(text, str) or not text.strip():
        return DailyNarrativeGenerationResult(
            status=PlayerTextGenerationStatus.INVALID_OUTPUT,
            provider_name=provider_name,
            error_message="模型返回空内容。",
        )
    return DailyNarrativeGenerationResult(
        status=PlayerTextGenerationStatus.SUCCESS,
        text=text,
        provider_name=provider_name,
    )
