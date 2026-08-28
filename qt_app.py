from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine

from core.config import AppConfig
from ui_qt.asset_bridge import AssetBridge
from ui_qt.character_controller import CharacterController
from ui_qt.game_controller import MainGameController
from ui_qt.home_controller import HomeController
from ui_qt.settings_controller import SettingsController

PROJECT_ROOT = Path(__file__).resolve().parent
QML_DIR = PROJECT_ROOT / "ui_qml"


def main() -> int:
    app = QGuiApplication(sys.argv)
    app.setApplicationName("星光练习室")

    # Reuse the existing app icon path directly; no copy / no rename.
    icon_path = AssetBridge.app_icon_filesystem_path()
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))

    engine = QQmlApplicationEngine()

    asset_bridge = AssetBridge()
    shared_config = AppConfig()
    home_controller = HomeController()
    settings_controller = SettingsController(shared_config)
    character_controller = CharacterController(shared_config)
    game_controller = MainGameController()
    engine.rootContext().setContextProperty("assetBridge", asset_bridge)
    engine.rootContext().setContextProperty("homeController", home_controller)
    engine.rootContext().setContextProperty("settingsController", settings_controller)
    engine.rootContext().setContextProperty("characterController", character_controller)
    engine.rootContext().setContextProperty("gameController", game_controller)

    engine.addImportPath(str(QML_DIR))
    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))

    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
