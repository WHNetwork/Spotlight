from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Slot

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_ROOT = PROJECT_ROOT / "assets"


class AssetBridge(QObject):
    """Read-only bridge that exposes existing assets to QML as file URLs.

    Logical paths stay identical to the Flet front-end (e.g.
    "backgrounds/home_bg.png", "icons/ui/app_logo.png"); this helper only
    converts them to absolute file:// URLs so QML ``Image.source`` can load
    them. No assets are moved, renamed, copied or modified.
    """

    def __init__(self, assets_root: Path = ASSETS_ROOT, parent=None) -> None:
        super().__init__(parent)
        self._assets_root = Path(assets_root)

    def _url(self, rel_path: str) -> str:
        rel_path = rel_path.replace("\\", "/")
        full = (self._assets_root / rel_path).resolve()
        return full.as_uri()

    @Slot(str, result=str)
    def assetUrl(self, rel_path: str) -> str:  # noqa: N802 (QML slot name)
        """Return a file:// URL for an asset given its existing relative path."""
        return self._url(rel_path)

    @Slot(str, result=str)
    def iconUrl(self, name: str) -> str:  # noqa: N802 (QML slot name)
        """Return the icon URL, mirroring ui.shared.icon_src fallback logic."""
        ui_path = "icons/ui/" + name + ".png"
        old_path = "icons/" + name + ".png"
        chosen = ui_path if (self._assets_root / ui_path).exists() else old_path
        return self._url(chosen)

    @staticmethod
    def app_icon_filesystem_path() -> str:
        """Filesystem path to the existing app icon (no copy / no rename)."""
        for cand in ("app_icon.ico", "app_icon.png"):
            p = ASSETS_ROOT / cand
            if p.exists():
                return str(p)
        return ""
