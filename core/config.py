from __future__ import annotations

import json
import os
from pathlib import Path
from dotenv import load_dotenv
try:
    import keyring
except Exception:  # keyring may be unavailable in minimal test environments
    keyring = None

APP_NAME = "kpop_idol_simulator"
CONFIG_DIR = Path.home() / ".kpop_idol_simulator"
CONFIG_PATH = CONFIG_DIR / "config.json"


class AppConfig:
    def __init__(self) -> None:
        load_dotenv()
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.base_url = "https://api.deepseek.com"
        self.model_policy = "auto"
        self.flash_model = "deepseek-v4-flash"
        self.pro_model = "deepseek-v4-pro"
        self.custom_model = "deepseek-chat"
        self.timeout_seconds = 120
        self.load()

    def load(self) -> None:
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                self.base_url = data.get("base_url", self.base_url)
                self.model_policy = data.get("model_policy", self.model_policy)
                self.flash_model = data.get("flash_model", self.flash_model)
                self.pro_model = data.get("pro_model", self.pro_model)
                self.custom_model = data.get("custom_model", data.get("model", self.custom_model))
                self.timeout_seconds = int(data.get("timeout_seconds", self.timeout_seconds))
            except Exception:
                pass

    def save(self, base_url: str, model_policy: str, flash_model: str, pro_model: str, custom_model: str, timeout_seconds: int = 120) -> None:
        self.base_url = base_url.strip() or self.base_url
        self.model_policy = model_policy.strip() or self.model_policy
        self.flash_model = flash_model.strip() or self.flash_model
        self.pro_model = pro_model.strip() or self.pro_model
        self.custom_model = custom_model.strip() or self.custom_model
        self.timeout_seconds = int(timeout_seconds)
        CONFIG_PATH.write_text(json.dumps({
            "base_url": self.base_url,
            "model_policy": self.model_policy,
            "flash_model": self.flash_model,
            "pro_model": self.pro_model,
            "custom_model": self.custom_model,
            "timeout_seconds": self.timeout_seconds,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    def model_for_tier(self, tier: str) -> str:
        if self.model_policy == "flash":
            return self.flash_model
        if self.model_policy == "pro":
            return self.pro_model
        if self.model_policy == "custom":
            return self.custom_model
        return self.pro_model if tier == "pro" else self.flash_model

    def get_api_key(self) -> str:
        env_key = os.getenv("DEEPSEEK_API_KEY")
        if env_key:
            return env_key
        try:
            if keyring is None:
                return ""
            return keyring.get_password(APP_NAME, "DEEPSEEK_API_KEY") or ""
        except Exception:
            return ""

    def set_api_key(self, api_key: str) -> None:
        api_key = api_key.strip()
        if not api_key:
            return
        try:
            if keyring is None:
                raise RuntimeError("keyring unavailable")
            keyring.set_password(APP_NAME, "DEEPSEEK_API_KEY", api_key)
        except Exception:
            fallback = CONFIG_DIR / ".api_key"
            fallback.write_text(api_key, encoding="utf-8")

    def get_api_key_fallback(self) -> str:
        key = self.get_api_key()
        if key:
            return key
        fallback = CONFIG_DIR / ".api_key"
        if fallback.exists():
            return fallback.read_text(encoding="utf-8").strip()
        return ""
