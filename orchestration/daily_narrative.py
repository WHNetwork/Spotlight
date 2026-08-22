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
把 FACT DATA 中这一天确实发生的事情写成自然的生活叙述，让玩家感觉自己经历了这些事。
它不是小说章节、成长总结、励志文、心理独白或电视剧脚本。

1. 使用第二人称有限视角（“你”）。禁止全知旁白，以及角色无法感知的并行场景。
2. 按真实顺序组织，但不逐项翻译 8 个 Slot。只使用弱连接推进：上完课、之后到公司、
   休息一会儿、训练结束后。FACT DATA 只写 SCHOOL 时，不补科目、作业、截止日或同学；
   只写 TRAINING 时，不补老师评价、具体失误、练习材料或不存在的进步。
3. events[*].event_brief 是当天实际发生的事件；有 choice_brief 时，那是玩家实际做出的选择。
   必须保留原意。effect_summary 只能轻量表现结果方向，不能据此发明夸奖、批评或新原因。
4. 普通日子可以没有主线、高潮、主题、成长、冲突或感悟。事实少就写短；事实多时选择性
   展开，不为连接或篇幅补剧情。不要用总结段把整天强行解释成某种意义。
5. 对白少量、短、低风险，只呈现已有互动；不得新增约定、未来计划、评价、背景或关系变化。
6. Character Guidance 只约束已有 NPC 如何表现，不证明 NPC 主动关心、记得表现或特别注意玩家。
7. 身体状态以普通行为轻量表现；不得补新症状。生理期仅在当天确有意义时写。月评只写 FACT
   DATA 支持的结果，不自行补老师反应或精确评价过程。
8. 不提前知道第二天，不写明天安排、未来事件或 settlement 之后的事实。结尾停在当天一个
   具体动作或生活节点即可，不要“今天没什么特别的”“不知道明天会怎样”式总结。
9. 纯正文：无标题、日期、Day 编号、Markdown、列表、内部字段或系统术语。"""


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
