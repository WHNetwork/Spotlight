# -*- coding: utf-8 -*-
"""
LLM Layer 2A：Global Writing Policy / Narrative Constitution。

架构约束（architectural invariant）：
    All future player-visible LLM prose must pass through this writing layer.
    Decision / classification / structured-judgment LLM calls are excluded.

正式 public API（其余为内部实现，不 export）。
依赖方向单向：orchestration/writing → core.llm / core.config。
"""
from orchestration.writing.policy import GLOBAL_WRITING_CONSTITUTION, WritingPolicyError
from orchestration.writing.provider_adapters import get_provider_writing_adapter
from orchestration.writing.prompt_builder import (
    WritingPromptBundle,
    build_writing_messages,
    generate_player_text,
)

__all__ = [
    "GLOBAL_WRITING_CONSTITUTION",
    "WritingPolicyError",
    "get_provider_writing_adapter",
    "WritingPromptBundle",
    "build_writing_messages",
    "generate_player_text",
]
