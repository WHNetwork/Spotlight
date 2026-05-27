from __future__ import annotations

import json
from typing import Dict, List
import httpx
from loguru import logger
from core.config import AppConfig
from core.models import TurnResponse, Choice

class LLMError(RuntimeError):
    pass

class BaseProvider:
    def generate(self, messages: List[Dict[str, str]], model: str | None = None) -> str:
        raise NotImplementedError

class MockProvider(BaseProvider):
    def generate(self, messages: List[Dict[str, str]], model: str | None = None) -> str:
        mock = {
            "narrative": "练习室的灯还亮着。你按照被系统校验后的行动推进，先把能做的事落在当前阶段里，而不是越过时间线去拿还不属于你的资源。",
            "npc_reactions": [{"name": "经纪人韩室长", "reaction": "她看了你一眼，提醒你先把眼前的考核做好。"}],
            "choices": [
                {"id": "A", "text": "按当前阶段继续推进。"},
                {"id": "B", "text": "找老师确认下一步训练重点。"},
                {"id": "C", "text": "先休息，观察身体状态。"},
                {"id": "D", "text": "和同期练习生沟通。"},
                {"id": "E", "text": "自定义行动"}
            ],
            "suggested_diff": {},
            "new_flags": [],
            "resolved_flags": [],
            "public_summary": "你把行动调整回当前阶段能够执行的范围。",
            "private_notes": "Mock 模式。"
        }
        return json.dumps(mock, ensure_ascii=False)

class DeepSeekProvider(BaseProvider):
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def generate(self, messages: List[Dict[str, str]], model: str | None = None) -> str:
        api_key = self.config.get_api_key_fallback()
        if not api_key:
            raise LLMError("没有找到 DeepSeek API Key。请在设置页填写，或使用 Mock 模式。")
        actual_model = model or self.config.custom_model
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": actual_model, "messages": messages, "temperature": 0.85, "stream": False}
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        logger.info(f"Calling DeepSeek: {url}, model={actual_model}")
        try:
            with httpx.Client(timeout=self.config.timeout_seconds) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            raise LLMError(f"DeepSeek HTTP 错误：{exc.response.status_code} {exc.response.text}") from exc
        except Exception as exc:
            raise LLMError(f"DeepSeek 调用失败：{exc}") from exc
        try:
            return data["choices"][0]["message"]["content"]
        except Exception as exc:
            raise LLMError(f"DeepSeek 返回格式异常：{data}") from exc

def parse_turn_response(raw: str) -> TurnResponse:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMError(f"无法解析模型 JSON：{exc}\n原始内容：{raw[:1000]}") from exc
    result = TurnResponse.model_validate(data)
    if not result.choices:
        result.choices = [
            Choice(id="A", text="继续观察"),
            Choice(id="B", text="主动行动"),
            Choice(id="C", text="找人商量"),
            Choice(id="D", text="暂时休息"),
            Choice(id="E", text="自定义行动"),
        ]
    return result
