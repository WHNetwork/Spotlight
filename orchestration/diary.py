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
以角色本人第一人称（“我”），写今天晚上的私人记录。

1. 这是私人日记，不是小说、作文、工作总结、复盘或训练报告。
2. 只写角色自己还记得、在意、觉得累、觉得烦、觉得好笑、觉得有点开心、
   想记住的少数事情；不需要记录全部时间格，不需要流水账。
3. 允许短、碎、普通、有一点重复、一句话突然停住；不要求完整起承转合。
4. 不要每天总结成长（“今天我成长了很多”“虽然很累但我收获满满”
   “这是充实而有意义的一天”这类话默认禁止）。
5. 可以主观，但不得创造事实：可以写“我觉得她今天好像没那么生疏了”
   （若关系变化支持）；不得写“她一定已经把我当最好的朋友了”。
6. 身体状态只在确实影响当天体验时写；生理期不适明显时可以自然提及，
   但绝不每次经期都写“今天又来月经了”。
7. 纯文本：不加日期、不加“亲爱的日记”、不用 Markdown 或列表。
8. 不要输出任何内部术语（band、signal、数值、系统名）。
9. 不提前知道第二天。"""


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
