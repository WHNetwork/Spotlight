from __future__ import annotations

import json
import re
from typing import Dict, List
import httpx
from loguru import logger
from core.config import AppConfig
from core.models import TurnResponse, Choice


class LLMError(RuntimeError):
    pass


def _extract_assistant_content(data: dict, provider_name: str) -> str:
    """统一提取 assistant content；三家 Provider 完全一致。

    content 必须为非空 str（strip 后非空），否则明确抛 LLMError；
    正常返回 content.strip()。不做任何 fallback / 占位 / 文学后处理。
    """
    try:
        content = data["choices"][0]["message"]["content"]
    except Exception as exc:
        raise LLMError(f"{provider_name} 返回格式异常：{data}") from exc
    if not isinstance(content, str) or not content.strip():
        raise LLMError(f"{provider_name} 返回空 assistant content。")
    return content.strip()


class BaseProvider:
    def generate(self, messages: List[Dict[str, str]], model: str | None = None, json_mode: bool = True) -> str:
        raise NotImplementedError


class DeepSeekProvider(BaseProvider):
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def generate(self, messages: List[Dict[str, str]], model: str | None = None, json_mode: bool = True) -> str:
        api_key = self.config.get_api_key_fallback()
        if not api_key:
            raise LLMError("没有找到 DeepSeek API Key。请在设置页填写 API Key，或设置环境变量 DEEPSEEK_API_KEY。")

        actual_model = model or self.config.custom_model
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": actual_model,
            "messages": messages,
            "temperature": 0.85,
            "stream": False,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        logger.info(f"Calling DeepSeek: {url}, model={actual_model}")
        return self._post_chat(url, headers, payload, provider_name="DeepSeek")

    def _post_chat(self, url: str, headers: dict, payload: dict, provider_name: str) -> str:
        try:
            with httpx.Client(timeout=self.config.timeout_seconds) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            raise LLMError(f"{provider_name} HTTP 错误：{exc.response.status_code} {exc.response.text}") from exc
        except Exception as exc:
            raise LLMError(f"{provider_name} 调用失败：{exc}") from exc

        content = _extract_assistant_content(data, provider_name)
        preview = content.replace("\n", " ")[:260]
        logger.info(f"{provider_name} returned content: chars={len(content)}, preview={preview}")
        return content


class XiaomiMiMoProvider(BaseProvider):
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def generate(self, messages: List[Dict[str, str]], model: str | None = None, json_mode: bool = True) -> str:
        api_key = self.config.get_mimo_api_key_fallback()
        if not api_key:
            raise LLMError("没有找到 Xiaomi MiMo API Key。请在设置页填写 MiMo API Key，或设置环境变量 MIMO_API_KEY。")

        actual_model = model or self.config.mimo_custom_model
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": actual_model,
            "messages": messages,
            "max_completion_tokens": 4096,
            "temperature": 0.85,
            "top_p": 0.95,
            "stream": False,
            "thinking": {"type": "disabled"},
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        url = self.config.mimo_base_url.rstrip("/") + "/chat/completions"
        logger.info(f"Calling Xiaomi MiMo: {url}, model={actual_model}")

        try:
            with httpx.Client(timeout=self.config.timeout_seconds) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            raise LLMError(f"Xiaomi MiMo HTTP 错误：{exc.response.status_code} {exc.response.text}") from exc
        except Exception as exc:
            raise LLMError(f"Xiaomi MiMo 调用失败：{exc}") from exc

        content = _extract_assistant_content(data, "Xiaomi MiMo")
        preview = content.replace("\n", " ")[:260]
        logger.info(f"Xiaomi MiMo returned content: chars={len(content)}, preview={preview}")
        return content


