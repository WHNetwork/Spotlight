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
            content = data["choices"][0]["message"]["content"]
            preview = str(content).replace("\n", " ")[:260]
            logger.info(f"DeepSeek returned content: chars={len(str(content))}, preview={preview}")
            return content
        except Exception as exc:
            raise LLMError(f"DeepSeek 返回格式异常：{data}") from exc


def _stringify_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content") or item.get("reaction") or item.get("body") or ""
                if text:
                    parts.append(str(text).strip())
            elif item is not None:
                parts.append(str(item).strip())
        return "\n".join(p for p in parts if p)
    if isinstance(value, dict):
        for key in ["text", "content", "body", "narrative", "正文", "剧情", "推进情节"]:
            if key in value and value[key]:
                return _stringify_text(value[key])
        return "\n".join(str(v).strip() for v in value.values() if str(v).strip())
    return str(value).strip()


def _normalize_turn_response_data(data: dict) -> dict:
    if not isinstance(data, dict):
        return data

    if not _stringify_text(data.get("narrative")):
        for key in [
            "推进情节", "本回合剧情", "剧情", "正文", "story", "main_story",
            "main_text", "content", "text", "response", "narration",
        ]:
            if key in data and _stringify_text(data.get(key)):
                data["narrative"] = _stringify_text(data.get(key))
                break

    if not _stringify_text(data.get("public_summary")):
        for key in ["回合总结", "summary", "public", "publicSummary", "本回合总结"]:
            if key in data and _stringify_text(data.get(key)):
                data["public_summary"] = _stringify_text(data.get(key))
                break

    if "choices" not in data:
        for key in ["选项", "下一步选择", "options", "actions"]:
            if key in data:
                data["choices"] = data[key]
                break

    if isinstance(data.get("choices"), dict):
        data["choices"] = [
            {"id": str(k), "text": _stringify_text(v)}
            for k, v in data["choices"].items()
        ]
    elif isinstance(data.get("choices"), list):
        fixed = []
        default_ids = ["A", "B", "C", "D", "E"]
        for i, item in enumerate(data["choices"]):
            if isinstance(item, dict):
                fixed.append({"id": str(item.get("id") or item.get("key") or default_ids[min(i, 4)]), "text": _stringify_text(item.get("text") or item.get("content") or item.get("label") or item)})
            else:
                fixed.append({"id": default_ids[min(i, 4)], "text": _stringify_text(item)})
        data["choices"] = fixed

    if "suggested_diff" not in data:
        for key in ["diff", "属性变化", "状态变化", "attribute_changes", "suggestedDiff"]:
            if key in data and isinstance(data[key], dict):
                data["suggested_diff"] = data[key]
                break

    # Some models return NPC reactions as strings. Normalize to the expected schema.
    if isinstance(data.get("npc_reactions"), list):
        fixed = []
        for i, item in enumerate(data["npc_reactions"]):
            if isinstance(item, dict):
                fixed.append({"name": str(item.get("name") or item.get("角色") or f"人物{i+1}"), "reaction": _stringify_text(item.get("reaction") or item.get("反应") or item.get("text") or item)})
            else:
                fixed.append({"name": f"人物{i+1}", "reaction": _stringify_text(item)})
        data["npc_reactions"] = fixed

    return data


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

    data = _normalize_turn_response_data(data)
    result = TurnResponse.model_validate(data)
    logger.info(
        f"Parsed TurnResponse: narrative_chars={len(str(result.narrative or ''))}, "
        f"summary_chars={len(str(result.public_summary or ''))}, "
        f"choices={len(result.choices)}"
    )

    if not str(result.narrative or "").strip():
        fallback_parts = []
        if result.public_summary.strip():
            fallback_parts.append(result.public_summary.strip())
        for reaction in result.npc_reactions[:3]:
            if reaction.reaction.strip():
                fallback_parts.append(reaction.reaction.strip())
        result.narrative = "\n".join(fallback_parts).strip() or "练习室的灯还亮着。你把今天的状态写进心里，然后等待下一步选择。"

    if not result.choices:
        result.choices = [
            Choice(id="A", text="继续观察"),
            Choice(id="B", text="主动行动"),
            Choice(id="C", text="找人商量"),
            Choice(id="D", text="暂时休息"),
            Choice(id="E", text="自定义行动"),
        ]
    return result
