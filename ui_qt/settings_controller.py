from __future__ import annotations

from typing import Optional

from loguru import logger
from PySide6.QtCore import QObject, Property, QRunnable, QThreadPool, Qt, Signal, Slot

from core.config import AppConfig
from core.llm import get_llm_provider

_PROVIDER_LABELS = {"deepseek": "DeepSeek", "mimo": "Xiaomi MiMo", "glm": "GLM"}


def _label(provider: str) -> str:
    return _PROVIDER_LABELS.get(provider, provider)


class _TestConfig:
    """Throwaway duck-typed config for testing the *current form* values.

    Only exposes the attributes/methods the Provider classes read (base_url,
    mimo_base_url, glm_base_url, timeout_seconds, get_*_api_key_fallback).
    Nothing is persisted; this object lives only for the single test call.
    """

    def __init__(self, base_url: str, timeout: int, api_key: str) -> None:
        self.base_url = base_url
        self.mimo_base_url = base_url
        self.glm_base_url = base_url
        self.timeout_seconds = timeout
        self._api_key = api_key

    def get_api_key_fallback(self) -> str:
        return self._api_key

    def get_mimo_api_key_fallback(self) -> str:
        return self._api_key

    def get_glm_api_key_fallback(self) -> str:
        return self._api_key


class _TestModelTask(QRunnable):
    """One short model test off the UI thread, using a form-value snapshot.

    The snapshot (provider/base_url/timeout/api_key/model) is resolved on the
    UI thread from plain Python values, so the worker never touches QML objects
    or the shared AppConfig. Nothing is persisted during a test.
    """

    def __init__(self, snapshot: dict, done_signal) -> None:
        super().__init__()
        self._snap = snapshot
        self._done = done_signal

    def run(self) -> None:  # noqa: D401 (QRunnable entry)
        try:
            cfg = _TestConfig(self._snap["base_url"], self._snap["timeout"], self._snap["api_key"])
            provider_obj = get_llm_provider(cfg, provider_name=self._snap["provider"])
            raw = provider_obj.generate(
                [
                    {"role": "system", "content": "你是一个简洁的中文助手。"},
                    {"role": "user", "content": "请只回复：API 连接成功。"},
                ],
                model=self._snap["model"],
                json_mode=False,
            )
            preview = str(raw).replace("\n", " ")[:60]
            self._done.emit(
                True,
                f"连接成功 · {_label(self._snap['provider'])} · {self._snap['model']}　返回：{preview}",
                "",
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("model test failed")
            self._done.emit(False, "", f"{type(exc).__name__}: {exc}")


class SettingsController(QObject):
    """Lightweight bridge between AppConfig and the QML settings page.

    - Exposes current config fields as read-only properties for the form's
      initial values.
    - Never exposes real API keys: only a boolean "has key" + a status hint.
    - Saves config + API keys (only when the user typed a new key).
    - Runs "test current model" on a QThreadPool worker so the UI never blocks.
    """

    dataChanged = Signal()
    statusChanged = Signal()
    testingChanged = Signal()
    testDone = Signal(bool, str, str)  # ok, message, error

    def __init__(self, config: Optional[AppConfig] = None, parent=None) -> None:
        super().__init__(parent)
        self._config = config or AppConfig()
        self._testing = False
        self._status_text = ""
        self._status_is_error = False
        self.testDone.connect(self._on_test_done, Qt.QueuedConnection)

    # ---- config-derived properties --------------------------------------
    def _policy_display(self) -> str:
        return "flash" if self._config.model_policy == "auto" else self._config.model_policy

    @Property(str, notify=dataChanged)
    def provider(self) -> str:  # noqa: N802
        return self._config.provider

    @Property(str, notify=dataChanged)
    def modelPolicy(self) -> str:  # noqa: N802
        return self._policy_display()

    @Property(int, notify=dataChanged)
    def timeoutSeconds(self) -> int:  # noqa: N802
        return self._config.timeout_seconds

    @Property(str, notify=dataChanged)
    def deepseekBaseUrl(self) -> str:  # noqa: N802
        return self._config.base_url

    @Property(str, notify=dataChanged)
    def deepseekFlashModel(self) -> str:  # noqa: N802
        return self._config.flash_model

    @Property(str, notify=dataChanged)
    def deepseekProModel(self) -> str:  # noqa: N802
        return self._config.pro_model

    @Property(str, notify=dataChanged)
    def deepseekCustomModel(self) -> str:  # noqa: N802
        return self._config.custom_model

    @Property(str, notify=dataChanged)
    def mimoBaseUrl(self) -> str:  # noqa: N802
        return self._config.mimo_base_url

    @Property(str, notify=dataChanged)
    def mimoFlashModel(self) -> str:  # noqa: N802
        return self._config.mimo_flash_model

    @Property(str, notify=dataChanged)
    def mimoProModel(self) -> str:  # noqa: N802
        return self._config.mimo_pro_model

    @Property(str, notify=dataChanged)
    def mimoCustomModel(self) -> str:  # noqa: N802
        return self._config.mimo_custom_model

    @Property(str, notify=dataChanged)
    def glmBaseUrl(self) -> str:  # noqa: N802
        return self._config.glm_base_url

    @Property(str, notify=dataChanged)
    def glmFlashModel(self) -> str:  # noqa: N802
        return self._config.glm_flash_model

    @Property(str, notify=dataChanged)
    def glmProModel(self) -> str:  # noqa: N802
        return self._config.glm_pro_model

    @Property(str, notify=dataChanged)
    def glmCustomModel(self) -> str:  # noqa: N802
        return self._config.glm_custom_model

    @Property(bool, notify=dataChanged)
    def hasDeepSeekApiKey(self) -> bool:  # noqa: N802
        return bool(self._config.get_api_key_fallback())

    @Property(bool, notify=dataChanged)
    def hasMimoApiKey(self) -> bool:  # noqa: N802
        return bool(self._config.get_mimo_api_key_fallback())

    @Property(bool, notify=dataChanged)
    def hasGlmApiKey(self) -> bool:  # noqa: N802
        return bool(self._config.get_glm_api_key_fallback())

    @Property(str, notify=dataChanged)
    def deepSeekKeyHint(self) -> str:  # noqa: N802
        return "已保存；留空则保持不变" if self._config.get_api_key_fallback() else "尚未配置"

    @Property(str, notify=dataChanged)
    def mimoKeyHint(self) -> str:  # noqa: N802
        return "已保存；留空则保持不变" if self._config.get_mimo_api_key_fallback() else "尚未配置"

    @Property(str, notify=dataChanged)
    def glmKeyHint(self) -> str:  # noqa: N802
        return "已保存；留空则保持不变" if self._config.get_glm_api_key_fallback() else "尚未配置"

    # ---- status ---------------------------------------------------------
    @Property(str, notify=statusChanged)
    def statusText(self) -> str:  # noqa: N802
        return self._status_text

    @Property(bool, notify=statusChanged)
    def statusIsError(self) -> bool:  # noqa: N802
        return self._status_is_error

    @Property(bool, notify=testingChanged)
    def testing(self) -> bool:  # noqa: N802
        return self._testing

    def _set_status(self, text: str, is_error: bool = False) -> None:
        self._status_text = text
        self._status_is_error = is_error
        self.statusChanged.emit()

    # ---- save -----------------------------------------------------------
    @Slot(dict, result=str)
    def saveSettings(self, values: dict) -> str:  # noqa: N802
        """Persist config + API keys.

        API keys are only written when the user typed a non-empty value, so an
        empty input never clobbers an existing stored key.
        """
        try:
            provider = str(values.get("provider", "")).strip().lower() or self._config.provider
            policy = str(values.get("policy", "")).strip().lower() or self._config.model_policy
            if policy == "auto":  # UI never sends auto, but be safe
                policy = "flash"
            timeout = int(values.get("timeout", 0) or 0) or 120

            self._config.save(
                provider=provider,
                model_policy=policy,
                timeout_seconds=timeout,
                base_url=values.get("deepseekBaseUrl", ""),
                flash_model=values.get("deepseekFlashModel", ""),
                pro_model=values.get("deepseekProModel", ""),
                custom_model=values.get("deepseekCustomModel", ""),
                mimo_base_url=values.get("mimoBaseUrl", ""),
                mimo_flash_model=values.get("mimoFlashModel", ""),
                mimo_pro_model=values.get("mimoProModel", ""),
                mimo_custom_model=values.get("mimoCustomModel", ""),
                glm_base_url=values.get("glmBaseUrl", ""),
                glm_flash_model=values.get("glmFlashModel", ""),
                glm_pro_model=values.get("glmProModel", ""),
                glm_custom_model=values.get("glmCustomModel", ""),
            )

            ds_key = str(values.get("deepseekApiKey", "")).strip()
            if ds_key:
                self._config.set_api_key(ds_key)
            mimo_key = str(values.get("mimoApiKey", "")).strip()
            if mimo_key:
                self._config.set_mimo_api_key(mimo_key)
            glm_key = str(values.get("glmApiKey", "")).strip()
            if glm_key:
                self._config.set_glm_api_key(glm_key)

            self.dataChanged.emit()
            self._set_status("设置已保存")
            return self._status_text
        except Exception as exc:  # noqa: BLE001
            logger.exception("saveSettings failed")
            self._set_status(f"保存失败：{exc}", is_error=True)
            return self._status_text

    # ---- test -----------------------------------------------------------
    def _extract_test_snapshot(self, values: dict) -> dict:
        """Resolve the current form into plain values for a non-persistent test.

        For the selected provider: use the form's Base URL / Model / API Key
        (typed key if non-empty, else the stored fallback). Never persists.
        """
        provider = str(values.get("provider", "")).strip().lower() or self._config.provider
        if provider not in {"deepseek", "mimo", "glm"}:
            provider = "deepseek"
        policy = str(values.get("policy", "")).strip().lower() or "flash"
        tier = policy if policy in {"flash", "pro", "custom"} else "flash"

        try:
            timeout = int(str(values.get("timeout", "")).strip())
        except (TypeError, ValueError):
            timeout = self._config.timeout_seconds
        if timeout <= 0:
            timeout = 120

        tier_key = tier.capitalize()  # Flash / Pro / Custom

        if provider == "mimo":
            base_url = str(values.get("mimoBaseUrl", "")).strip() or self._config.mimo_base_url
            model = str(values.get("mimo" + tier_key + "Model", "")).strip() or self._config.mimo_flash_model
            typed = str(values.get("mimoApiKey", "")).strip()
            api_key = typed or self._config.get_mimo_api_key_fallback()
        elif provider == "glm":
            base_url = str(values.get("glmBaseUrl", "")).strip() or self._config.glm_base_url
            model = str(values.get("glm" + tier_key + "Model", "")).strip() or self._config.glm_flash_model
            typed = str(values.get("glmApiKey", "")).strip()
            api_key = typed or self._config.get_glm_api_key_fallback()
        else:
            base_url = str(values.get("deepseekBaseUrl", "")).strip() or self._config.base_url
            model = str(values.get("deepseek" + tier_key + "Model", "")).strip() or self._config.flash_model
            typed = str(values.get("deepseekApiKey", "")).strip()
            api_key = typed or self._config.get_api_key_fallback()

        return {
            "provider": provider,
            "base_url": base_url,
            "timeout": timeout,
            "api_key": api_key,
            "model": model,
        }

    @Slot(dict)
    def testCurrentModel(self, values: dict) -> None:  # noqa: N802
        """Test the *current form* values (not the saved config). Never persists."""
        if self._testing:
            return
        snapshot = self._extract_test_snapshot(values)
        self._testing = True
        self.testingChanged.emit()
        self._set_status("正在测试…")
        task = _TestModelTask(snapshot, self.testDone)
        QThreadPool.globalInstance().start(task)

    @Slot(bool, str, str)
    def _on_test_done(self, ok: bool, message: str, error: str) -> None:  # noqa: N802
        self._testing = False
        self.testingChanged.emit()
        if ok:
            self._set_status(message)
        else:
            self._set_status(f"测试失败：{error}", is_error=True)