class GLMProvider(BaseProvider):
    """智谱 GLM（普通开放平台，OpenAI-compatible Chat Completions）。

    只负责 transport：messages → GLM API → assistant content 字符串。
    不接入 Coding Plan endpoint；不返回 reasoning_content；
    不做任何文本后处理（除与现有 Provider 一致的 .strip 级别保持）。
    """

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def generate(self, messages: List[Dict[str, str]], model: str | None = None, json_mode: bool = True) -> str:
        api_key = self.config.get_glm_api_key_fallback()
        if not api_key:
            raise LLMError("没有找到 GLM API Key。请设置环境变量 GLM_API_KEY，或按 DeepSeek/MiMo 同样的方式保存。")

        actual_model = model or self.config.glm_model
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": actual_model,
            "messages": messages,
            "temperature": 0.85,
            "stream": False,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        url = self.config.glm_base_url.rstrip("/") + "/chat/completions"
        logger.info(f"Calling GLM: {url}, model={actual_model}")

        try:
            with httpx.Client(timeout=self.config.timeout_seconds) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            raise LLMError(f"GLM HTTP 错误：{exc.response.status_code} {exc.response.text}") from exc
        except Exception as exc:
            raise LLMError(f"GLM 调用失败：{exc}") from exc

        content = _extract_assistant_content(data, "GLM")
        preview = content.replace("\n", " ")[:260]
        logger.info(f"GLM returned content: chars={len(content)}, preview={preview}")
        return content


def get_llm_provider(config: AppConfig, provider_name: str | None = None) -> BaseProvider:
    """窄接口：可显式指定 provider（"deepseek" / "mimo" / "glm"）。

    provider_name 为 None 时保持既有行为（按 config.provider 选择），
    不改变任何共享配置；model 名称仍由调用方从 config 读取。
    未知 provider 明确抛 LLMError，不做 generic fallback。
    """
    chosen = provider_name or config.provider
    if chosen == "glm":
        return GLMProvider(config)
    if chosen == "mimo":
        return XiaomiMiMoProvider(config)
    if chosen == "deepseek":
        return DeepSeekProvider(config)
    raise LLMError(f"unsupported provider: {chosen}")

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
                fixed.append({
                    "name": str(item.get("name") or item.get("角色") or f"人物{i+1}"),
                    "reaction": _stringify_text(item.get("reaction") or item.get("反应") or item.get("text") or item),
                    "role": item.get("role") or item.get("身份") or item.get("关系"),
                    "age": item.get("age") or item.get("年龄"),
                })
            else:
                fixed.append({"name": f"人物{i+1}", "reaction": _stringify_text(item)})
        data["npc_reactions"] = fixed

    return data


def _clean_fenced_json(raw: str) -> str:
    text = str(raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]
    return text


def _scan_json_string_value(text: str, key: str) -> str:
    """Extract a string value from malformed JSON.

    It handles model outputs like:
    "narrative": "他说："今天不休息？"她问。", "public_summary": ...
    where inner quotes were not escaped.
    """
    key_pat = '"' + key + '"'
    pos = text.find(key_pat)
    if pos < 0:
        return ""
    colon = text.find(":", pos + len(key_pat))
    if colon < 0:
        return ""
    i = colon + 1
    n = len(text)
    while i < n and text[i].isspace():
        i += 1
    if i >= n:
        return ""

    if text[i] != '"':
        j = i
        while j < n:
            if text[j] == "," and re.match(r'\s*"[\w\u4e00-\u9fff_]+":', text[j + 1:]):
                break
            if text[j] == "}" and j > i:
                break
            j += 1
        return text[i:j].strip().strip('"')

    i += 1
    out = []
    esc = False
    while i < n:
        ch = text[i]
        if esc:
            if ch == "n":
                out.append("\n")
            elif ch == "t":
                out.append("\t")
            elif ch == "r":
                out.append("\r")
            else:
                out.append(ch)
            esc = False
            i += 1
            continue

        if ch == "\\":
            esc = True
            i += 1
            continue

        if ch == '"':
            j = i + 1
            while j < n and text[j].isspace():
                j += 1
            if j >= n:
                break
            tail = text[j:]
            if tail.startswith("}") or re.match(r',\s*"[\w\u4e00-\u9fff_]+":', tail):
                break
            # Inner unescaped quote inside prose/dialogue.
            out.append(ch)
            i += 1
            continue

        out.append(ch)
        i += 1

    return "".join(out).strip()


