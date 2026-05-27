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


class DeepSeekProvider(BaseProvider):
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def generate(self, messages: List[Dict[str, str]], model: str | None = None) -> str:
        api_key = self.config.get_api_key_fallback()
        if not api_key:
            raise LLMError("没有找到 DeepSeek API Key。请在设置页填写 API Key，或设置环境变量 DEEPSEEK_API_KEY。")

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
