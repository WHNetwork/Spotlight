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

MIMO_WRITING_ADAPTER: str = """【Provider 写作适配（MIMO）】
1. 优先保持人物行为与既有关系连续性；一个小的经历只能产生同等量级的文本变化。
2. 不要为了柔和而泛滥使用：微微、轻轻、悄然、似乎、暖意、心底。
3. 人物允许普通、疲惫、尴尬、敷衍、没话说。
4. 没有重大内容时，允许平静、短一些。
5. 不要自动把一次 NPC 互动写成温暖的关系推进。
6. 避免每段最后一句进行情绪总结。"""

GLM_WRITING_ADAPTER: str = """【Provider 写作适配（GLM）】
1. 不要主动扩大剧情；一个小事实不要扩写成完整戏剧冲突。
2. 不要增加输入不存在的长期心理独白。
3. 不要为了文学性统一把对白润色成漂亮完整句。
4. 事实少时宁可短，不要自行补重大情节。
5. 每个场景只选择少量真正有效的生活细节。
6. 不要每段用总结句解释意义。"""

DEEPSEEK_WRITING_ADAPTER: str = """【Provider 写作适配（DeepSeek）】
1. 这是叙事写作，不是分析任务；不要解释为什么这样写。
2. 不要分析人物动机；不要把心理写成“因为 A，所以 B，因此 C”。
3. 情绪更多隐藏在动作、语气、选择里。
4. 不需要追求结构过度完整；现实场景允许没有明显起承转合。
5. 一句话可以没有得到漂亮回应。
6. 禁止输出推理过程。"""

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
