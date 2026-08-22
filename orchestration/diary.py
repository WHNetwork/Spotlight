# -*- coding: utf-8 -*-
"""
Diary（LLM Layer 2B）。

角色晚上以第一人称留下的私人记录：
- 与 Daily Narrative 完全独立（独立 LLM call；绝不读取 Narrative 文本）；
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


DIARY_TASK_INSTRUCTIONS: str = """【Diary 任务】
以角色本人第一人称（“我”）写今晚的私人记录。它不是 Daily Narrative 的第一人称改写，
也不是小说、心理咨询记录、复盘、训练报告或一天总结。

1. 从 FACT DATA 中选择角色最可能记下的 2–4 件事即可。允许漏掉 Slot、无所谓的 Event，
   也允许某件小事多写一点、某件大事只写一句；一旦提到，就必须忠于事实。
2. events[*].event_brief 是发生过的事，choice_brief 是玩家实际做过的选择。不得改写其语义，
   不得根据 effect_summary 补造老师评价、关系升级或其他原因。
3. 允许短、碎、普通、偶尔重复、句子不完整或突然停住：“今天声乐课还行。”“先这样。”
   不要求完整起承转合，也不要把口语自动润色成漂亮散文。
4. 可以有主观感受，但只能是当天事实支持的即时感受。不要用“其实、好像、有点、说不上来、
   不知道为什么、可能只是”串起每一段，也不要自动添加空虚、怅然或复杂心理。
5. 禁止新增作业、截止日、时间冲突、约定、明天/下次安排、NPC 背景、评价、承诺或关系结论。
   Diary 不读取 Narrative，也不能继承 Narrative 可能写出的任何额外细节。
6. 不做“今天成长了很多”“虽然很累但很充实”“今天没什么特别的”“不知道明天会怎样”式
   总结。可以停在一件具体小事、一句短话或写到这里自然结束。
7. 身体状态只在确实影响记录内容时生活化写；不补新症状。生理期无必要可以完全不提。
8. 纯文本：无日期、“亲爱的日记”、Markdown、列表、内部字段、数值或系统名；不提前知道明天。"""


class DiaryGenerationResult(BaseModel):
    status: PlayerTextGenerationStatus
    text: Optional[str] = None
    provider_name: str
    error_message: Optional[str] = None


def generate_diary_entry(
    context: DailyWritingContext,
    provider_name: str,
    provider: Optional[BaseProvider] = None,
) -> DiaryGenerationResult:
    """生成当天 Diary（一次调用，无 retry / 无 provider fallback）。"""
    try:
        text = generate_player_text(
            provider_name=provider_name,
            task_name="diary",
            task_instructions=DIARY_TASK_INSTRUCTIONS,
            fact_context=context.model_dump(mode="json"),
            provider=provider,
            json_mode=False,
        )
    except Exception as exc:
        return DiaryGenerationResult(
            status=PlayerTextGenerationStatus.PROVIDER_ERROR,
            provider_name=provider_name,
            error_message=f"{type(exc).__name__}: {exc}",
        )

    if not isinstance(text, str) or not text.strip():
        return DiaryGenerationResult(
            status=PlayerTextGenerationStatus.INVALID_OUTPUT,
            provider_name=provider_name,
            error_message="模型返回空内容。",
        )
    return DiaryGenerationResult(
        status=PlayerTextGenerationStatus.SUCCESS,
        text=text,
        provider_name=provider_name,
    )
