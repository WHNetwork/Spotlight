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

        # Active provider.
        self.provider = "deepseek"  # deepseek | mimo

        # DeepSeek settings. Keep old field names for backward compatibility.
        self.base_url = "https://api.deepseek.com"
        self.flash_model = "deepseek-v4-flash"
        self.pro_model = "deepseek-v4-pro"
        self.custom_model = "deepseek-chat"

        # Xiaomi MiMo settings. MiMo OpenAI-compatible endpoint is:
        # https://api.xiaomimimo.com/v1/chat/completions
        self.mimo_base_url = "https://api.xiaomimimo.com/v1"
        self.mimo_flash_model = "mimo-v2.5"
        self.mimo_pro_model = "mimo-v2.5-pro"
        self.mimo_custom_model = "mimo-v2.5-pro"

        # GLM (Zhipu Open Platform) settings. OpenAI-compatible endpoint:
        # https://open.bigmodel.cn/api/paas/v4/chat/completions
        self.glm_base_url = "https://open.bigmodel.cn/api/paas/v4/"
        self.glm_model = "glm-5.2"  # legacy field, kept for backward compat
        self.glm_flash_model = "glm-4.7-flash"
        self.glm_pro_model = "glm-5.2"
        self.glm_custom_model = "glm-5.2"

        # New default is "flash". "auto" is still recognized on load for
        # legacy config files, but the UI never exposes it.
        self.model_policy = "flash"
        self.timeout_seconds = 120
        self.load()

    def load(self) -> None:
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                self.provider = data.get("provider", self.provider)

                self.base_url = data.get("base_url", data.get("deepseek_base_url", self.base_url))
                self.flash_model = data.get("flash_model", data.get("deepseek_flash_model", self.flash_model))
                self.pro_model = data.get("pro_model", data.get("deepseek_pro_model", self.pro_model))
                self.custom_model = data.get("custom_model", data.get("model", data.get("deepseek_custom_model", self.custom_model)))

                self.mimo_base_url = data.get("mimo_base_url", self.mimo_base_url)
                self.mimo_flash_model = data.get("mimo_flash_model", self.mimo_flash_model)
                self.mimo_pro_model = data.get("mimo_pro_model", self.mimo_pro_model)
                self.mimo_custom_model = data.get("mimo_custom_model", self.mimo_custom_model)

                self.glm_base_url = data.get("glm_base_url", self.glm_base_url)
                self.glm_model = data.get("glm_model", self.glm_model)
                # GLM 3-tier migration: a legacy config that only had glm_model
                # seeds glm_pro_model / glm_custom_model from it.
                legacy_glm = data.get("glm_model")
                self.glm_flash_model = data.get("glm_flash_model", "glm-4.7-flash")
                self.glm_pro_model = data.get("glm_pro_model") or legacy_glm or "glm-5.2"
                self.glm_custom_model = data.get("glm_custom_model") or legacy_glm or "glm-5.2"

                self.model_policy = data.get("model_policy", self.model_policy)
                self.timeout_seconds = int(data.get("timeout_seconds", self.timeout_seconds))
            except Exception:
                pass

    def save(
        self,
        base_url: str | None = None,
        model_policy: str | None = None,
        flash_model: str | None = None,
        pro_model: str | None = None,
        custom_model: str | None = None,
        timeout_seconds: int = 120,
        provider: str | None = None,
        mimo_base_url: str | None = None,
        mimo_flash_model: str | None = None,
        mimo_pro_model: str | None = None,
        mimo_custom_model: str | None = None,
        glm_base_url: str | None = None,
        glm_model: str | None = None,
        glm_flash_model: str | None = None,
        glm_pro_model: str | None = None,
        glm_custom_model: str | None = None,
    ) -> None:
        if provider is not None:
            provider = provider.strip().lower()
            self.provider = provider if provider in {"deepseek", "mimo", "glm"} else "deepseek"

        if base_url is not None:
            self.base_url = base_url.strip() or self.base_url
        if model_policy is not None:
            policy = model_policy.strip() or self.model_policy
            self.model_policy = policy if policy in {"auto", "flash", "pro", "custom"} else "auto"
        if flash_model is not None:
            self.flash_model = flash_model.strip() or self.flash_model
        if pro_model is not None:
            self.pro_model = pro_model.strip() or self.pro_model
        if custom_model is not None:
            self.custom_model = custom_model.strip() or self.custom_model

        if mimo_base_url is not None:
            self.mimo_base_url = mimo_base_url.strip() or self.mimo_base_url
        if mimo_flash_model is not None:
            self.mimo_flash_model = mimo_flash_model.strip() or self.mimo_flash_model
        if mimo_pro_model is not None:
            self.mimo_pro_model = mimo_pro_model.strip() or self.mimo_pro_model
        if mimo_custom_model is not None:
            self.mimo_custom_model = mimo_custom_model.strip() or self.mimo_custom_model

        if glm_base_url is not None:
            self.glm_base_url = glm_base_url.strip() or self.glm_base_url
        if glm_model is not None:
            self.glm_model = glm_model.strip() or self.glm_model
        if glm_flash_model is not None:
            self.glm_flash_model = glm_flash_model.strip() or self.glm_flash_model
        if glm_pro_model is not None:
            self.glm_pro_model = glm_pro_model.strip() or self.glm_pro_model
        if glm_custom_model is not None:
            self.glm_custom_model = glm_custom_model.strip() or self.glm_custom_model

        self.timeout_seconds = int(timeout_seconds)
        CONFIG_PATH.write_text(json.dumps({
            "provider": self.provider,
            "base_url": self.base_url,
            "flash_model": self.flash_model,
            "pro_model": self.pro_model,
            "custom_model": self.custom_model,
            "mimo_base_url": self.mimo_base_url,
            "mimo_flash_model": self.mimo_flash_model,
            "mimo_pro_model": self.mimo_pro_model,
            "mimo_custom_model": self.mimo_custom_model,
            "glm_base_url": self.glm_base_url,
            "glm_model": self.glm_model,
            "glm_flash_model": self.glm_flash_model,
            "glm_pro_model": self.glm_pro_model,
            "glm_custom_model": self.glm_custom_model,
            "model_policy": self.model_policy,
            "timeout_seconds": self.timeout_seconds,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    def provider_label(self) -> str:
        if self.provider == "mimo":
            return "Xiaomi MiMo"
        if self.provider == "glm":
            return "GLM"
        return "DeepSeek"

    def active_base_url(self) -> str:
        if self.provider == "mimo":
            return self.mimo_base_url
        if self.provider == "glm":
            return self.glm_base_url
        return self.base_url

    def model_for_provider(self, provider_name: str, tier: str = "flash") -> str:
        """Return the model for a given provider + tier (flash/pro/custom).

        ``tier`` of 'auto' is treated as the caller-supplied tier for legacy
        compatibility. Does not mutate any shared provider config.
        """
        name = (provider_name or self.provider).strip().lower()
        if name == "deepseek":
            flash, pro, custom = self.flash_model, self.pro_model, self.custom_model
        elif name == "mimo":
            flash, pro, custom = self.mimo_flash_model, self.mimo_pro_model, self.mimo_custom_model
        elif name == "glm":
            flash, pro, custom = self.glm_flash_model, self.glm_pro_model, self.glm_custom_model
        else:
            raise ValueError(f"unsupported provider: {name}")
        t = (tier or "flash").strip().lower()
        if t == "pro":
            return pro
        if t == "custom":
            return custom
        return flash

    def model_for_tier(self, tier: str) -> str:
        policy = self.model_policy
        if policy in {"flash", "pro", "custom"}:
            return self.model_for_provider(self.provider, policy)
        # legacy 'auto': the caller-supplied tier decides
        return self.model_for_provider(self.provider, tier or "flash")

    # DeepSeek API key: keep legacy names for compatibility.
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

    # Xiaomi MiMo API key.
    def get_mimo_api_key(self) -> str:
        env_key = os.getenv("MIMO_API_KEY") or os.getenv("XIAOMI_MIMO_API_KEY")
        if env_key:
            return env_key
        try:
            if keyring is None:
                return ""
            return keyring.get_password(APP_NAME, "MIMO_API_KEY") or ""
        except Exception:
            return ""

    def set_mimo_api_key(self, api_key: str) -> None:
        api_key = api_key.strip()
        if not api_key:
            return
        try:
            if keyring is None:
                raise RuntimeError("keyring unavailable")
            keyring.set_password(APP_NAME, "MIMO_API_KEY", api_key)
        except Exception:
            fallback = CONFIG_DIR / ".mimo_api_key"
            fallback.write_text(api_key, encoding="utf-8")

    def get_mimo_api_key_fallback(self) -> str:
        key = self.get_mimo_api_key()
        if key:
            return key
        fallback = CONFIG_DIR / ".mimo_api_key"
        if fallback.exists():
            return fallback.read_text(encoding="utf-8").strip()
        return ""

    # GLM (Zhipu Open Platform) API key.
    def get_glm_api_key(self) -> str:
        env_key = os.getenv("GLM_API_KEY") or os.getenv("ZHIPU_API_KEY")
        if env_key:
            return env_key
        try:
            if keyring is None:
                return ""
            return keyring.get_password(APP_NAME, "GLM_API_KEY") or ""
        except Exception:
            return ""

    def set_glm_api_key(self, api_key: str) -> None:
        api_key = api_key.strip()
        if not api_key:
            return
        try:
            if keyring is None:
                raise RuntimeError("keyring unavailable")
            keyring.set_password(APP_NAME, "GLM_API_KEY", api_key)
        except Exception:
            fallback = CONFIG_DIR / ".glm_api_key"
            fallback.write_text(api_key, encoding="utf-8")

    def get_glm_api_key_fallback(self) -> str:
        key = self.get_glm_api_key()
        if key:
            return key
        fallback = CONFIG_DIR / ".glm_api_key"
        if fallback.exists():
            return fallback.read_text(encoding="utf-8").strip()
        return ""

    def get_active_api_key_fallback(self) -> str:
        if self.provider == "mimo":
            return self.get_mimo_api_key_fallback()
        if self.provider == "glm":
            return self.get_glm_api_key_fallback()
        return self.get_api_key_fallback()
