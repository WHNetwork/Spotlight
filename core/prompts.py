from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Any
from loguru import logger
from core.models import GameState, RouteInfo, SystemEvent

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SYSTEM_PROMPT_PATH = DATA_DIR / "system_prompt.md"


def _read_md(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def load_system_prompt() -> str:
    if SYSTEM_PROMPT_PATH.exists():
        return _read_md(SYSTEM_PROMPT_PATH)
    return ""


def list_prompt_modules() -> List[str]:
    return []


POLISH_SYSTEM_PROMPT = """请只对下面文字做文风润色，不改变剧情、不改变人物关系、不新增事件。

润色目标：去除 AI 味，让文字更自然、细腻、真实、有温度。

具体要求：
1. 删除剧情总结式句子，改成具体场景和动作。
2. 删除模板化抒情（尤其是"这一刻、终于明白、像被击中、心脏漏拍、救赎、破碎、命运、光、全世界安静"等表达）。
3. 降低对话解释功能，不要让人物把内心和主题直接说透。
4. 增加生活细节和身体细节（衣角、汗、灯光、手机、鞋带、镜子、走廊声音、呼吸、停顿）。
5. 保持克制，不要过度煽情，不要频繁哭、抱、崩溃。
6. 保持原文信息量，只优化语言质感和叙事流动性。

请直接输出润色后的正文，不要解释修改原因。"""


def polish_narrative(original: str, provider, flash_model: str) -> str:
    if not original or not original.strip():
        return original
    try:
        messages = [
            {"role": "system", "content": POLISH_SYSTEM_PROMPT},
            {"role": "user", "content": original},
        ]
        result = provider.generate(messages, model=flash_model, json_mode=False)
        if result and result.strip():
            return result.strip()
    except Exception:
        logger.exception("polish_narrative failed")
    return original
