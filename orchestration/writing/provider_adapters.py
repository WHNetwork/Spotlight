# -*- coding: utf-8 -*-
"""
Provider-specific Writing Adapters（LLM Layer 2A）。

只修正各模型在本项目中的常见写作偏向；约 80% 规则来自 GLOBAL_WRITING_CONSTITUTION。
Adapter 是 immutable 字符串常量，任务层不得运行时修改。
provider_name 必须使用项目真实 provider identifier。

当前项目真实 identifier：mimo、deepseek、glm（core/config.py + core/llm.py）。
"""
from __future__ import annotations

from typing import Mapping

from orchestration.writing.policy import WritingPolicyError

MIMO_WRITING_ADAPTER: str = """【Provider 执行提醒（MiMo）】
严格服从共享宪法，不得通过补新事实提高连贯性。普通日子不要自动写成淡淡感伤的
散文，也不要追加总结、意义或“明天会怎样”的尾声。事实少就自然写短。"""

GLM_WRITING_ADAPTER: str = """【Provider 执行提醒（GLM）】
严格服从共享宪法。不要把日常写成影视剧或抒情散文，不用灯光、镜头、停顿制造戏剧感；
不要扩展人物关系，也不要用大段心理总结替代已有事实。"""

DEEPSEEK_WRITING_ADAPTER: str = """【Provider 执行提醒（DeepSeek）】
严格服从共享宪法。不要为获得逻辑闭环而补背景、动机或因果链，不要解释人物为什么必然
这样做；保留普通生活里的空白、不完整回应和没有结论的片段。只输出正文。"""

# 真实 provider identifier → adapter（GLM 已正式接入，identifier = "glm"）。
_PROVIDER_ADAPTERS: Mapping[str, str] = {
    "mimo": MIMO_WRITING_ADAPTER,
    "deepseek": DEEPSEEK_WRITING_ADAPTER,
    "glm": GLM_WRITING_ADAPTER,
}


def get_provider_writing_adapter(provider_name: str) -> str:
    """返回指定 provider 的写作适配规则（显式选择；未知 provider 明确失败）。"""
    adapter = _PROVIDER_ADAPTERS.get(provider_name)
    if adapter is None:
        raise WritingPolicyError(f"unsupported provider for narrative writing: {provider_name}")
    return adapter
