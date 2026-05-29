from __future__ import annotations

from typing import Optional, Dict, Any
import json
import threading
import random
import re
from pathlib import Path
from datetime import datetime, timedelta

import flet as ft
from loguru import logger

from core.config import AppConfig
from core.engine import TurnEngine
from core.llm import LLMError, get_llm_provider
from core.models import GameState, Choice
from core.storage import SaveStorage
from core.action_validator import ActionBlockedError
from core.character_validator import validate_character_input, CharacterValidationError
from core.relationship_system import public_relationship_label, is_cp_eligible
from core.time_system import compute_age_group
from core.weekly_plan import compose_action_with_weekly_plan, normalize_weekly_plan_keys, weekly_plan_context, weekly_plan_options, weekly_plan_summary


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def icon(name: str):
    return getattr(ft.Icons, name, None)


def asset(path: str) -> str:
    return path.replace("\\", "/")


def asset_exists(path: str) -> bool:
    try:
        return (PROJECT_ROOT / "assets" / path).exists()
    except Exception:
        return False


def icon_src(name: str) -> str:
    ui_path = f"icons/ui/{name}.png"
    old_path = f"icons/{name}.png"
    return asset(ui_path if asset_exists(ui_path) else old_path)


def icon_image(name: str, size: int = 24, opacity: float = 1.0) -> ft.Image:
    return ft.Image(src=icon_src(name), width=size, height=size, fit="contain", opacity=opacity)


def avatar_src_from_character(character: Dict[str, Any] | None) -> str:
    if isinstance(character, dict):
        avatar = str(character.get("avatar") or "").strip()
        if avatar and asset_exists(avatar):
            return asset(avatar)
        seed_text = str(character.get("艺名") or character.get("本名") or character.get("姓名") or "starlight")
    else:
        seed_text = "starlight"
    idx = (sum(ord(ch) for ch in seed_text) % 36) + 1
    return asset(f"avatars/avatar_{idx:03d}.png")


def flag_code_from_nationality(nationality: str) -> str:
    text = str(nationality or "").strip().lower()
    if any(x in text for x in ["中国", "china", "chinese", "cn", "大陆"]):
        return "cn"
    if any(x in text for x in ["韩国", "korea", "korean", "kr", "韩"]):
        return "kr"
    if any(x in text for x in ["日本", "japan", "japanese", "jp", "日"]):
        return "jp"
    if any(x in text for x in ["泰国", "thailand", "thai", "th"]):
        return "th"
    if any(x in text for x in ["美国", "usa", "american", "us", "u.s."]):
        return "us"
    if any(x in text for x in ["海外", "国际", "global", "多国"]):
        return "global"
    return "unknown"


def flag_src_from_nationality(nationality: str) -> str:
    code = flag_code_from_nationality(nationality)
    return asset(f"icons/flags/{code}.png")

def glass_color(opacity: float = 0.72) -> str:
    return ft.Colors.with_opacity(opacity, ft.Colors.WHITE)


FONT_CN = "Microsoft YaHei UI"
FONT_EN = "Arial"
FONT_KO = "Malgun Gothic"

C = {
    "bg_top": "#FBFCFF",
    "bg_mid": "#F8F2FA",
    "bg_low": "#F3F8F5",
    "card": "#FFFFFF",
    "ink": "#3D4A5C",
    "sub": "#728197",
    "dai": "#536B89",
    "lavender": "#9A8FC4",
    "lotus": "#D9C2E6",
    "jade": "#93C9B7",
    "celadon": "#CFE8D5",
    "rouge": "#D86B7A",
    "peach": "#F7B7B2",
    "apricot": "#F2C982",
    "line": "#E9EAF2",
}


__all__ = [
    "Optional",
    "Dict",
    "Any",
    "json",
    "threading",
    "random",
    "re",
    "Path",
    "datetime",
    "timedelta",
    "ft",
    "logger",
    "AppConfig",
    "TurnEngine",
    "LLMError",
    "get_llm_provider",
    "GameState",
    "Choice",
    "SaveStorage",
    "ActionBlockedError",
    "validate_character_input",
    "CharacterValidationError",
    "public_relationship_label",
    "is_cp_eligible",
    "compute_age_group",
    "compose_action_with_weekly_plan",
    "normalize_weekly_plan_keys",
    "weekly_plan_context",
    "weekly_plan_options",
    "weekly_plan_summary",
    "PROJECT_ROOT",
    "icon",
    "asset",
    "asset_exists",
    "icon_src",
    "icon_image",
    "avatar_src_from_character",
    "flag_code_from_nationality",
    "flag_src_from_nationality",
    "glass_color",
    "FONT_CN",
    "FONT_EN",
    "FONT_KO",
    "C",
]