def _extract_balanced_value_after_key(text: str, key: str):
    key_pat = '"' + key + '"'
    pos = text.find(key_pat)
    if pos < 0:
        return None
    colon = text.find(":", pos + len(key_pat))
    if colon < 0:
        return None
    i = colon + 1
    n = len(text)
    while i < n and text[i].isspace():
        i += 1
    if i >= n:
        return None

    if text[i] == '"':
        return _scan_json_string_value(text, key)

    if text[i] not in "[{":
        j = i
        while j < n:
            if text[j] == "," and re.match(r'\s*"[\w\u4e00-\u9fff_]+":', text[j + 1:]):
                break
            if text[j] == "}" and j > i:
                break
            j += 1
        raw_value = text[i:j].strip()
        try:
            return json.loads(raw_value)
        except Exception:
            return raw_value.strip('"')

    open_ch = text[i]
    close_ch = "]" if open_ch == "[" else "}"
    depth = 0
    in_str = False
    esc = False
    j = i
    while j < n:
        ch = text[j]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                k = j + 1
                while k < n and text[k].isspace():
                    k += 1
                if k < n and text[k] not in [",", "}", "]", ":"]:
                    pass
                else:
                    in_str = False
            j += 1
            continue
        if ch == '"':
            in_str = True
        elif ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                raw_value = text[i:j + 1]
                try:
                    return json.loads(raw_value)
                except Exception:
                    return raw_value
        j += 1
    return None


def _split_choice_items(raw: str) -> list:
    if not raw:
        return []
    text = str(raw).strip()
    choices = []
    for match in re.finditer(r'\{(.*?)\}', text, flags=re.S):
        obj = match.group(1)
        obj_text = "{" + obj + "}"
        cid = _scan_json_string_value(obj_text, "id") or _scan_json_string_value(obj_text, "key")
        ctext = _scan_json_string_value(obj_text, "text") or _scan_json_string_value(obj_text, "content") or _scan_json_string_value(obj_text, "label")
        if ctext:
            choices.append({"id": cid or chr(ord("A") + min(len(choices), 4)), "text": ctext})
    if choices:
        return choices[:5]

    for cid, ctext in re.findall(r'["\']?([A-E])["\']?\s*[:.、]\s*["\']?([^"\n,，]+)', text):
        choices.append({"id": cid, "text": ctext.strip()})
    return choices[:5]


def _fallback_parse_turn_response_data(raw: str) -> dict:
    text = _clean_fenced_json(raw)

    narrative = (
        _scan_json_string_value(text, "narrative")
        or _scan_json_string_value(text, "推进情节")
        or _scan_json_string_value(text, "story")
        or _scan_json_string_value(text, "content")
        or _scan_json_string_value(text, "text")
    )
    public_summary = (
        _scan_json_string_value(text, "public_summary")
        or _scan_json_string_value(text, "summary")
        or _scan_json_string_value(text, "回合总结")
        or _scan_json_string_value(text, "本回合总结")
    )
    private_notes = _scan_json_string_value(text, "private_notes") or _scan_json_string_value(text, "private")

    choices_value = _extract_balanced_value_after_key(text, "choices")
    if choices_value is None:
        choices_value = _extract_balanced_value_after_key(text, "选项")
    if isinstance(choices_value, list):
        choices = choices_value
    else:
        choices = _split_choice_items(str(choices_value or ""))

    suggested = _extract_balanced_value_after_key(text, "suggested_diff")
    if not isinstance(suggested, dict):
        suggested = _extract_balanced_value_after_key(text, "diff")
    if not isinstance(suggested, dict):
        suggested = {}

    npc_value = _extract_balanced_value_after_key(text, "npc_reactions")
    npc_reactions = npc_value if isinstance(npc_value, list) else []

    new_flags = _extract_balanced_value_after_key(text, "new_flags")
    resolved_flags = _extract_balanced_value_after_key(text, "resolved_flags")

    return {
        "narrative": narrative,
        "public_summary": public_summary,
        "private_notes": private_notes,
        "choices": choices,
        "suggested_diff": suggested,
        "npc_reactions": npc_reactions,
        "new_flags": new_flags if isinstance(new_flags, list) else [],
        "resolved_flags": resolved_flags if isinstance(resolved_flags, list) else [],
    }


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
        logger.warning(f"Strict JSON parse failed, using tolerant parser: {exc}")
        try:
            data = _fallback_parse_turn_response_data(raw)
            if not _stringify_text(data.get("narrative")):
                raise ValueError("tolerant parser did not recover narrative")
        except Exception as fallback_exc:
            raise LLMError(f"无法解析模型 JSON：{exc}\n原始内容：{raw[:1000]}") from fallback_exc

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
