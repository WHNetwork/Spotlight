from __future__ import annotations

from ui.shared import *
from ui.sections.character import CharacterMixin
from ui.sections.contract import ContractMixin
from ui.sections.diary_settings import DiaryScheduleSettingsMixin
from ui.sections.game import GameMixin
from ui.sections.home import HomeMixin


class KpopApp(
    HomeMixin,
    ContractMixin,
    DiaryScheduleSettingsMixin,
    CharacterMixin,
    GameMixin,
):
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.page.title = "星光练习室"
        self.page.window_width = 1320
        self.page.window_height = 860
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.theme = ft.Theme(font_family=FONT_CN)
        app_icon = PROJECT_ROOT / "assets" / "app_icon.ico"
        if app_icon.exists() and hasattr(self.page, "window"):
            self.page.window.icon = str(app_icon)
        self.config = AppConfig()
        self.storage = SaveStorage()
        self.save_id: Optional[int] = None
        self.state: Optional[GameState] = None
        self.story_view = ft.Column(expand=True, spacing=16)
        self.left_panel = ft.Column(width=300, scroll=ft.ScrollMode.AUTO)
        self.right_panel = ft.Column(width=340, scroll=ft.ScrollMode.AUTO)
        self.choice_row = ft.Column()
        self.custom_input = ft.TextField(label="自定义行动", multiline=True, min_lines=2, max_lines=4, expand=True)
        self.is_generating = False
        self.choice_buttons = []
        self.weekly_plan_selected: list[str] = []
        self.weekly_plan_controls = []
        self.submit_button = None
        self.thinking_banner = None
        self.pinned_alerts = ft.Column(spacing=8, visible=False)
        self.alerts_expanded = False
        self.expanded_sections = {
            "overview": True,
            "schedule_profile": False,
            "body": True,
            "mind": True,
            "career": False,
            "talents": False,
            "period": False,
            "social_env": False,
            "company": True,
            "team": True,
            "fans": False,
            "risks": True,
            "relationships": False,
            "crisis_flags": True,
        }

    def run(self) -> None:
        self.show_home()

    def clear(self) -> None:
        self.page.on_resize = None
        self.page.controls.clear()


def main(page: ft.Page) -> None:
    KpopApp(page).run()


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")