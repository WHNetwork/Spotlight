from __future__ import annotations

from typing import Optional

from loguru import logger
from PySide6.QtCore import QObject, Property, Signal, Slot

from core.storage import SaveStorage


class HomeController(QObject):
    """Minimal Python controller for the QML home page.

    - Reads whether a latest save exists via the real ``SaveStorage`` backend.
    - Exposes that state to QML so the "继续旅程" button can be truly
      enabled/disabled.
    - Emits formal navigation requests for the four main menu entries and the
      four top-right shortcuts. Target QML pages are not migrated yet, so the
      routes are only logged/emitted in this phase.
    """

    navigationRequested = Signal(str)
    latestSaveChanged = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._storage = SaveStorage()
        self._latest_save_id: Optional[int] = None
        self._refresh_latest()

    def _refresh_latest(self) -> None:
        try:
            self._latest_save_id = self._storage.latest_save_id()
        except Exception:
            logger.exception("latest_save_id failed in HomeController")
            self._latest_save_id = None
        self.latestSaveChanged.emit()

    @Property(bool, notify=latestSaveChanged)
    def hasLatestSave(self) -> bool:  # noqa: N802 (QML property name)
        return self._latest_save_id is not None

    @Property(str, notify=latestSaveChanged)
    def latestSaveStatusText(self) -> str:  # noqa: N802 (QML property name)
        return "最新存档可读取" if self._latest_save_id is not None else "尚未开始旅程"

    @Slot()
    def refreshLatestSave(self) -> None:  # noqa: N802 (QML slot name)
        self._refresh_latest()

    @Slot()
    def continueGame(self) -> None:  # noqa: N802 (QML slot name)
        self._emit("continue")

    @Slot()
    def newGame(self) -> None:  # noqa: N802 (QML slot name)
        self._emit("new_game")

    @Slot()
    def loadGame(self) -> None:  # noqa: N802 (QML slot name)
        self._emit("load_game")

    @Slot()
    def openSettings(self) -> None:  # noqa: N802 (QML slot name)
        self._emit("settings")

    @Slot()
    def openContract(self) -> None:  # noqa: N802 (QML slot name)
        self._emit("contract")

    @Slot()
    def openDiary(self) -> None:  # noqa: N802 (QML slot name)
        self._emit("diary")

    @Slot()
    def openSchedule(self) -> None:  # noqa: N802 (QML slot name)
        self._emit("schedule")

    def _emit(self, route: str) -> None:
        logger.info("[QML home] navigation requested: {}", route)
        self.navigationRequested.emit(route)
