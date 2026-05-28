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
from core.relationship_system import relationship_ui_summary


def icon(name: str):
    return getattr(ft.Icons, name, None)


def asset(path: str) -> str:
    return path.replace("\\", "/")


def asset_exists(path: str) -> bool:
    try:
        return (Path(__file__).resolve().parent / "assets" / path).exists()
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


class KpopApp:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.page.title = "星光练习室"
        self.page.window_width = 1320
        self.page.window_height = 860
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.theme = ft.Theme(font_family=FONT_CN)
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
        self.submit_button = None
        self.thinking_banner = None
        self.bgm_audio = None
        self.bgm_enabled = False
        self.bgm_button = None
        self.bgm_button_label = None
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

    def show_home(self) -> None:
        self.clear()
        self.page.padding = 0
        self.page.bgcolor = ft.Colors.WHITE
        latest_id = self.storage.latest_save_id()

        # Flet 不会自动把固定像素 UI 等比缩放，所以主页按当前窗口尺寸计算比例。
        # 设计稿基准接近 1536×864；窗口变化时重建主页，避免按钮和背景错位。
        vw = int(self.page.width or 1460)
        vh = int(self.page.height or 820)
        scale = min(vw / 1536, vh / 864)
        scale = max(0.72, min(1.12, scale))

        def r(value: float) -> int:
            return max(1, int(value * scale))

        def top_icon(name: str, tooltip: str, handler):
            return ft.Container(
                width=r(92),
                height=r(46),
                padding=ft.Padding(left=r(12), right=r(12), top=r(7), bottom=r(7)),
                bgcolor=glass_color(0.74),
                border=ft.Border.all(1, ft.Colors.with_opacity(0.68, ft.Colors.WHITE)),
                border_radius=r(22),
                alignment=ft.Alignment.CENTER,
                tooltip=tooltip,
                on_click=handler,
                ink=True,
                shadow=ft.BoxShadow(
                    blur_radius=r(20),
                    spread_radius=0,
                    color=ft.Colors.with_opacity(0.13, "#536B89"),
                    offset=ft.Offset(0, r(8)),
                ),
                content=ft.Row([
                    ft.Container(
                        icon_image(name, r(22), 0.92),
                        width=r(26),
                        height=r(26),
                        border_radius=r(13),
                        bgcolor=ft.Colors.with_opacity(0.28, "#F7ECEE"),
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Text(tooltip, size=r(12), color="#536B89", weight=ft.FontWeight.W_600, font_family=FONT_CN),
                ], spacing=r(6), alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            )

        button_w = max(r(360), min(r(430), int(vw * 0.42)))
        button_h = r(76)

        def menu_button(title: str, subtitle: str, icon_name: str, english: str, handler, disabled: bool = False):
            bg = ft.Colors.with_opacity(0.80 if not disabled else 0.46, ft.Colors.WHITE)
            fg = "#56617A" if not disabled else "#9AA0B5"
            return ft.Container(
                width=button_w,
                height=button_h,
                padding=ft.Padding(left=r(22), right=r(22), top=r(10), bottom=r(10)),
                border_radius=r(38),
                bgcolor=bg,
                border=ft.Border.all(1, ft.Colors.with_opacity(0.84, "#FFFFFF")),
                shadow=ft.BoxShadow(
                    blur_radius=r(28),
                    spread_radius=0,
                    color=ft.Colors.with_opacity(0.12, "#536B89"),
                    offset=ft.Offset(0, r(10)),
                ),
                opacity=0.62 if disabled else 1,
                on_click=None if disabled else handler,
                ink=not disabled,
                content=ft.Row([
                    ft.Container(
                        icon_image(icon_name, r(36), 0.95 if not disabled else 0.4),
                        width=r(48),
                        height=r(48),
                        border_radius=r(24),
                        bgcolor=ft.Colors.with_opacity(0.52, "#F7ECEE"),
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Column([
                        ft.Text(title, size=r(18), weight=ft.FontWeight.W_600, color=fg),
                        ft.Text(subtitle, size=r(11), color=ft.Colors.with_opacity(0.70, fg)),
                    ], spacing=max(1, r(2)), expand=True),
                    ft.Text(english, size=r(10), color=ft.Colors.with_opacity(0.48, fg), italic=True),
                ], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            )

        profile_card = ft.Container(
            width=r(320),
            height=r(126),
            padding=r(18),
            border_radius=r(24),
            bgcolor=glass_color(0.62),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.72, ft.Colors.WHITE)),
            shadow=ft.BoxShadow(blur_radius=r(26), color=ft.Colors.with_opacity(0.10, "#536B89"), offset=ft.Offset(0, r(10))),
            content=ft.Row([
                ft.Container(icon_image("app_logo", r(72)), width=r(78), height=r(78), border_radius=r(39), bgcolor=ft.Colors.with_opacity(0.55, "#F7ECEE"), alignment=ft.Alignment.CENTER),
                ft.Column([
                    ft.Text("星光练习室", size=r(18), weight=ft.FontWeight.W_700, color="#56617A"),
                    ft.Text("Starlight Practice Room", size=r(11), italic=True, color="#8C88A6", font_family=FONT_EN),
                    ft.Container(height=r(6)),
                    ft.Text("最新存档可读取" if latest_id is not None else "尚未开始旅程", size=r(12), color="#7D8CA0"),
                ], spacing=1),
            ], spacing=r(12)),
        )

        news_card = ft.Container(
            width=r(410),
            padding=r(22),
            border_radius=r(24),
            bgcolor=glass_color(0.58),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.72, ft.Colors.WHITE)),
            shadow=ft.BoxShadow(blur_radius=r(24), color=ft.Colors.with_opacity(0.10, "#536B89"), offset=ft.Offset(0, r(10))),
            content=ft.Column([
                ft.Row([icon_image("diary", r(22)), ft.Text("星光日报", size=r(16), weight=ft.FontWeight.W_700, color="#6A6684")], spacing=r(8)),
                ft.Text("今日行程更新", size=r(13), color="#7D8CA0"),
                ft.Text("· 个人档案：开启角色创建", size=r(13), color="#7D8CA0"),
                ft.Text("· 存档：支持正式回合记录", size=r(13), color="#7D8CA0"),
                ft.Text("· UI：主页视觉重制中", size=r(13), color="#7D8CA0"),
            ], spacing=r(6)),
        )

        title_block = ft.Column([
            ft.Text("✦", size=r(36), color="#B7A6D8", text_align=ft.TextAlign.CENTER),
            ft.Text("星光练习室", size=r(64), weight=ft.FontWeight.W_700, color="#8E88B8", text_align=ft.TextAlign.CENTER),
            ft.Text("Starlight Practice Room", size=r(18), italic=True, color="#9A96B7", text_align=ft.TextAlign.CENTER, font_family=FONT_EN),
            ft.Text("KPOP 女团爱豆模拟器", size=r(16), color="#7D8CA0", text_align=ft.TextAlign.CENTER),
        ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

        menu = ft.Column([
            menu_button("继续旅程", "读取最近一次存档，回到练习室", "app_logo", "CONTINUE", lambda e: self.load_latest(), disabled=latest_id is None),
            menu_button("新的人生", "创建角色，从第一天报到开始", "new_character", "NEW GAME", lambda e: self.show_character_create()),
            menu_button("读取存档", "查看所有保存的故事线", "save_archive", "LOAD GAME", lambda e: self.show_save_list()),
            menu_button("系统设置", "配置模型与 API", "settings", "SETTINGS", lambda e: self.show_settings()),
        ], spacing=r(22), horizontal_alignment=ft.CrossAxisAlignment.CENTER)

        # 小窗口时隐藏两侧装饰卡片，避免挤压主菜单。
        show_side_cards = vw >= 980 and vh >= 680
        show_quote = vw >= 1100 and vh >= 720
        side_width = r(430) if show_side_cards else r(40)

        home = ft.Stack([
            ft.Image(src=asset("backgrounds/home_bg.png"), width=vw, height=vh, fit="cover"),
            ft.Container(width=vw, height=vh, bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.WHITE)),
            ft.Container(
                width=vw,
                height=vh,
                padding=ft.Padding(left=r(42), right=r(42), top=r(30), bottom=r(34)),
                content=ft.Column([
                    ft.Row([
                        profile_card if show_side_cards else ft.Container(width=1, height=1),
                        ft.Container(expand=True),
                        top_icon("contract", "合同", lambda e: self.show_static_page_picker("contract")),
                        top_icon("diary", "日记", lambda e: self.show_static_page_picker("diary")),
                        top_icon("schedule", "行程", lambda e: self.show_static_page_picker("schedule")),
                        top_icon("settings", "设置", lambda e: self.show_settings()),
                    ], spacing=r(14), vertical_alignment=ft.CrossAxisAlignment.START),
                    ft.Container(expand=True),
                    ft.Row([
                        ft.Container(width=side_width),
                        ft.Column([title_block, ft.Container(height=r(34)), menu], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
                        ft.Container(width=side_width),
                    ], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Container(expand=True),
                    ft.Row([
                        news_card if show_side_cards else ft.Container(width=1, height=1),
                        ft.Container(expand=True),
                        ft.Container(
                            width=r(500),
                            padding=ft.Padding(left=r(8), right=r(8), top=r(6), bottom=r(6)),
                            alignment=ft.Alignment.CENTER_RIGHT,
                            content=ft.Image(
                                src=asset("images/home_quote_clean.png"),
                                width=r(455),
                                fit="contain",
                                opacity=0.98,
                            ),
                        ) if show_quote else ft.Container(width=1, height=1),
                    ], vertical_alignment=ft.CrossAxisAlignment.END),
                ], expand=True),
            ),
        ], width=vw, height=vh)

        # 主页需要跟随窗口尺寸重算；其他页面在 clear() 里会移除这个 resize handler。
        def _home_resize(e):
            self.show_home()

        self.page.on_resize = _home_resize
        self.page.add(home)
        self.page.update()


    def load_latest_for_static_page(self) -> bool:
        """Load latest save for home top pages if no game is currently active."""
        if self.state is not None and self.save_id is not None:
            return True
        save_id = self.storage.latest_save_id()
        if save_id is None:
            return False
        try:
            self.save_id = save_id
            self.state = self.storage.load_save(save_id)
            return True
        except Exception:
            logger.exception("load_latest_for_static_page failed")
            return False

    def static_page_bg(self):
        """Stack background fixed to all four edges.

        In Flet desktop, Image(expand=True) inside Stack may keep intrinsic width
        and leave a white area on high-DPI / resized windows. Stack-positioned
        Container with DecorationImage is constrained by left/top/right/bottom
        and therefore scales with the window.
        """
        return ft.Container(
            left=0,
            top=0,
            right=0,
            bottom=0,
            bgcolor="#F8F6FC",
            image=ft.DecorationImage(
                src=asset("backgrounds/subpage_bg_wide.png"),
                fit="cover",
                opacity=1.0,
            ),
        )

    def static_page_top_bar(self, title: str, subtitle: str, icon_name: str):
        return ft.Container(
            padding=ft.Padding(left=28, right=28, top=18, bottom=14),
            content=ft.Row([
                ft.Container(icon_image(icon_name, 32, 0.95), width=46, height=46, border_radius=18, bgcolor=ft.Colors.with_opacity(0.45, "#F7ECEE"), alignment=ft.Alignment.CENTER),
                ft.Column([
                    ft.Text(title, size=self.ui_size(24), weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN),
                    ft.Text(subtitle, size=self.ui_size(12), color=C["sub"], font_family=FONT_CN),
                ], spacing=1),
                ft.Container(expand=True),
                ft.Container(
                    padding=ft.Padding(left=14, right=14, top=8, bottom=8),
                    border_radius=20,
                    bgcolor=ft.Colors.with_opacity(0.78, ft.Colors.WHITE),
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.58, C["line"])),
                    ink=True,
                    on_click=lambda e: self.show_home(),
                    content=ft.Row([icon_image("app_logo", 18, 0.9), ft.Text("返回首页", size=self.ui_size(12), color=C["dai"], font_family=FONT_CN)], spacing=6),
                ),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )


    def select_save_for_static_page(self, save_id: int, target: str) -> None:
        try:
            self.save_id = save_id
            self.state = self.storage.load_save(save_id)
        except Exception:
            logger.exception("select_save_for_static_page failed")
            self.snack("读取角色档案失败。")
            return
        if target == "contract":
            self.show_contract_page()
        elif target == "diary":
            self.show_diary_page()
        elif target == "schedule":
            self.show_schedule_page()

    def show_static_page_picker(self, target: str) -> None:
        title_map = {
            "contract": ("选择合同档案", "选择要查看哪位角色的公司与合约记录", "contract"),
            "diary": ("选择日记本", "选择要打开哪位角色的私人日记", "diary"),
            "schedule": ("选择行程表", "选择要查看哪位角色的近期安排", "schedule"),
        }
        title, subtitle, icon_name = title_map.get(target, ("选择角色档案", "先选择一个角色", "new_character"))

        saves = []
        try:
            saves = self.storage.list_saves()
        except Exception:
            logger.exception("list_saves failed in static picker")

        self.clear()
        self.page.padding = 0
        self.page.bgcolor = ft.Colors.WHITE

        cards = []
        for item in saves:
            save_id = item.get("id")
            raw_name = item.get("name") or item.get("save_name") or f"存档 {save_id}"
            turn = item.get("turn") or 0
            stage = item.get("current_stage") or "未知阶段"
            updated_at = item.get("updated_at") or ""
            created_at = item.get("created_at") or ""
            label = f"{stage} · 第 {turn} 回合"
            cards.append(
                ft.Container(
                    width=360,
                    padding=18,
                    border_radius=26,
                    bgcolor=ft.Colors.with_opacity(0.84, ft.Colors.WHITE),
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.70, ft.Colors.WHITE)),
                    shadow=ft.BoxShadow(
                        blur_radius=22,
                        spread_radius=0,
                        color=ft.Colors.with_opacity(0.12, C["dai"]),
                        offset=ft.Offset(0, 8),
                    ),
                    ink=True,
                    on_click=lambda e, sid=save_id: self.select_save_for_static_page(sid, target),
                    content=ft.Row([
                        ft.Container(icon_image(icon_name, 28, 0.92), width=42, height=42, border_radius=18, bgcolor=ft.Colors.with_opacity(0.36, C["lotus"]), alignment=ft.Alignment.CENTER),
                        ft.Column([
                            ft.Text(str(raw_name), size=self.ui_size(16), weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN, max_lines=1),
                            ft.Text(label, size=self.ui_size(12), color=C["sub"], font_family=FONT_CN, max_lines=1),
                            ft.Text(f"更新：{updated_at or created_at}", size=self.ui_size(10), color=C["dai"], font_family=FONT_CN, max_lines=1),
                        ], spacing=2, expand=True),
                    ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                )
            )

        if not cards:
            body = ft.Container(
                width=520,
                padding=28,
                border_radius=30,
                bgcolor=ft.Colors.with_opacity(0.84, ft.Colors.WHITE),
                border=ft.Border.all(1, ft.Colors.with_opacity(0.70, ft.Colors.WHITE)),
                shadow=ft.BoxShadow(blur_radius=28, color=ft.Colors.with_opacity(0.12, C["dai"]), offset=ft.Offset(0, 10)),
                content=ft.Column([
                    ft.Text("还没有角色档案", size=self.ui_size(20), weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN),
                    ft.Text("先创建角色或读取存档后，再查看合同、日记和行程。", size=self.ui_size(13), color=C["sub"], font_family=FONT_CN, text_align=ft.TextAlign.CENTER),
                    ft.Row([
                        ft.Container(
                            padding=ft.Padding(left=18, right=18, top=10, bottom=10),
                            border_radius=22,
                            bgcolor=ft.Colors.with_opacity(0.86, C["lotus"]),
                            ink=True,
                            on_click=lambda e: self.show_character_create(),
                            content=ft.Text("创建角色", size=self.ui_size(13), color=C["ink"], font_family=FONT_CN, weight=ft.FontWeight.W_600),
                        ),
                        ft.Container(
                            padding=ft.Padding(left=18, right=18, top=10, bottom=10),
                            border_radius=22,
                            bgcolor=ft.Colors.with_opacity(0.86, ft.Colors.WHITE),
                            border=ft.Border.all(1, ft.Colors.with_opacity(0.54, C["line"])),
                            ink=True,
                            on_click=lambda e: self.show_save_list(),
                            content=ft.Text("读取存档", size=self.ui_size(13), color=C["dai"], font_family=FONT_CN, weight=ft.FontWeight.W_600),
                        ),
                    ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
                ], spacing=14, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            )
        else:
            body = ft.Column([
                ft.Container(
                    width=min(1180, int((self.page.width or 1320) - 80)),
                    padding=ft.Padding(left=4, right=4, top=8, bottom=8),
                    content=ft.Row(cards, wrap=True, spacing=18, run_spacing=18),
                ),
            ], expand=True, scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

        content = ft.Column([
            self.static_page_top_bar(title, subtitle, icon_name),
            ft.Container(
                expand=True,
                alignment=ft.Alignment.TOP_CENTER,
                padding=ft.Padding(left=self.ui_size(26), right=self.ui_size(26), top=self.ui_size(16), bottom=self.ui_size(28)),
                content=body,
            ),
        ], expand=True)
        self.page.add(ft.Stack([self.static_page_bg(), content], expand=True))
        self.page.update()

    def static_empty_page(self, title: str, subtitle: str, icon_name: str):
        self.clear()
        self.page.padding = 0
        self.page.bgcolor = ft.Colors.WHITE
        content = ft.Column([
            self.static_page_top_bar(title, subtitle, icon_name),
            ft.Container(expand=True),
            ft.Container(
                width=520,
                padding=28,
                border_radius=30,
                bgcolor=ft.Colors.with_opacity(0.82, ft.Colors.WHITE),
                border=ft.Border.all(1, ft.Colors.with_opacity(0.72, ft.Colors.WHITE)),
                shadow=ft.BoxShadow(blur_radius=30, color=ft.Colors.with_opacity(0.12, C["dai"]), offset=ft.Offset(0, 10)),
                content=ft.Column([
                    ft.Text("还没有可以读取的角色档案", size=20, weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN, text_align=ft.TextAlign.CENTER),
                    ft.Text("先创建角色或读取存档后，这里会显示当前角色对应的内容。每个角色的合同、日记和行程都跟随各自存档，不会串到其他角色。", size=13, color=C["sub"], font_family=FONT_CN, text_align=ft.TextAlign.CENTER),
                    ft.Row([
                        ft.Container(
                            padding=ft.Padding(left=18, right=18, top=10, bottom=10),
                            border_radius=22,
                            bgcolor=ft.Colors.with_opacity(0.86, C["lotus"]),
                            ink=True,
                            on_click=lambda e: self.show_character_create(),
                            content=ft.Text("创建角色", size=13, color=C["ink"], font_family=FONT_CN, weight=ft.FontWeight.W_600),
                        ),
                        ft.Container(
                            padding=ft.Padding(left=18, right=18, top=10, bottom=10),
                            border_radius=22,
                            bgcolor=ft.Colors.with_opacity(0.86, ft.Colors.WHITE),
                            border=ft.Border.all(1, ft.Colors.with_opacity(0.54, C["line"])),
                            ink=True,
                            on_click=lambda e: self.show_save_list(),
                            content=ft.Text("读取存档", size=13, color=C["dai"], font_family=FONT_CN, weight=ft.FontWeight.W_600),
                        ),
                    ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
                ], spacing=14, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            ),
            ft.Container(expand=True),
        ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        self.page.add(ft.Stack([self.static_page_bg(), ft.Container(content=content, expand=True)], expand=True))
        self.page.update()

    def static_page_card(self, title: str, subtitle: str, icon_name: str, body, width: int | None = None):
        return ft.Container(
            width=width,
            padding=20,
            border_radius=26,
            bgcolor=ft.Colors.with_opacity(0.82, ft.Colors.WHITE),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.68, ft.Colors.WHITE)),
            shadow=ft.BoxShadow(blur_radius=24, color=ft.Colors.with_opacity(0.10, C["dai"]), offset=ft.Offset(0, 8)),
            content=ft.Column([
                ft.Row([
                    ft.Container(icon_image(icon_name, 24, 0.9), width=36, height=36, border_radius=18, bgcolor=ft.Colors.with_opacity(0.32, C["lotus"]), alignment=ft.Alignment.CENTER),
                    ft.Column([
                        ft.Text(title, size=self.ui_size(17), weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN),
                        ft.Text(subtitle, size=self.ui_size(11), color=C["sub"], font_family=FONT_CN),
                    ], spacing=1, expand=True),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Container(height=4),
                body,
            ], spacing=10),
        )

    def static_text_block(self, text: str, min_lines: int = 4, max_lines: int = 12, size: float | None = None):
        fs = size if size is not None else self.ui_size(13)
        return ft.TextField(
            value=text,
            expand=True,
            read_only=True,
            multiline=True,
            min_lines=min_lines,
            max_lines=max_lines,
            border_color=ft.Colors.TRANSPARENT,
            focused_border_color=ft.Colors.TRANSPARENT,
            cursor_color=ft.Colors.TRANSPARENT,
            text_style=ft.TextStyle(font_family=FONT_CN, color=C["ink"], size=fs),
            bgcolor=ft.Colors.with_opacity(0.00, ft.Colors.WHITE),
        )

    def ui_scale(self) -> float:
        try:
            vw = float(self.page.width or 1320)
            vh = float(self.page.height or 860)
        except Exception:
            vw, vh = 1320, 860
        return max(0.72, min(1.16, min(vw / 1360, vh / 820)))

    def ui_size(self, value: float) -> int:
        return max(1, int(value * self.ui_scale()))

    def subpage_layout_mode(self) -> str:
        try:
            vw = int(self.page.width or 1320)
        except Exception:
            vw = 1320
        if vw < 940:
            return "narrow"
        if vw < 1180:
            return "medium"
        return "wide"

    def static_responsive_row(self, controls: list, spacing: int | None = None):
        mode = self.subpage_layout_mode()
        spacing = spacing if spacing is not None else self.ui_size(18)
        if mode == "narrow":
            return ft.Column(controls, spacing=spacing, scroll=ft.ScrollMode.AUTO, expand=True)
        return ft.Row(controls, spacing=spacing, vertical_alignment=ft.CrossAxisAlignment.START, expand=True)

    def subpage_shell(self, title: str, subtitle: str, icon_name: str, body):
        self.clear()
        self.page.padding = 0
        self.page.bgcolor = ft.Colors.WHITE
        content = ft.Column([
            self.static_page_top_bar(title, subtitle, icon_name),
            ft.Container(
                padding=ft.Padding(left=self.ui_size(24), right=self.ui_size(24), top=self.ui_size(8), bottom=self.ui_size(24)),
                expand=True,
                content=body,
            ),
        ], expand=True)
        self.page.add(ft.Stack([self.static_page_bg(), content], expand=True))
        self.page.update()

    def subpage_resize_refresh(self, page_name: str) -> None:
        def handler(e):
            if page_name == "contract":
                self.show_contract_page()
            elif page_name == "diary":
                self.show_diary_page()
            elif page_name == "schedule":
                self.show_schedule_page()
        self.page.on_resize = handler

    def active_character_label(self) -> str:
        if self.state is None:
            return "未读取角色"
        ch = self.state.character if isinstance(self.state.character, dict) else {}
        name = ch.get("艺名") or ch.get("本名") or self.state.save_name or "当前角色"
        stage = self.state.current_stage or "当前阶段"
        return f"{name} · {stage} · 第 {self.state.turn} 回合"

    def show_contract_page(self) -> None:
        if not self.load_latest_for_static_page():
            self.static_empty_page("合同档案", "公司、合约与边界", "contract")
            return
        self.subpage_resize_refresh("contract")

        s = self.state
        ch = s.character if isinstance(s.character, dict) else {}
        company = s.company if isinstance(s.company, dict) else {}
        risks = s.risks if isinstance(s.risks, dict) else {}
        safety = s.safety if isinstance(s.safety, dict) else {}
        debut = s.debut if isinstance(s.debut, dict) else {}

        if s.is_trainee_stage():
            contract_name = "练习生协议"
            contract_phase = "训练观察期"
            activity_limit = "外出、公开社交、外部合作均需公司确认"
        else:
            contract_name = "专属艺人合约"
            contract_phase = "活动履行期"
            activity_limit = "公开行程、个人活动、品牌露出与恋爱相关议题均受公司管理"

        risk_text = "\n".join([
            f"• 当前合约：{contract_name}",
            f"• 合约阶段：{contract_phase}",
            f"• 活动限制：{activity_limit}",
            f"• 公司信任：{company.get('公司信任度', 0)}",
            f"• 资源倾斜：{company.get('资源倾斜度', 0)}",
            f"• 个人议价：{company.get('个人议价权', 0)}",
            f"• 续约倾向：{company.get('续约倾向', 0)}",
            f"• 出道动向：{self.player_debut_status(debut)}",
        ])
        notes = "\n".join([
            "• 低信任会提高请假、外出、调整训练计划时的阻力。",
            "• 资源倾斜会影响镜头、训练机会、考核关注度与后续行程。",
            "• 个人议价权会在续约、Solo、制作参与、个人活动窗口中发挥作用。",
            "• 私自接触外部资源、绕开经纪人发声、公开暧昧关系，会显著提高公关与合约风险。",
            "• 未成年或海外成员会额外受到监护、签证、学校和家庭沟通约束。",
        ])

        mode = self.subpage_layout_mode()
        side_w = None if mode == "narrow" else self.ui_size(340)
        controls = [
            self.static_page_card(
                "合约概览", "当前角色与公司的绑定关系", "contract",
                ft.Column([
                    self.text_line("角色", ch.get("艺名") or ch.get("本名") or s.save_name, "new_character", C["lotus"]),
                    self.text_line("身份", ch.get("身份", "练习生"), "stage", C["jade"]),
                    self.text_line("国籍", ch.get("国籍", "未填写"), "market", C["apricot"]),
                    self.text_line("阶段", contract_phase, "schedule", C["lavender"]),
                    self.text_line("当前主线", s.current_mainline, "diary", C["lotus"]),
                ], spacing=self.ui_size(8)),
                width=side_w,
            ),
            ft.Container(
                expand=True,
                content=ft.Column([
                    self.static_page_card("关键条款", "静态浏览版：先展示，不开放修改", "staff_boundary", self.static_text_block(risk_text, 8, 14)),
                    self.static_page_card("风险说明", "这些内容会影响行动合法性与剧情后果", "crisis_pr", self.static_text_block(notes, 8, 14)),
                ], spacing=self.ui_size(18), scroll=ft.ScrollMode.AUTO, expand=True),
            ),
            self.static_page_card(
                "风险与边界", "公司可见的风险状态", "safety",
                ft.Column([
                    self.metric_bar("合约稳定度", company.get("合约稳定度", 0), "contract", C["jade"]),
                    self.metric_bar("公关危机风险", risks.get("公关危机风险", 0), "crisis_pr", C["rouge"], danger_high=True),
                    self.metric_bar("私生风险", risks.get("私生风险", 0), "safety", C["rouge"], danger_high=True),
                    self.metric_bar("边界风险", safety.get("boundary_violation_risk", 0), "staff_boundary", C["rouge"], danger_high=True),
                    self.metric_bar("外出许可", safety.get("outing_permission", 0), "schedule", C["jade"]),
                ], spacing=self.ui_size(6)),
                width=side_w,
            ),
        ]
        self.subpage_shell("合同档案", self.active_character_label(), "contract", self.static_responsive_row(controls))

    def turn_date_for_diary(self, turn_no: int, row_created_at: str | None = None) -> str:
        if self.state is not None and isinstance(self.state.time, dict):
            current = str(self.state.time.get("current_date") or "")
            current_turn = int(getattr(self.state, "turn", 0) or 0)
            try:
                base = datetime.strptime(current, "%Y-%m-%d")
                delta_turns = max(0, current_turn - int(turn_no))
                return (base - timedelta(days=delta_turns * 7)).strftime("%Y-%m-%d")
            except Exception:
                pass
        if row_created_at:
            try:
                return datetime.fromisoformat(str(row_created_at)).strftime("%Y-%m-%d")
            except Exception:
                pass
        return ""

    def parse_json_object(self, raw: str) -> Dict[str, Any]:
        text = str(raw or "").strip()
        if text.startswith("```"):
            text = text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(text)
        except Exception:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                return json.loads(text[start:end + 1])
            raise

    def generate_diary_entry_with_ds(self, row) -> Dict[str, Any]:
        try:
            response = json.loads(row["response_json"] or "{}")
        except Exception:
            response = {}
        try:
            events = json.loads(row["system_events_json"] or "[]")
        except Exception:
            events = []
        try:
            applied = json.loads(row["applied_diff_json"] or "{}")
        except Exception:
            applied = {}

        turn_no = int(row["turn_no"])
        narrative = self.display_narrative_from_response_data(response, "")
        action = str(row["player_action"] or "").strip()
        ch = self.state.character if self.state is not None and isinstance(self.state.character, dict) else {}
        state_payload = self.state.as_prompt_dict() if self.state is not None else {}

        hidden_context = {
            "period": state_payload.get("period", {}),
            "inner_life": state_payload.get("inner_life", {}),
            "relationships": state_payload.get("relationships", {}),
            "family": state_payload.get("family", {}),
            "school": state_payload.get("school", {}),
            "safety": state_payload.get("safety", {}),
            "company": state_payload.get("company", {}),
            "team": state_payload.get("team", {}),
            "risks": state_payload.get("risks", {}),
            "events": events,
            "applied_diff": applied,
        }

        messages = [
            {
                "role": "system",
                "content": (
                    "你是《星光练习室》的私人日记生成器。输出必须是严格 JSON。"
                    "你要把回合剧情改写成角色自己的私人日记，不要照抄剧情正文。"
                    "禁止写系统词、数值、JSON解释、少女心事系统、生理周期系统、属性变化、DS、API。"
                    "可以把身体不适、经期困扰、友情、暧昧、被照顾、被忽视、家庭压力、学校压力、公司压迫、练习室疲惫写成含蓄的内心感受。"
                    "文风细腻、真实、克制，第一人称，不写流水账，不靠对话堆砌。"
                    "字段：title, content, mood, tags, related_people。content 120到220字。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps({
                    "character": {
                        "name": ch.get("艺名") or ch.get("本名") or (self.state.save_name if self.state else "当前角色"),
                        "age": ch.get("年龄"),
                        "nationality": ch.get("国籍"),
                        "identity": ch.get("身份"),
                    },
                    "turn": turn_no,
                    "date": self.turn_date_for_diary(turn_no, row["created_at"] if "created_at" in row.keys() else None),
                    "player_action": action,
                    "narrative": narrative,
                    "public_summary": response.get("public_summary", ""),
                    "hidden_context": hidden_context,
                }, ensure_ascii=False),
            },
        ]

        try:
            raw = get_llm_provider(self.config).generate(messages, model=self.config.model_for_tier("flash"))
            data = self.parse_json_object(raw)
            return {
                "turn": turn_no,
                "date": self.turn_date_for_diary(turn_no, row["created_at"] if "created_at" in row.keys() else None),
                "title": self.normalize_visible_text(data.get("title"))[:30] or f"第 {turn_no} 回合的记录",
                "content": self.normalize_visible_text(data.get("content"))[:520] or self.diary_entry_from_row(row)["content"],
                "mood": self.normalize_visible_text(data.get("mood"))[:18] or "平稳",
                "tags": [str(x)[:10] for x in data.get("tags", []) if str(x).strip()][:6] or ["日常"],
                "related_people": [str(x)[:12] for x in data.get("related_people", []) if str(x).strip()][:5],
                "source": "deepseek",
            }
        except Exception:
            logger.exception("generate_diary_entry_with_ds failed")
            entry = self.diary_entry_from_row(row)
            entry["source"] = "fallback"
            return entry

    def ensure_diary_entries(self, limit: int = 12, max_generate: int = 3) -> list[Dict[str, Any]]:
        """Return diary entries from cache; only generate missing turns.

        If generation fails, fallback entries are also cached. This prevents the
        page from retrying the same failed DS generation every time it opens.
        """
        if self.save_id is None:
            return []

        rows = self.latest_turn_rows(limit)
        cached: Dict[int, Dict[str, Any]] = {}
        try:
            for entry in self.storage.get_diary_entries(self.save_id, limit=limit):
                cached[int(entry.get("turn", -1))] = entry
        except Exception:
            logger.exception("load cached diary entries failed")
            cached = {}

        generated = 0
        entries: list[Dict[str, Any]] = []
        for row in rows:
            turn_no = int(row["turn_no"])
            entry = cached.get(turn_no)
            if entry is not None:
                entry.setdefault("source", "cache")
                entries.append(entry)
                continue

            if generated < max_generate:
                entry = self.generate_diary_entry_with_ds(row)
                generated += 1
            else:
                entry = self.diary_entry_from_row(row)
                entry["source"] = "preview"

            # Cache both DS and fallback/preview entries so reopening does not regenerate.
            try:
                self.storage.upsert_diary_entry(self.save_id, turn_no, entry)
            except Exception:
                logger.exception("upsert diary entry failed")
            entries.append(entry)

        return entries

    def latest_turn_rows(self, limit: int = 30) -> list:
        if self.save_id is None:
            return []
        try:
            with self.storage.connect() as conn:
                return conn.execute(
                    """
                    SELECT turn_no, player_action, response_json, applied_diff_json, system_events_json, created_at
                    FROM turns
                    WHERE save_id=?
                    ORDER BY turn_no DESC
                    LIMIT ?
                    """,
                    (self.save_id, limit),
                ).fetchall()
        except Exception:
            logger.exception("latest_turn_rows failed")
            return []

    def diary_entry_from_row(self, row) -> Dict[str, Any]:
        try:
            response = json.loads(row["response_json"] or "{}")
        except Exception:
            response = {}
        try:
            events = json.loads(row["system_events_json"] or "[]")
        except Exception:
            events = []

        narrative = self.display_narrative_from_response_data(response, "")
        summary = self.normalize_visible_text(response.get("public_summary") or "")
        action = str(row["player_action"] or "").strip()
        turn_no = row["turn_no"]

        title = summary.split("。")[0].split("\n")[0].strip()
        if not title:
            title = f"第 {turn_no} 回合的记录"
        title = title[:24]

        tags = []
        for word, tag in [
            ("练", "训练"), ("舞", "训练"), ("唱", "声乐"), ("rap", "RAP"), ("公司", "公司"),
            ("老师", "老师"), ("队友", "关系"), ("经纪", "公司"), ("休息", "身体"),
            ("睡", "身体"), ("痛", "身体"), ("考核", "考核"), ("粉丝", "粉丝"),
        ]:
            if word in action.lower() or word in narrative.lower() or word in summary.lower():
                if tag not in tags:
                    tags.append(tag)

        event_titles = []
        for ev in events:
            if not isinstance(ev, dict):
                continue
            if self.is_hidden_system_event(ev):
                continue
            title_ev = ev.get("title")
            if title_ev and title_ev not in event_titles:
                event_titles.append(title_ev)

        content = narrative.strip() or summary.strip() or "今天的内容没有被完整记录下来，只留下了行动和状态的痕迹。"
        if len(content) > 900:
            content = content[:900].rstrip() + "……"

        mood = "平稳"
        mood_source = content + summary
        if any(x in mood_source for x in ["疲", "痛", "撑", "压力", "不安", "怕"]):
            mood = "疲惫"
        if any(x in mood_source for x in ["开心", "轻", "笑", "顺利", "恢复"]):
            mood = "松动"
        if any(x in mood_source for x in ["争执", "危机", "骂", "崩"]):
            mood = "紧绷"

        return {
            "turn": turn_no,
            "date": self.turn_date_for_diary(turn_no, row["created_at"] if "created_at" in row.keys() else None),
            "title": title,
            "content": content,
            "mood": mood,
            "tags": tags[:5] or ["日常"],
            "events": event_titles[:3],
            "action": action,
        }


    def show_diary_loading_page(self, missing_count: int = 0) -> None:
        """Show an immediate visible state before synchronous diary generation."""
        self.clear()
        self.page.padding = 0
        self.page.bgcolor = ft.Colors.WHITE
        content = ft.Column([
            self.static_page_top_bar("私人日记", self.active_character_label(), "diary"),
            ft.Container(
                expand=True,
                alignment=ft.Alignment.CENTER,
                content=ft.Container(
                    width=520,
                    padding=30,
                    border_radius=32,
                    bgcolor=ft.Colors.with_opacity(0.86, ft.Colors.WHITE),
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.70, ft.Colors.WHITE)),
                    shadow=ft.BoxShadow(blur_radius=30, color=ft.Colors.with_opacity(0.12, C["dai"]), offset=ft.Offset(0, 10)),
                    content=ft.Column([
                        ft.ProgressRing(width=34, height=34, stroke_width=3),
                        ft.Text("正在撰写日记中", size=self.ui_size(20), weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN, text_align=ft.TextAlign.CENTER),
                    ], spacing=14, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                ),
            ),
        ], expand=True)
        self.page.add(ft.Stack([self.static_page_bg(), content], expand=True))
        self.page.update()

    def count_missing_diary_entries(self, limit: int = 24) -> int:
        if self.save_id is None:
            return 0
        rows = self.latest_turn_rows(limit)
        cached_turns = set()
        try:
            for entry in self.storage.get_diary_entries(self.save_id, limit=limit):
                cached_turns.add(int(entry.get("turn", -1)))
        except Exception:
            return min(len(rows), 3)
        return sum(1 for row in rows if int(row["turn_no"]) not in cached_turns)

    def render_diary_entries_page(self, entries: list[Dict[str, Any]]) -> None:
        """Render diary page from already loaded/generated entries."""
        if self.state is None:
            self.static_empty_page("私人日记", "每个角色各自保存的回合记忆", "diary")
            return

        if not entries:
            entries = [{
                "turn": self.state.turn,
                "date": self.state.time.get("current_date", "") if isinstance(self.state.time, dict) else "",
                "title": "练习室的第一页",
                "content": "这个角色的日记还没有正式开始。推进一回合后，这里会根据当前角色的经历生成可浏览的私人记录。",
                "mood": "等待",
                "tags": ["开始"],
                "events": [],
                "related_people": [],
                "action": "",
            }]

        entry_cards = []
        for entry in entries:
            tags = entry.get("tags") or ["日常"]
            related = entry.get("related_people") or []
            entry_cards.append(
                self.static_page_card(
                    f"第 {entry.get('turn')} 回合 · {entry.get('title', '私人记录')}",
                    f"{entry.get('date') or '日期未定'} · 心情：{entry.get('mood', '平稳')}",
                    "diary",
                    ft.Column([
                        self.static_text_block(entry.get("content", ""), 7, 18),
                        ft.Row([self.mini_chip(tag, C["lotus"]) for tag in tags[:6]], wrap=True, spacing=6, run_spacing=6),
                        ft.Row([self.mini_chip(x, C["jade"]) for x in related[:5]], wrap=True, spacing=6, run_spacing=6) if related else ft.Container(height=1),
                    ], spacing=self.ui_size(8)),
                )
            )

        mode = self.subpage_layout_mode()
        left_w = None if mode == "narrow" else self.ui_size(330)
        intro_card = self.static_page_card(
            "日记说明", "当前角色的私人记录",
            "diary",
            ft.Column([
                ft.Text("日记跟随当前角色存档保存，不同角色之间互不共享。", size=self.ui_size(13), color=C["ink"], font_family=FONT_CN),
                ft.Text("打开本页时，会把缺失回合交给叙事模型改写成私人日记并缓存到当前存档。已经写好的日记会直接读取，不会重复生成。", size=self.ui_size(12), color=C["sub"], font_family=FONT_CN),
                ft.Divider(height=self.ui_size(16), color=ft.Colors.with_opacity(0.32, C["line"])),
                self.text_line("当前角色", self.state.character.get("艺名") or self.state.save_name, "new_character", C["lotus"]),
                self.text_line("记录数量", len(entries), "schedule", C["jade"]),
                self.text_line("最近回合", self.state.turn, "stage", C["apricot"]),
            ], spacing=self.ui_size(8)),
            width=left_w,
        )
        entries_view = ft.Container(expand=True, content=ft.Column(entry_cards, spacing=self.ui_size(18), scroll=ft.ScrollMode.AUTO, expand=True))
        self.subpage_shell("私人日记", self.active_character_label(), "diary", self.static_responsive_row([intro_card, entries_view]))

    def show_diary_page(self) -> None:
        if not self.load_latest_for_static_page():
            self.static_empty_page("私人日记", "每个角色各自保存的回合记忆", "diary")
            return
        self.subpage_resize_refresh("diary")

        missing = self.count_missing_diary_entries(limit=24)
        if missing <= 0:
            entries = self.ensure_diary_entries(limit=24, max_generate=0)
            self.render_diary_entries_page(entries)
            return

        # Show loading immediately, then generate in a background thread.
        # Without the thread, Flet repaints only after the synchronous DS calls finish,
        # so the user never actually sees "正在撰写日记中".
        self.show_diary_loading_page(min(missing, 3))

        def worker():
            try:
                entries = self.ensure_diary_entries(limit=24, max_generate=3)
                self.render_diary_entries_page(entries)
            except Exception:
                logger.exception("diary generation worker failed")
                self.snack("日记生成失败，已保留当前存档。")

        threading.Thread(target=worker, daemon=True).start()


    def show_schedule_page(self) -> None:
        if not self.load_latest_for_static_page():
            self.static_empty_page("行程表", "训练、考核与恢复安排", "schedule")
            return
        self.subpage_resize_refresh("schedule")

        s = self.state
        time_data = s.time if isinstance(s.time, dict) else {}
        profile = s.schedule_profile if isinstance(s.schedule_profile, dict) else {}
        body = s.body if isinstance(s.body, dict) else {}
        current_profile = profile.get("current_profile", {}) if isinstance(profile.get("current_profile", {}), dict) else {}

        future_items = [
            ("今天", s.current_schedule or "根据状态完成当日安排", "schedule"),
            ("本回合", f"预计跨度：{time_data.get('turn_duration_days', 7)} 天", "schedule"),
            ("月末考核", f"倒计时：{time_data.get('next_evaluation_days', time_data.get('assessment_countdown_days', '未知'))} 天", "stage"),
            ("恢复安排", "体力低于 35 或伤病风险高于 60 时，建议优先恢复", "health"),
            ("训练维护", "长期不练的技能会先掉手感，之后才可能退化属性", "training"),
        ]

        if s.is_trainee_stage():
            plan_text = "\n".join([
                "• 练习生阶段以训练、考核、基础纪律、宿舍与学校压力为主。",
                "• 舞蹈、声乐、RAP、舞台表现需要周期性维护。",
                "• 月末考核前，强行堆训练会增加疲劳和伤病风险。",
                "• 公司观察期内，私自外出、迟到、缺课会影响信任与出道候选。",
            ])
        else:
            plan_text = "\n".join([
                "• 爱豆阶段以打歌、拍摄、综艺、巡演、回归准备为主。",
                "• 训练从能力提升转为状态维护，长期不练仍会影响舞台质量。",
                "• 高工作负荷会挤压睡眠、恢复和关系经营。",
                "• 回归窗口、合约窗口、危机窗口会改变行程优先级。",
            ])

        mode = self.subpage_layout_mode()
        side_w = None if mode == "narrow" else self.ui_size(360)
        controls = [
            self.static_page_card(
                "未来节点", "当前存档的近期安排",
                "schedule",
                ft.Column([self.text_line(day, text, icon_name, C["lotus"]) for day, text, icon_name in future_items], spacing=self.ui_size(9)),
                width=side_w,
            ),
            ft.Container(
                expand=True,
                content=ft.Column([
                    self.static_page_card("阶段节奏", "按当前身份给出的日程逻辑", "training", self.static_text_block(plan_text, 8, 14)),
                    self.static_page_card(
                        "时间压力", "当前节奏的风险提示",
                        "schedule",
                        ft.Column([
                            self.metric_bar("行程负荷", profile.get("workload_pressure", 0), "schedule", C["apricot"], danger_high=True),
                            self.metric_bar("体力", body.get("体力", 0), "health", C["jade"]),
                            self.metric_bar("睡眠质量", body.get("睡眠质量", 0), "period", C["lotus"]),
                            self.metric_bar("肌肉疲劳", body.get("肌肉疲劳", 0), "dance", C["rouge"], danger_high=True),
                            self.metric_bar("伤病风险", body.get("伤病风险", 0), "crisis_pr", C["rouge"], danger_high=True),
                        ], spacing=self.ui_size(6)),
                    ),
                ], spacing=self.ui_size(18), scroll=ft.ScrollMode.AUTO, expand=True),
            ),
            self.static_page_card(
                "训练构成", "当前阶段的时间分布",
                "stage",
                ft.Column(
                    [self.metric_bar(k, v, "training", C["jade"]) for k, v in current_profile.items()] or
                    [ft.Text("暂无行程构成。", size=self.ui_size(12), color=C["sub"], font_family=FONT_CN)],
                    spacing=self.ui_size(6),
                ),
                width=side_w,
            ),
        ]
        self.subpage_shell("行程表", self.active_character_label(), "schedule", self.static_responsive_row(controls))


    def settings_page_bg(self):
        return ft.Container(
            left=0,
            top=0,
            right=0,
            bottom=0,
            bgcolor="#F8F7FC",
            image=ft.DecorationImage(
                src=asset("backgrounds/settings_bg_v3.png"),
                fit="cover",
                opacity=1.0,
            ),
        )

    def settings_card(self, title: str, subtitle: str, icon_name: str, controls: list, width: int | None = None):
        return ft.Container(
            width=width,
            padding=22,
            border_radius=30,
            bgcolor=ft.Colors.with_opacity(0.78, ft.Colors.WHITE),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.74, ft.Colors.WHITE)),
            shadow=ft.BoxShadow(
                blur_radius=28,
                spread_radius=0,
                color=ft.Colors.with_opacity(0.12, C["dai"]),
                offset=ft.Offset(0, 10),
            ),
            content=ft.Column([
                ft.Row([
                    ft.Container(icon_image(icon_name, 24, 0.92), width=38, height=38, border_radius=18, bgcolor=ft.Colors.with_opacity(0.34, C["lotus"]), alignment=ft.Alignment.CENTER),
                    ft.Column([
                        ft.Text(title, size=self.ui_size(17), weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN),
                        ft.Text(subtitle, size=self.ui_size(11), color=C["sub"], font_family=FONT_CN),
                    ], spacing=1, expand=True),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Container(height=4),
                *controls,
            ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        )

    def settings_input_style(self):
        return {
            "border_radius": 18,
            "border_color": ft.Colors.with_opacity(0.52, C["line"]),
            "focused_border_color": C["dai"],
            "bgcolor": ft.Colors.with_opacity(0.62, ft.Colors.WHITE),
            "content_padding": ft.Padding(left=14, right=14, top=10, bottom=10),
            "text_style": ft.TextStyle(font_family=FONT_CN, color=C["ink"], size=self.ui_size(13)),
            "label_style": ft.TextStyle(font_family=FONT_CN, color=C["sub"], size=self.ui_size(11)),
        }

    def settings_textfield(self, label: str, value: str = "", width: int = 390, password: bool = False, hint_text: str = ""):
        return ft.TextField(
            label=label,
            value=value,
            width=width,
            password=password,
            can_reveal_password=password,
            hint_text=hint_text,
            **self.settings_input_style(),
        )

    def settings_dropdown(self, label: str, value: str, options: list, width: int = 390):
        return ft.Dropdown(
            label=label,
            value=value,
            width=width,
            options=options,
            border_radius=18,
            border_color=ft.Colors.with_opacity(0.52, C["line"]),
            focused_border_color=C["dai"],
            bgcolor=ft.Colors.with_opacity(0.62, ft.Colors.WHITE),
            content_padding=ft.Padding(left=14, right=14, top=8, bottom=8),
            text_style=ft.TextStyle(font_family=FONT_CN, color=C["ink"], size=self.ui_size(13)),
            label_style=ft.TextStyle(font_family=FONT_CN, color=C["sub"], size=self.ui_size(11)),
        )



    def show_settings(self) -> None:
        self.clear()
        self.page.padding = 0
        self.page.bgcolor = ft.Colors.WHITE

        provider = self.settings_dropdown(
            "模型服务商",
            self.config.provider,
            [
                ft.dropdown.Option("deepseek", "DeepSeek"),
                ft.dropdown.Option("mimo", "Xiaomi MiMo"),
            ],
            width=390,
        )
        model_policy = self.settings_dropdown(
            "叙事模式",
            self.config.model_policy,
            [
                ft.dropdown.Option("auto", "auto：普通回合用 Flash，重点回合用 Pro"),
                ft.dropdown.Option("flash", "固定 Flash"),
                ft.dropdown.Option("pro", "固定 Pro"),
                ft.dropdown.Option("custom", "固定 Custom"),
            ],
            width=390,
        )
        timeout_seconds = self.settings_textfield("超时时间（秒）", str(self.config.timeout_seconds), width=190)

        deepseek_api_key = self.settings_textfield("DeepSeek API Key", "", width=420, password=True, hint_text="sk-...")
        deepseek_base_url = self.settings_textfield("DeepSeek Base URL", self.config.base_url, width=420)
        deepseek_flash_model = self.settings_textfield("DeepSeek Flash Model", self.config.flash_model, width=420)
        deepseek_pro_model = self.settings_textfield("DeepSeek Pro Model", self.config.pro_model, width=420)
        deepseek_custom_model = self.settings_textfield("DeepSeek Custom Model", self.config.custom_model, width=420)

        mimo_api_key = self.settings_textfield("MiMo API Key", "", width=420, password=True, hint_text="mimo key")
        mimo_base_url = self.settings_textfield("MiMo Base URL", self.config.mimo_base_url, width=420)
        mimo_flash_model = self.settings_textfield("MiMo Flash Model", self.config.mimo_flash_model, width=420)
        mimo_pro_model = self.settings_textfield("MiMo Pro Model", self.config.mimo_pro_model, width=420)
        mimo_custom_model = self.settings_textfield("MiMo Custom Model", self.config.mimo_custom_model, width=420)

        status = ft.Text("", color=C["jade"], size=self.ui_size(13), font_family=FONT_CN)

        def save_settings(e=None):
            try:
                timeout_value = int(timeout_seconds.value or "120")
            except Exception:
                timeout_value = 120

            self.config.save(
                provider=provider.value or "deepseek",
                model_policy=model_policy.value or "auto",
                timeout_seconds=timeout_value,
                base_url=deepseek_base_url.value or "https://api.deepseek.com",
                flash_model=deepseek_flash_model.value or "deepseek-v4-flash",
                pro_model=deepseek_pro_model.value or "deepseek-v4-pro",
                custom_model=deepseek_custom_model.value or "deepseek-chat",
                mimo_base_url=mimo_base_url.value or "https://api.xiaomimimo.com/v1",
                mimo_flash_model=mimo_flash_model.value or "mimo-v2.5",
                mimo_pro_model=mimo_pro_model.value or "mimo-v2.5-pro",
                mimo_custom_model=mimo_custom_model.value or "mimo-v2.5-pro",
            )
            if deepseek_api_key.value:
                self.config.set_api_key(deepseek_api_key.value)
            if mimo_api_key.value:
                self.config.set_mimo_api_key(mimo_api_key.value)

            status.color = C["jade"]
            status.value = f"设置已保存。当前服务商：{self.config.provider_label()}。"
            self.page.update()

        def test_model(e, tier: str):
            save_settings(e)
            model = self.config.model_for_tier(tier)
            label = self.config.provider_label()
            status.color = C["dai"]
            status.value = f"正在测试 {label}：{model}"
            self.page.update()
            try:
                provider_obj = get_llm_provider(self.config)
                raw = provider_obj.generate(
                    [
                        {"role": "system", "content": "你是一个简洁的中文助手。"},
                        {"role": "user", "content": f"请只回复：{label} API 连接成功。"},
                    ],
                    model=model,
                )
                status.color = C["jade"]
                status.value = f"✅ 调用成功。服务商：{label}；模型：{model}；返回：{raw[:120]}"
            except Exception as exc:
                status.color = ft.Colors.RED
                status.value = f"❌ 调用失败：{exc}"
            self.page.update()

        def pill_button(label: str, icon_name: str, handler, fill=C["lotus"]):
            return ft.Container(
                padding=ft.Padding(left=15, right=15, top=10, bottom=10),
                border_radius=22,
                bgcolor=ft.Colors.with_opacity(0.84, fill),
                border=ft.Border.all(1, ft.Colors.with_opacity(0.58, ft.Colors.WHITE)),
                ink=True,
                on_click=handler,
                content=ft.Row([
                    icon_image(icon_name, 18, 0.9),
                    ft.Text(label, size=self.ui_size(12), color=C["ink"], weight=ft.FontWeight.W_600, font_family=FONT_CN),
                ], spacing=7, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            )

        top_bar = ft.Container(
            padding=ft.Padding(left=30, right=30, top=20, bottom=12),
            content=ft.Row([
                ft.Container(icon_image("settings", 30, 0.95), width=46, height=46, border_radius=18, bgcolor=ft.Colors.with_opacity(0.45, C["lotus"]), alignment=ft.Alignment.CENTER),
                ft.Column([
                    ft.Text("系统设置", size=self.ui_size(25), weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN),
                    ft.Text("模型服务商、API Key 与叙事模型配置", size=self.ui_size(12), color=C["sub"], font_family=FONT_CN),
                ], spacing=1),
                ft.Container(expand=True),
                pill_button("返回首页", "app_logo", lambda e: self.show_home(), ft.Colors.WHITE),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )

        guide_text = (
            "MiMo 使用 OpenAI 兼容的 /v1/chat/completions 接口。"
            "Base URL 默认填 https://api.xiaomimimo.com/v1；API Key 可用 MIMO_API_KEY 环境变量，"
            "也可以在这里保存。"
        )

        deepseek_card = self.settings_card(
            "DeepSeek",
            "保留原有接口配置",
            "api",
            [
                deepseek_api_key,
                deepseek_base_url,
                deepseek_flash_model,
                deepseek_pro_model,
                deepseek_custom_model,
            ],
            width=470,
        )
        mimo_card = self.settings_card(
            "Xiaomi MiMo",
            "新增小米大模型接口配置",
            "settings",
            [
                mimo_api_key,
                mimo_base_url,
                mimo_flash_model,
                mimo_pro_model,
                mimo_custom_model,
            ],
            width=470,
        )
        global_card = self.settings_card(
            "全局选择",
            "决定正式回合使用哪个服务商",
            "api",
            [
                provider,
                model_policy,
                timeout_seconds,
                ft.Text(guide_text, size=self.ui_size(12), color=C["sub"], font_family=FONT_CN, text_align=ft.TextAlign.CENTER),
                ft.Text("模型设置会持久保存；API Key 优先进入系统密钥环，失败时保存到用户配置目录。", size=self.ui_size(11), color=C["dai"], font_family=FONT_CN, text_align=ft.TextAlign.CENTER),
                ft.Row([
                    pill_button("保存设置", "save_archive", save_settings, C["jade"]),
                    pill_button("测试 Flash", "stage", lambda e: test_model(e, "flash"), C["lotus"]),
                    pill_button("测试 Pro", "contract", lambda e: test_model(e, "pro"), C["apricot"]),
                ], spacing=10, wrap=True, alignment=ft.MainAxisAlignment.CENTER),
                status,
            ],
            width=430,
        )

        settings_body = ft.Column([
            ft.Row([global_card, deepseek_card, mimo_card], spacing=18, alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.START),
        ], spacing=18, horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO)

        content = ft.Column([
            top_bar,
            ft.Container(
                expand=True,
                alignment=ft.Alignment.TOP_CENTER,
                padding=ft.Padding(left=34, right=34, top=18, bottom=30),
                content=settings_body,
            ),
        ], expand=True)

        self.page.add(ft.Stack([self.settings_page_bg(), content], expand=True))
        self.page.update()


    def normalize_character_name_key(self, name: Any) -> str:
        return re.sub(r"\s+", "", str(name or "").strip()).lower()

    def character_save_name(self, character: Dict[str, Any]) -> str:
        art = str(character.get("艺名") or "").strip()
        real = str(character.get("本名") or "").strip()
        return art or real or "星光练习室存档"

    def existing_character_name_keys(self) -> set[str]:
        keys: set[str] = set()
        try:
            saves = self.storage.list_saves()
        except Exception:
            logger.exception("list_saves failed for duplicate check")
            saves = []

        for item in saves:
            for raw in [item.get("name"), item.get("save_name")]:
                key = self.normalize_character_name_key(raw)
                if key:
                    keys.add(key)
            sid = item.get("id")
            if sid is None:
                continue
            try:
                state = self.storage.load_save(int(sid))
                ch = state.character if isinstance(state.character, dict) else {}
                for raw in [state.save_name, ch.get("艺名"), ch.get("本名")]:
                    key = self.normalize_character_name_key(raw)
                    if key:
                        keys.add(key)
            except Exception:
                continue
        return keys

    def validate_character_name_unique(self, character: Dict[str, Any]) -> list[str]:
        existing = self.existing_character_name_keys()
        errors: list[str] = []
        art = str(character.get("艺名") or "").strip()
        real = str(character.get("本名") or "").strip()
        save_name = self.character_save_name(character)
        for label, value in [("艺名", art), ("本名", real), ("存档名", save_name)]:
            key = self.normalize_character_name_key(value)
            if key and key in existing:
                errors.append(f"{label}“{value}”已经存在。请换一个名字，避免角色档案串档。")
        if art and real and self.normalize_character_name_key(art) == self.normalize_character_name_key(real):
            errors.append("艺名和本名不能完全一样。")
        return errors

    def random_character_names(self, nationality: str | None = None) -> Dict[str, str]:
        text = str(nationality or "").strip().lower()
        cn_surnames = ["林", "沈", "许", "温", "姜", "顾", "程", "苏", "夏", "宋", "陆", "白", "乔", "叶", "唐", "周"]
        cn_given = ["子恩", "若宁", "予夏", "知遥", "安禾", "念初", "芷晴", "沐言", "星眠", "南栀", "清梨", "云舒", "听澜", "以棠", "书妍", "洛笙"]
        kr_surnames = ["韩", "裴", "姜", "尹", "郑", "金", "申", "崔", "柳", "朴"]
        kr_given = ["夏恩", "智允", "瑞雅", "娜玹", "宥真", "多贤", "世琳", "恩序", "旼书", "艺琳", "秀妍", "采原"]
        jp_surnames = ["星野", "白石", "七濑", "樱井", "花泽", "月岛", "森川", "浅仓"]
        jp_given = ["遥", "凛", "美绪", "结夏", "千寻", "纱良", "优衣", "明里"]
        global_given = ["Mia", "Lia", "Nina", "Iris", "Luna", "Sena", "Rina", "Ari", "Ena", "Yuna", "Sora", "Mina"]
        stage_roots = ["Luna", "Sera", "Yuna", "Mina", "Rina", "Aria", "Navi", "Sia", "Lia", "Nari", "Moa", "Ena", "Rhea", "Ivy", "Nell", "Sori"]
        stage_suffix = ["", "", "", "a", "i", "e", "n", "ly", "star", "one"]
        existing = self.existing_character_name_keys()
        for _ in range(100):
            if any(x in text for x in ["韩国", "korea", "korean", "kr", "韩"]):
                real = random.choice(kr_surnames) + random.choice(kr_given)
            elif any(x in text for x in ["日本", "japan", "japanese", "jp", "日"]):
                real = random.choice(jp_surnames) + random.choice(jp_given)
            elif any(x in text for x in ["海外", "美国", "thai", "泰国", "global", "us", "english"]):
                real = random.choice(global_given)
            else:
                real = random.choice(cn_surnames) + random.choice(cn_given)
            art = random.choice(stage_roots) + random.choice(stage_suffix)
            if random.random() < 0.25:
                art = random.choice(["星禾", "浅月", "清梨", "知夏", "南音", "白露", "青栀", "月宁"])
            if self.normalize_character_name_key(real) not in existing and self.normalize_character_name_key(art) not in existing and self.normalize_character_name_key(real) != self.normalize_character_name_key(art):
                return {"艺名": art, "本名": real}
        stamp = random.randint(100, 999)
        return {"艺名": f"Stella{stamp}", "本名": f"星光练习生{stamp}"}

    def show_character_create(self) -> None:
        self.clear()
        fields: Dict[str, ft.TextField] = {}
        labels = ["艺名", "本名", "国籍", "年龄", "身高", "外貌特征", "性格", "爱好", "特长", "弱项", "家庭状况", "练习生经历", "在团定位", "你希望观众记住你的什么", "你不希望剧情触碰的内容", "其他补充"]
        for label in labels:
            fields[label] = ft.TextField(label=label, width=470)
        identity = ft.Dropdown(label="身份", width=470, options=[ft.dropdown.Option("素人学生被星探发现"), ft.dropdown.Option("富二代 / 优渥家庭出身"), ft.dropdown.Option("某位 KPOP 顶流爱豆的妹妹 / 亲属"), ft.dropdown.Option("海外追梦练习生"), ft.dropdown.Option("前运动员转型练习生"), ft.dropdown.Option("选秀节目淘汰者"), ft.dropdown.Option("小公司前成员 / 再出道"), ft.dropdown.Option("自定义身份")], value="素人学生被星探发现")
        source_tags = ft.TextField(label="出身来源标签，多个用逗号分隔", width=470, hint_text="街头星探, 校园舞蹈社, 前运动员")
        timeline = ft.Dropdown(label="时间线", width=470, options=[ft.dropdown.Option("练习生阶段"), ft.dropdown.Option("出道前一天"), ft.dropdown.Option("回归瓶颈期"), ft.dropdown.Option("续约前一年")], value="练习生阶段")
        period_mode = ft.Dropdown(
            label="生理周期系统（可关闭）",
            width=470,
            options=[ft.dropdown.Option("简化"), ft.dropdown.Option("开启"), ft.dropdown.Option("关闭")],
            value="简化",
            helper_text="开局选择。关闭后不会推进周期，也不会触发生理期事件；少女心事仍作为隐藏系统存在。",
        )
        status = ft.Text("", color=ft.Colors.RED)

        def randomize_names(e=None):
            names = self.random_character_names(fields["国籍"].value)
            fields["艺名"].value = names["艺名"]
            fields["本名"].value = names["本名"]
            status.color = C["dai"]
            status.value = f"已随机生成：艺名 {names['艺名']} / 本名 {names['本名']}。"
            self.page.update()

        def randomize_art_name(e=None):
            names = self.random_character_names(fields["国籍"].value)
            fields["艺名"].value = names["艺名"]
            status.color = C["dai"]
            status.value = f"已随机生成艺名：{names['艺名']}。"
            self.page.update()

        def check_duplicate(e=None):
            raw_character: Dict[str, Any] = {"身份": identity.value, "出身来源标签": [s.strip() for s in (source_tags.value or "").split(",") if s.strip()], "时间线": timeline.value, "生理周期系统": period_mode.value}
            for k, field in fields.items():
                raw_character[k] = field.value or ""
            raw_character["艺名"] = str(raw_character.get("艺名") or "").strip()
            raw_character["本名"] = str(raw_character.get("本名") or "").strip()
            errors = self.validate_character_name_unique(raw_character)
            if errors:
                status.color = ft.Colors.RED
                status.value = "重名校验未通过：\n" + "\n".join(f"• {x}" for x in errors)
            else:
                status.color = C["jade"]
                status.value = f"重名校验通过。存档将命名为：{self.character_save_name(raw_character)}"
            self.page.update()

        def create(e):
            raw_character: Dict[str, Any] = {"身份": identity.value, "出身来源标签": [s.strip() for s in (source_tags.value or "").split(",") if s.strip()], "时间线": timeline.value, "生理周期系统": period_mode.value}
            for k, field in fields.items():
                raw_character[k] = field.value or ""
            raw_character["艺名"] = str(raw_character.get("艺名") or "").strip()
            raw_character["本名"] = str(raw_character.get("本名") or "").strip()
            raw_character["国籍"] = str(raw_character.get("国籍") or "").strip()
            try:
                normalized = validate_character_input(raw_character)
            except CharacterValidationError as exc:
                status.color = ft.Colors.RED
                status.value = "角色创建信息有误：\n" + "\n".join(f"• {e}" for e in exc.errors)
                self.page.update()
                return

            normalized.data["艺名"] = str(normalized.data.get("艺名") or "").strip()
            normalized.data["本名"] = str(normalized.data.get("本名") or "").strip()
            duplicate_errors = self.validate_character_name_unique(normalized.data)
            if duplicate_errors:
                status.color = ft.Colors.RED
                status.value = "重名校验未通过：\n" + "\n".join(f"• {e}" for e in duplicate_errors)
                self.page.update()
                return

            if normalized.warnings:
                status.color = ft.Colors.ORANGE
                status.value = "提示：\n" + "\n".join(f"• {w}" for w in normalized.warnings)
                self.page.update()

            # 为新角色随机分配一个内置头像。头像文件会随完整包放在 assets/avatars/。
            normalized.data["avatar"] = self.random_avatar_path()
            engine = TurnEngine(self.storage, self.config)
            state = engine.create_initial_state(normalized.data)
            state.save_name = self.character_save_name(normalized.data)
            self.save_id = self.storage.create_save(state)
            self.state = state
            self.show_game(initial=True)

        period_card = ft.Container(
            padding=ft.Padding(left=16, right=16, top=12, bottom=12),
            border_radius=18,
            bgcolor=ft.Colors.with_opacity(0.70, ft.Colors.WHITE),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.55, C["lotus"])),
            content=ft.Column([
                ft.Text("身体系统设置", size=14, weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN),
                period_mode,
                ft.Text("这项只在角色创建时决定。想要完全不出现生理期，就选“关闭”。", size=12, color=C["sub"], font_family=FONT_CN),
            ], spacing=8),
        )
        name_tools = ft.Row([
            ft.Container(
                padding=ft.Padding(left=14, right=14, top=8, bottom=8),
                border_radius=18,
                bgcolor=ft.Colors.with_opacity(0.82, C["lotus"]),
                ink=True,
                on_click=randomize_names,
                content=ft.Row([icon_image("new_character", 18), ft.Text("随机姓名 / 艺名", size=12, color=C["ink"], font_family=FONT_CN, weight=ft.FontWeight.W_600)], spacing=6),
            ),
            ft.Container(
                padding=ft.Padding(left=14, right=14, top=8, bottom=8),
                border_radius=18,
                bgcolor=ft.Colors.with_opacity(0.78, ft.Colors.WHITE),
                border=ft.Border.all(1, ft.Colors.with_opacity(0.52, C["line"])),
                ink=True,
                on_click=randomize_art_name,
                content=ft.Row([icon_image("stage", 18), ft.Text("只随机艺名", size=12, color=C["dai"], font_family=FONT_CN, weight=ft.FontWeight.W_600)], spacing=6),
            ),
            ft.Container(
                padding=ft.Padding(left=14, right=14, top=8, bottom=8),
                border_radius=18,
                bgcolor=ft.Colors.with_opacity(0.78, ft.Colors.WHITE),
                border=ft.Border.all(1, ft.Colors.with_opacity(0.52, C["line"])),
                ink=True,
                on_click=check_duplicate,
                content=ft.Row([icon_image("save_archive", 18), ft.Text("检查重名", size=12, color=C["dai"], font_family=FONT_CN, weight=ft.FontWeight.W_600)], spacing=6),
            ),
        ], spacing=10, wrap=True)

        form = ft.Column([
            ft.Text("🎤 角色创建", size=28, weight=ft.FontWeight.BOLD, font_family=FONT_CN, color=C["ink"]),
            ft.Text("存档会优先使用艺名命名；没有艺名时使用本名。创建前会校验重名。", size=12, color=C["sub"], font_family=FONT_CN),
            name_tools,
            identity, source_tags, timeline, period_card, ft.Divider()
        ], spacing=10, scroll=ft.ScrollMode.AUTO)
        left, right = ft.Column(spacing=8), ft.Column(spacing=8)
        for i, label in enumerate(labels):
            (left if i % 2 == 0 else right).controls.append(fields[label])
        form.controls.append(ft.Row([left, right], spacing=24, vertical_alignment=ft.CrossAxisAlignment.START))
        form.controls.extend([ft.Row([ft.ElevatedButton("创建角色", icon=icon("PLAY_ARROW"), on_click=create), ft.OutlinedButton("返回首页", on_click=lambda e: self.show_home())]), status])
        self.page.add(ft.Container(content=form, padding=24, expand=True))
        self.page.update()

    def load_latest(self) -> None:
        save_id = self.storage.latest_save_id()
        if save_id is None:
            self.show_home()
            return
        self.save_id = save_id
        self.state = self.storage.load_save(save_id)
        self.show_game()

    def show_save_list(self) -> None:
        self.clear()
        saves = self.storage.list_saves()
        rows = []
        for item in saves:
            sid = item["id"]
            rows.append(ft.ListTile(title=ft.Text(f'{item["name"]}'), subtitle=ft.Text(f'ID {sid} · 更新时间 {item["updated_at"]}'), trailing=ft.Icon(icon("CHEVRON_RIGHT")), on_click=lambda e, save_id=sid: self.load_save_by_id(save_id)))
        self.page.add(ft.Container(content=ft.Column([ft.Text("存档列表", size=28, weight=ft.FontWeight.BOLD), ft.Column(rows) if rows else ft.Text("暂无存档。"), ft.OutlinedButton("返回首页", on_click=lambda e: self.show_home())], spacing=12, scroll=ft.ScrollMode.AUTO), padding=24))
        self.page.update()

    def load_save_by_id(self, save_id: int) -> None:
        self.save_id = save_id
        self.state = self.storage.load_save(save_id)
        self.show_game()


    def soft_card(self, content, padding: int = 16, radius: int = 24, bgcolor: str | None = None, expand: bool = False, width: int | None = None, height: int | None = None):
        return ft.Container(
            content=content,
            padding=padding,
            border_radius=radius,
            width=width,
            height=height,
            expand=expand,
            bgcolor=bgcolor or ft.Colors.with_opacity(0.78, ft.Colors.WHITE),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.72, ft.Colors.WHITE)),
            shadow=ft.BoxShadow(
                blur_radius=24,
                spread_radius=0,
                color=ft.Colors.with_opacity(0.10, "#536B89"),
                offset=ft.Offset(0, 8),
            ),
        )

    def section_title(self, icon_name: str, title: str, subtitle: str | None = None):
        items = [
            ft.Row([
                ft.Container(icon_image(icon_name, 22, 0.92), width=30, height=30, border_radius=15, bgcolor=ft.Colors.with_opacity(0.42, "#F7ECEE"), alignment=ft.Alignment.CENTER),
                ft.Text(title, size=16, weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        ]
        if subtitle:
            items.append(ft.Text(subtitle, size=self.ui_size(11), color=C["sub"], font_family=FONT_CN))
        return ft.Column(items, spacing=2)

    def metric_bar(self, label: str, value, icon_name: str = "app_logo", color: str = "#93C9B7", danger_high: bool = False):
        try:
            v = int(value)
        except Exception:
            v = 0
        v = max(0, min(100, v))
        active_color = color
        if danger_high and v >= 70:
            active_color = C["rouge"]
        elif (not danger_high) and v <= 25:
            active_color = C["apricot"]
        bar_w = 142
        fill_w = max(4, int(bar_w * v / 100))
        return ft.Container(
            padding=ft.Padding(left=2, right=2, top=4, bottom=4),
            content=ft.Row([
                ft.Container(icon_image(icon_name, 18, 0.9), width=26, height=26, border_radius=13, bgcolor=ft.Colors.with_opacity(0.38, "#F7ECEE"), alignment=ft.Alignment.CENTER),
                ft.Column([
                    ft.Row([
                        ft.Text(label, size=12, color=C["ink"], weight=ft.FontWeight.W_600, font_family=FONT_CN),
                        ft.Container(expand=True),
                        ft.Text(str(v), size=11, color=C["sub"], font_family=FONT_EN),
                    ], spacing=4),
                    ft.Stack([
                        ft.Container(width=bar_w, height=7, border_radius=8, bgcolor=ft.Colors.with_opacity(0.45, "#E8EAF4")),
                        ft.Container(width=fill_w, height=7, border_radius=8, bgcolor=ft.Colors.with_opacity(0.88, active_color)),
                    ], width=bar_w, height=7),
                ], spacing=4, expand=True),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )

    def mini_chip(self, text: str, color: str = "#9A8FC4"):
        return ft.Container(
            padding=ft.Padding(left=10, right=10, top=5, bottom=5),
            border_radius=14,
            bgcolor=ft.Colors.with_opacity(0.12, color),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.18, color)),
            content=ft.Text(text, size=11, color=C["ink"], font_family=FONT_CN),
        )


    def value_of(self, source: Dict[str, Any] | None, key: str, default=0):
        if not isinstance(source, dict):
            return default
        return source.get(key, default)

    def vget(self, source: Dict[str, Any] | None, *keys: str, default=0):
        if not isinstance(source, dict):
            return default
        for key in keys:
            if key in source:
                return source.get(key)
        return default

    def toggle_section(self, key: str) -> None:
        self.expanded_sections[key] = not self.expanded_sections.get(key, False)
        self.refresh_panels()
        self.page.update()

    def foldout_section(self, key: str, icon_name: str, title: str, subtitle: str, children: list, default_open: bool = False):
        expanded = self.expanded_sections.get(key, default_open)
        arrow = "⌃" if expanded else "⌄"
        header = ft.Container(
            padding=ft.Padding(left=8, right=8, top=8, bottom=8),
            border_radius=18,
            bgcolor=ft.Colors.with_opacity(0.34 if expanded else 0.22, ft.Colors.WHITE),
            on_click=lambda e, k=key: self.toggle_section(k),
            ink=True,
            content=ft.Row([
                ft.Container(icon_image(icon_name, 20, 0.92), width=30, height=30, border_radius=15, bgcolor=ft.Colors.with_opacity(0.34, "#F7ECEE"), alignment=ft.Alignment.CENTER),
                ft.Column([
                    ft.Text(title, size=15, weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN),
                    ft.Text(subtitle, size=10, color=C["sub"], font_family=FONT_CN, max_lines=1),
                ], spacing=0, expand=True),
                ft.Text(arrow, size=15, color=C["lavender"], font_family=FONT_EN),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )
        controls = [header]
        if expanded:
            controls.append(ft.Container(height=4))
            controls.extend(children)
        return ft.Container(
            padding=ft.Padding(left=8, right=8, top=8, bottom=10),
            border_radius=22,
            bgcolor=ft.Colors.with_opacity(0.34, ft.Colors.WHITE),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.48, ft.Colors.WHITE)),
            content=ft.Column(controls, spacing=6),
        )

    def text_line(self, label: str, value: Any, icon_name: str = "app_logo", color: str = "#9A8FC4"):
        return ft.Row([
            ft.Container(icon_image(icon_name, 16, 0.82), width=24, height=24, border_radius=12, bgcolor=ft.Colors.with_opacity(0.22, color), alignment=ft.Alignment.CENTER),
            ft.Text(label, size=12, color=C["ink"], font_family=FONT_CN, weight=ft.FontWeight.W_600),
            ft.Container(expand=True),
            ft.Text(str(value), size=12, color=C["sub"], font_family=FONT_CN, text_align=ft.TextAlign.RIGHT),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def chip_wrap(self, chips: list[str], color: str = "#9A8FC4", empty_text: str = "暂无记录"):
        if not chips:
            return ft.Text(empty_text, size=12, color=C["sub"], font_family=FONT_CN)
        return ft.Row([self.mini_chip(str(x)[:22], color) for x in chips[:18]], wrap=True, spacing=6, run_spacing=6)

    def event_to_title(self, event: Any) -> str:
        if isinstance(event, dict):
            return str(event.get("title") or event.get("code") or "")
        return str(getattr(event, "title", "") or getattr(event, "code", ""))

    def event_to_severity(self, event: Any) -> str:
        if isinstance(event, dict):
            return str(event.get("severity") or "")
        return str(getattr(event, "severity", "") or "")

    def player_debut_status(self, debut: Dict[str, Any] | None) -> str:
        if not isinstance(debut, dict):
            return "尚未开启"
        raw = str(debut.get("last_result") or debut.get("status") or "")
        mapping = {
            "not_candidate": "尚未开启",
            "not_ready": "继续准备",
            "candidate_deferred": "候选延期",
            "confirmed": "进入准备",
            "未进入出道候选窗口": "继续准备",
            "候选但延期": "候选延期",
            "进入出道准备": "进入准备",
        }
        return mapping.get(raw, raw or "尚未开启")

    def player_ending_status(self, ending: Dict[str, Any] | None, top_ending: Dict[str, Any] | None = None) -> str:
        if isinstance(top_ending, dict) and top_ending.get("name"):
            return str(top_ending.get("name"))
        if not isinstance(ending, dict):
            return "尚未开启"
        raw = str(ending.get("window") or ending.get("status") or "")
        mapping = {
            "closed": "尚未开启",
            "open": "正在形成",
            "ongoing": "仍在路上",
            "resolved": "阶段落定",
        }
        return mapping.get(raw, raw or "尚未开启")

    def turn_kind_label(self, kind: Any) -> str:
        text = str(kind or "")
        mapping = {
            "ordinary": "日常推进",
            "focus": "重点回合",
            "crisis": "事件窗口",
            "summary": "阶段总结",
            "fast_forward": "快进回合",
        }
        return mapping.get(text, text or "日常推进")

    def event_to_source(self, event: Any) -> str:
        if isinstance(event, dict):
            return str(event.get("source_system") or "")
        return str(getattr(event, "source_system", "") or "")

    def is_hidden_system_event(self, event: Any) -> bool:
        source = self.event_to_source(event)
        title = self.event_to_title(event)
        hidden_words = ["少女心事", "心事阈值", "秘密重量", "心动线索"]
        return source == "inner_life" or any(w in title for w in hidden_words)


    def random_avatar_path(self) -> str:
        return f"avatars/avatar_{random.randint(1, 36):03d}.png"

    def get_character_avatar_src(self) -> str:
        if self.state is None:
            return asset("avatars/avatar_001.png")
        if not isinstance(self.state.character, dict):
            return asset("avatars/avatar_001.png")
        avatar = str(self.state.character.get("avatar") or "").strip()
        if not avatar or not asset_exists(avatar):
            avatar = avatar_src_from_character(self.state.character)
            # Store the fallback path in memory so the same session does not flicker.
            self.state.character["avatar"] = avatar
        return asset(avatar)

    def character_identity_card(self) -> ft.Container:
        s = self.state
        if s is None:
            return ft.Container()
        ch = s.character if isinstance(s.character, dict) else {}
        art_name = str(ch.get("艺名") or ch.get("本名") or s.save_name or "练习生")
        real_name = str(ch.get("本名") or "").strip()
        age = ch.get("年龄", "未知")
        nationality = str(ch.get("国籍") or "未填写")
        identity = str(ch.get("身份") or "练习生")
        mainline = str(s.current_mainline or "日常推进")
        exam_countdown = "考核未知"
        try:
            if isinstance(s.time, dict):
                exam_countdown = f"考核 {s.time.get('assessment_countdown_days', '未知')} 天"
        except Exception:
            pass

        return ft.Container(
            width=430,
            padding=ft.Padding(left=14, right=14, top=8, bottom=8),
            border_radius=24,
            bgcolor=ft.Colors.with_opacity(0.62, ft.Colors.WHITE),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.48, C["line"])),
            shadow=ft.BoxShadow(
                blur_radius=24,
                spread_radius=0,
                color=ft.Colors.with_opacity(0.08, C["dai"]),
                offset=ft.Offset(0, 8),
            ),
            content=ft.Row([
                ft.Stack([
                    ft.Container(
                        content=ft.Image(src=self.get_character_avatar_src(), width=54, height=54, fit="cover"),
                        width=54,
                        height=54,
                        border_radius=18,
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                        border=ft.Border.all(1, ft.Colors.with_opacity(0.58, ft.Colors.WHITE)),
                    ),
                    ft.Container(
                        content=ft.Image(src=flag_src_from_nationality(nationality), width=20, height=20, fit="cover"),
                        width=24,
                        height=24,
                        border_radius=12,
                        bgcolor=ft.Colors.WHITE,
                        alignment=ft.Alignment.CENTER,
                        left=36,
                        top=36,
                    ),
                ], width=62, height=62),
                ft.Column([
                    ft.Row([
                        ft.Text(art_name, size=16, weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN, max_lines=1),
                        self.mini_chip(f"{nationality}", C["jade"]),
                        self.mini_chip(f"{age}岁", C["lotus"]),
                    ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Text(
                        f"{real_name + ' · ' if real_name and real_name != art_name else ''}{identity}",
                        size=11,
                        color=C["sub"],
                        font_family=FONT_CN,
                        max_lines=1,
                    ),
                    ft.Text(
                        f"{s.current_stage} · 第 {s.turn} 回合 · {exam_countdown} · {mainline}",
                        size=11,
                        color=C["dai"],
                        font_family=FONT_CN,
                        max_lines=1,
                    ),
                ], spacing=2, expand=True),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )

    def toggle_alert_tray(self, e=None) -> None:
        self.alerts_expanded = not self.alerts_expanded
        self.refresh_pinned_alerts()
        self.page.update()

    def collect_pinned_alerts(self) -> list[Dict[str, str]]:
        if self.state is None:
            return []
        s = self.state
        alerts: list[Dict[str, str]] = []
        seen: set[str] = set()

        def add(title: str, detail: str, level: str = "warning", icon_name: str = "crisis_pr"):
            title = (title or "").strip()
            if not title or title in seen:
                return
            seen.add(title)
            alerts.append({"title": title, "detail": detail or "需要优先处理。", "level": level, "icon": icon_name})

        for c in getattr(s, "active_crises", []) or []:
            stage = str(getattr(c, "stage", ""))
            if stage not in {"closed", "converted"}:
                add(str(getattr(c, "title", "重大事件窗口")), f"当前阶段：{stage}。处理不当会持续影响后续回合。", "crisis", "crisis_pr")

        important_words = ["窗口", "危机", "考核", "到来", "强制", "警告", "私生", "跟踪", "骚扰", "霸凌", "边界", "曝光", "伤病", "回应"]
        for ev in list(getattr(s, "system_events", []) or [])[-12:]:
            if self.is_hidden_system_event(ev):
                continue
            title = self.event_to_title(ev)
            sev = self.event_to_severity(ev)
            if sev in {"crisis", "warning"} or any(w in title for w in important_words):
                icon_name = "safety" if any(w in title for w in ["私生", "跟踪", "骚扰", "霸凌", "安全"]) else "crisis_pr"
                add(title, "这是系统保留提示，不会被折叠。", "crisis" if sev == "crisis" else "warning", icon_name)

        for flag in list(getattr(s, "flags", []) or [])[-20:]:
            flag_text = str(flag)
            if any(w in flag_text for w in important_words):
                add(flag_text, "长期记录中存在需要关注的风险或窗口。", "warning", "diary")

        return alerts[:12]

    def refresh_pinned_alerts(self) -> None:
        if self.pinned_alerts is None:
            return
        alerts = self.collect_pinned_alerts()
        self.pinned_alerts.controls.clear()
        if not alerts:
            self.pinned_alerts.visible = False
            return

        self.pinned_alerts.visible = True
        crisis_count = sum(1 for item in alerts if item.get("level") == "crisis")
        warning_count = max(0, len(alerts) - crisis_count)
        first = alerts[0]
        color = C["rouge"] if crisis_count else C["apricot"]
        summary_text = f"当前有 {len(alerts)} 条提醒"
        if crisis_count:
            summary_text += f" · {crisis_count} 条高优先级"
        if warning_count:
            summary_text += f" · {warning_count} 条普通提醒"

        summary = ft.Container(
            padding=ft.Padding(left=14, right=14, top=10, bottom=10),
            border_radius=20,
            bgcolor=ft.Colors.with_opacity(0.82, "#FFF9F3"),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.42, color)),
            ink=True,
            on_click=self.toggle_alert_tray,
            content=ft.Row([
                ft.Container(icon_image(first.get("icon", "crisis_pr"), 22, 0.92), width=34, height=34, border_radius=17, bgcolor=ft.Colors.with_opacity(0.24, color), alignment=ft.Alignment.CENTER),
                ft.Column([
                    ft.Text(summary_text, size=13, weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN, max_lines=1),
                    ft.Text(first.get("title", "有新的状态提醒"), size=11, color=C["sub"], font_family=FONT_CN, max_lines=1),
                ], spacing=1, expand=True),
                ft.Text("收起" if self.alerts_expanded else "展开", size=12, color=C["dai"], font_family=FONT_CN),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )
        self.pinned_alerts.controls.append(summary)

        if not self.alerts_expanded:
            return

        cards = []
        for item in alerts:
            item_color = C["rouge"] if item["level"] == "crisis" else C["apricot"]
            cards.append(
                ft.Container(
                    padding=ft.Padding(left=12, right=12, top=9, bottom=9),
                    border_radius=18,
                    bgcolor=ft.Colors.with_opacity(0.76, ft.Colors.WHITE),
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.32, item_color)),
                    content=ft.Row([
                        ft.Container(icon_image(item["icon"], 20, 0.88), width=30, height=30, border_radius=15, bgcolor=ft.Colors.with_opacity(0.20, item_color), alignment=ft.Alignment.CENTER),
                        ft.Column([
                            ft.Text(item["title"], size=12, weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN, max_lines=1),
                            ft.Text(item["detail"], size=10, color=C["sub"], font_family=FONT_CN, max_lines=1),
                        ], spacing=1, expand=True),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                )
            )
        self.pinned_alerts.controls.append(ft.Row(cards, wrap=True, spacing=8, run_spacing=8))

    def build_turn_summary(self, applied: Dict[str, Any] | None = None, system_events: list | None = None, validation=None, route_info=None, action: str | None = None) -> ft.Column:
        lines = []
        if action:
            cleaned = action.strip()
            if cleaned:
                lines.append(("本回合选择：" + cleaned[:120], C["apricot"]))
        if validation is not None and getattr(validation, "normalized_action", None) != getattr(validation, "original_action", None):
            lines.append(("行动已被规则修正", C["apricot"]))
        if applied:
            changes = []
            for key, (old, new) in list(applied.items())[:8]:
                delta = new - old
                if delta == 0:
                    continue
                name = key.split(".")[-1]
                sign = "+" if delta > 0 else ""
                changes.append(f"{name} {sign}{delta}")
            if changes:
                lines.append(("状态变化：" + "，".join(changes), C["jade"]))
        important_events = []
        if system_events:
            for ev in system_events:
                if self.is_hidden_system_event(ev):
                    continue
                title = getattr(ev, "title", "")
                if title and title not in important_events:
                    important_events.append(title)
                if len(important_events) >= 5:
                    break
        if important_events:
            lines.append(("本回合提醒：" + "；".join(important_events), C["lavender"]))
        if route_info is not None:
            kind = getattr(route_info, "turn_kind", "ordinary")
            label = {"ordinary": "日常推进", "focus": "重点回合", "crisis": "危机处理", "mainline": "主线节点"}.get(kind, kind)
            lines.append((f"回合类型：{label}", C["dai"]))
        if not lines:
            lines.append(("本回合已记录。当前状态稳定，下一步可以继续选择行动。", C["sub"]))
        summary_text = "\n".join(f"• {text}" for text, color in lines)
        return self.readonly_story_text(summary_text, min_lines=3, max_lines=8)

    def story_block(self, title: str, subtitle: str, icon_name: str, body_control, accent: str = "#9A8FC4"):
        return ft.Container(
            expand=True,
            content=self.soft_card(
                ft.Column([
                    ft.Row([
                        ft.Container(icon_image(icon_name, 24, 0.92), width=36, height=36, border_radius=18, bgcolor=ft.Colors.with_opacity(0.35, accent), alignment=ft.Alignment.CENTER),
                        ft.Column([
                            ft.Text(title, size=self.ui_size(17), weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN),
                            ft.Text(subtitle, size=self.ui_size(11), color=C["sub"], font_family=FONT_CN),
                        ], spacing=0, expand=True),
                    ], spacing=10),
                    body_control,
                ], spacing=12, expand=True),
                padding=18,
                radius=24,
                bgcolor=ft.Colors.with_opacity(0.84, ft.Colors.WHITE),
                expand=True,
            ),
        )

    def display_narrative_from_response_data(self, data: Dict[str, Any] | None, fallback: str = "") -> str:
        if not isinstance(data, dict):
            return fallback or "练习室的灯还亮着。你把今天的状态写进心里，然后等待下一步选择。"

        def stringify(value) -> str:
            if value is None:
                return ""
            if isinstance(value, str):
                return value.strip()
            if isinstance(value, list):
                parts = []
                for item in value:
                    if isinstance(item, dict):
                        parts.append(stringify(item.get("reaction") or item.get("text") or item.get("content") or item.get("body")))
                    else:
                        parts.append(stringify(item))
                return "\n".join(p for p in parts if p)
            if isinstance(value, dict):
                for key in ["narrative", "text", "content", "body", "正文", "剧情", "推进情节"]:
                    if key in value and stringify(value.get(key)):
                        return stringify(value.get(key))
                return "\n".join(stringify(v) for v in value.values() if stringify(v))
            return str(value).strip()

        for key in ["narrative", "推进情节", "本回合剧情", "剧情", "正文", "story", "main_story", "main_text", "content", "text"]:
            txt = self.normalize_visible_text(stringify(data.get(key)))
            if txt:
                return txt

        parts = []
        summary = stringify(data.get("public_summary") or data.get("回合总结") or data.get("summary"))
        if summary:
            parts.append(summary)
        reactions = data.get("npc_reactions") or data.get("NPC反应") or data.get("reactions")
        react_text = stringify(reactions)
        if react_text:
            parts.append(react_text)
        merged = "\n".join(parts).strip()
        return self.fallback_story_text(merged or fallback)

    def display_narrative_from_response(self, response) -> str:
        """Extract narrative for UI using direct attributes first.

        This avoids a blank center card when a model/provider returns valid text,
        but Pydantic dump/alias conversion or zero-width characters make the old
        display path treat the body as empty.
        """
        direct = self.normalize_visible_text(getattr(response, "narrative", ""))
        if direct:
            return direct

        summary = self.normalize_visible_text(getattr(response, "public_summary", ""))
        if summary:
            return summary

        reactions = []
        for r in list(getattr(response, "npc_reactions", []) or [])[:4]:
            reactions.append(self.normalize_visible_text(getattr(r, "reaction", "")))
        reaction_text = "\n".join(x for x in reactions if x)
        if reaction_text:
            return reaction_text

        data = {}
        try:
            data = response.model_dump()
        except Exception:
            data = {
                "narrative": getattr(response, "narrative", ""),
                "public_summary": getattr(response, "public_summary", ""),
                "npc_reactions": [getattr(r, "model_dump", lambda: r)() for r in getattr(response, "npc_reactions", [])],
            }
        return self.display_narrative_from_response_data(data)

    def normalize_visible_text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (list, tuple)):
            parts = [self.normalize_visible_text(v) for v in value]
            return "\n".join(p for p in parts if p)
        if isinstance(value, dict):
            parts = [self.normalize_visible_text(v) for v in value.values()]
            return "\n".join(p for p in parts if p)
        text = str(value)
        for bad in ["\u200b", "\u200c", "\u200d", "\ufeff", "\x00"]:
            text = text.replace(bad, "")
        text = text.replace("```json", "").replace("```", "")
        return text.strip()

    def fallback_story_text(self, candidate: Any = "") -> str:
        text = self.normalize_visible_text(candidate)
        if text:
            return text
        if self.state is not None:
            last = self.normalize_visible_text(getattr(self.state, "last_public_summary", ""))
            if last:
                return last
        return "这一回合已经记录下来。练习室的灯还亮着，你可以先查看本回合总结，再决定下一步。"

    def readonly_story_text(self, text: str, min_lines: int = 5, max_lines: int = 18):
        """Render long story text through an expanded read-only TextField.

        Do not calculate width from page.width here. On Windows high-DPI scaling,
        Flet page.width is logical pixels while the center panel is laid out by
        expand; subtracting fixed side-panel widths makes the text field too
        narrow. A Row with an expanded TextField follows the actual parent width.
        """
        value = self.fallback_story_text(text)
        field = ft.TextField(
            value=value,
            expand=True,
            read_only=True,
            multiline=True,
            min_lines=min_lines,
            max_lines=max_lines,
            border_color=ft.Colors.TRANSPARENT,
            focused_border_color=ft.Colors.TRANSPARENT,
            cursor_color=ft.Colors.TRANSPARENT,
            text_style=ft.TextStyle(font_family=FONT_CN, color=C["ink"], size=13.5),
            bgcolor=ft.Colors.with_opacity(0.00, ft.Colors.WHITE),
        )
        return ft.Container(
            expand=True,
            padding=ft.Padding(left=10, right=10, top=8, bottom=8),
            border_radius=16,
            bgcolor=ft.Colors.with_opacity(0.18, ft.Colors.WHITE),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.22, C["line"])),
            content=ft.Row([field], expand=True, spacing=0),
        )

    def split_visible_lines(self, text: str, line_limit: int = 42) -> list[str]:
        """Split Chinese/English mixed text into short visible lines.

        Flet 0.85 occasionally fails to paint long selectable Text blocks inside
        nested glass cards. We avoid that renderer path by feeding it many short
        non-selectable lines with explicit width constraints.
        """
        text = self.normalize_visible_text(text)
        if not text:
            return []
        lines: list[str] = []
        for para in text.split("\n"):
            para = para.strip()
            if not para:
                continue
            buf = ""
            for ch in para:
                buf += ch
                # Chinese punctuation should close the line naturally.
                if len(buf) >= line_limit or (len(buf) >= 24 and ch in "。！？；"):
                    lines.append(buf.strip())
                    buf = ""
            if buf.strip():
                lines.append(buf.strip())
            # Preserve paragraph breathing room.
            if lines and lines[-1] != "":
                lines.append("")
        while lines and lines[-1] == "":
            lines.pop()
        return lines

    def narrative_body_control(self, narrative_text: str):
        lines = self.split_visible_lines(narrative_text, line_limit=44)
        if not lines:
            lines = ["这一回合已经记录下来。练习室的灯还亮着，你可以先查看本回合总结，再决定下一步。"]

        controls = []
        for line in lines[:90]:
            if line == "":
                controls.append(ft.Container(height=6))
                continue
            controls.append(
                ft.Text(
                    line,
                    size=13,
                    color=C["ink"],
                    font_family=FONT_CN,
                    height=1.42,
                    selectable=False,
                    no_wrap=False,
                )
            )
        if len(lines) > 90:
            controls.append(ft.Text("……正文较长，已截断显示。", size=12, color=C["sub"], font_family=FONT_CN))

        return ft.Container(
            padding=ft.Padding(left=4, right=4, top=2, bottom=2),
            content=ft.Column(controls, spacing=2, tight=True),
        )

    def add_story_pair(self, narrative: str, summary_control=None, replace: bool = False) -> None:
        if replace:
            self.story_view.controls.clear()
        narrative_text = self.fallback_story_text(narrative)
        narrative_body = self.readonly_story_text(narrative_text, min_lines=8, max_lines=18)
        self.story_view.controls.append(self.story_block("推进情节", "练习室里的这一回合", "diary", narrative_body, C["lotus"]))
        if summary_control is None:
            summary_control = self.build_turn_summary()
        self.story_view.controls.append(self.story_block("回合总结", "状态、风险与下一步提醒", "schedule", summary_control, C["jade"]))

    def set_story_pair(self, narrative: str, summary_control=None) -> None:
        self.add_story_pair(narrative, summary_control, replace=True)


    def render_recent_turns(self, limit: int = 1) -> bool:
        """Render recent saved turn narratives after loading a save.

        The save table only stores the latest GameState. The actual generated
        narrative lives in the turns table, so loading a save without reading
        recent turns makes the center panel look empty or generic.
        """
        if self.save_id is None:
            return False
        try:
            with self.storage.connect() as conn:
                rows = conn.execute(
                    """
                    SELECT turn_no, player_action, response_json, applied_diff_json, route_json, system_events_json
                    FROM turns
                    WHERE save_id=?
                    ORDER BY turn_no DESC
                    LIMIT ?
                    """,
                    (self.save_id, limit),
                ).fetchall()
        except Exception:
            logger.exception("render_recent_turns query failed")
            return False

        if not rows:
            return False

        for row in reversed(rows):
            try:
                response_data = json.loads(row["response_json"] or "{}")
            except Exception:
                response_data = {}
            narrative = self.display_narrative_from_response_data(response_data, "这一回合已经记录。")

            try:
                applied = json.loads(row["applied_diff_json"] or "{}")
            except Exception:
                applied = {}
            try:
                events = json.loads(row["system_events_json"] or "[]")
            except Exception:
                events = []
            try:
                route_data = json.loads(row["route_json"] or "{}")
            except Exception:
                route_data = {}

            summary = self.build_turn_summary_from_raw(
                action=row["player_action"],
                applied=applied,
                events=events,
                route_data=route_data,
            )
            self.set_story_pair(narrative, summary)
        return True

    def build_turn_summary_from_raw(self, action: str, applied: Dict[str, Any] | None = None, events: list | None = None, route_data: Dict[str, Any] | None = None) -> ft.Column:
        lines = []
        if action:
            lines.append(("本回合选择：" + action.strip()[:120], C["apricot"]))
        if applied:
            changes = []
            for key, value in list(applied.items())[:8]:
                try:
                    old, new = value
                    delta = int(new) - int(old)
                except Exception:
                    continue
                if delta == 0:
                    continue
                name = key.split(".")[-1]
                sign = "+" if delta > 0 else ""
                changes.append(f"{name} {sign}{delta}")
            if changes:
                lines.append(("状态变化：" + "，".join(changes), C["jade"]))
        if events:
            titles = []
            for ev in events:
                if self.is_hidden_system_event(ev):
                    continue
                title = ev.get("title") if isinstance(ev, dict) else getattr(ev, "title", "")
                if title and title not in titles:
                    titles.append(title)
                if len(titles) >= 5:
                    break
            if titles:
                lines.append(("本回合提醒：" + "；".join(titles), C["lavender"]))
        if route_data:
            kind = route_data.get("turn_kind", "ordinary")
            label = {"ordinary": "日常推进", "focus": "重点回合", "crisis": "危机处理", "mainline": "主线节点"}.get(kind, kind)
            lines.append((f"回合类型：{label}", C["dai"]))
        if not lines:
            lines.append(("本回合已记录。当前状态稳定，下一步可以继续选择行动。", C["sub"]))
        summary_text = "\n".join(f"• {text}" for text, color in lines)
        return self.readonly_story_text(summary_text, min_lines=3, max_lines=8)

    def run_in_background(self, fn) -> None:
        """Run 叙事引擎 turn generation without blocking the UI event handler."""
        if hasattr(self.page, "run_thread"):
            try:
                self.page.run_thread(fn)
                return
            except TypeError:
                pass
            except Exception:
                logger.exception("page.run_thread failed; fallback to threading.Thread")
        threading.Thread(target=fn, daemon=True).start()

    def init_audio(self) -> None:
        if self.bgm_audio is not None:
            return
        if not hasattr(ft, "Audio"):
            return
        try:
            self.bgm_audio = ft.Audio(src=asset("audio/home_bgm.wav"), autoplay=False, volume=0.25)
            self.page.overlay.append(self.bgm_audio)
        except Exception:
            self.bgm_audio = None

    def toggle_bgm(self, e=None) -> None:
        self.init_audio()
        if self.bgm_audio is None:
            self.snack("当前 Flet 环境不支持内置 BGM，或没有找到 audio/home_bgm.wav。")
            return
        try:
            if self.bgm_enabled:
                if hasattr(self.bgm_audio, "pause"):
                    self.bgm_audio.pause()
                self.bgm_enabled = False
            else:
                if hasattr(self.bgm_audio, "play"):
                    self.bgm_audio.play()
                self.bgm_enabled = True
            if self.bgm_button_label is not None:
                self.bgm_button_label.value = "音乐开" if self.bgm_enabled else "音乐关"
            elif self.bgm_button is not None and hasattr(self.bgm_button, "text"):
                self.bgm_button.text = "♪ 音乐开" if self.bgm_enabled else "♪ 音乐关"
            self.page.update()
        except Exception as exc:
            self.snack(f"BGM 播放失败：{exc}")

    def set_generating(self, value: bool) -> None:
        self.is_generating = value
        if self.thinking_banner is not None:
            self.thinking_banner.visible = value
        for btn in self.choice_buttons:
            try:
                btn.disabled = value
            except Exception:
                pass
        if self.submit_button is not None:
            self.submit_button.disabled = value
            self.submit_button.text = "生成中……" if value else "提交行动"
        if self.custom_input is not None:
            self.custom_input.disabled = value
        self.page.update()

    def show_game(self, initial: bool = False) -> None:
        if self.state is None:
            self.show_home()
            return
        self.clear()
        self.page.padding = 0
        self.page.bgcolor = "#FBFCFF"
        self.is_generating = False
        self.choice_buttons = []
        self.story_view = ft.Column(expand=True, spacing=16)
        self.left_panel = ft.Column(width=300, scroll=ft.ScrollMode.AUTO, spacing=12)
        self.right_panel = ft.Column(width=320, scroll=ft.ScrollMode.AUTO, spacing=12)
        self.choice_row = ft.Column(spacing=10)
        self.pinned_alerts = ft.Column(spacing=8, visible=False)
        self.alerts_expanded = False
        self.custom_input = ft.TextField(
            label="自定义行动",
            hint_text="写下这一回合你想做的事。生成中请等待，不要重复点击。",
            multiline=True,
            min_lines=2,
            max_lines=3,
            expand=True,
            border_color="#DDE2EC",
            focused_border_color=C["lavender"],
            text_style=ft.TextStyle(font_family=FONT_CN, color=C["ink"], size=14),
        )
        first_text = "角色创建完成。练习室的灯已经亮起，你可以从下方选择第一步。" if initial or self.state.turn == 0 else self.fallback_story_text(getattr(self.state, "last_public_summary", "存档已载入。"))
        if initial or self.state.turn == 0:
            self.set_story_pair(first_text)
        else:
            if not self.render_recent_turns(limit=1):
                self.set_story_pair(first_text)
        self.refresh_panels()
        self.refresh_choices()
        self.init_audio()

        route = self.state.route_history[-1] if self.state.route_history else None

        def top_nav_button(label: str, icon_name: str, handler, active: bool = False):
            return ft.Container(
                height=38,
                padding=ft.Padding(left=12, right=13, top=6, bottom=6),
                border_radius=19,
                bgcolor=ft.Colors.with_opacity(0.78 if not active else 0.92, ft.Colors.WHITE),
                border=ft.Border.all(1, ft.Colors.with_opacity(0.62, C["line"])),
                shadow=ft.BoxShadow(
                    blur_radius=16,
                    spread_radius=0,
                    color=ft.Colors.with_opacity(0.08, C["dai"]),
                    offset=ft.Offset(0, 5),
                ),
                ink=True,
                on_click=handler,
                content=ft.Row([
                    ft.Container(
                        icon_image(icon_name, 18, 0.88),
                        width=23,
                        height=23,
                        border_radius=12,
                        bgcolor=ft.Colors.with_opacity(0.24, C["lotus"] if not active else C["jade"]),
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Text(label, size=12, color=C["dai"], weight=ft.FontWeight.W_600, font_family=FONT_CN),
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER),
            )

        self.bgm_button_label = ft.Text("音乐开" if self.bgm_enabled else "音乐关", size=12, color=C["dai"], weight=ft.FontWeight.W_600, font_family=FONT_CN)
        self.bgm_button = ft.Container(
            height=38,
            padding=ft.Padding(left=12, right=13, top=6, bottom=6),
            border_radius=19,
            bgcolor=ft.Colors.with_opacity(0.78, ft.Colors.WHITE),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.62, C["line"])),
            shadow=ft.BoxShadow(
                blur_radius=16,
                spread_radius=0,
                color=ft.Colors.with_opacity(0.08, C["dai"]),
                offset=ft.Offset(0, 5),
            ),
            ink=True,
            on_click=self.toggle_bgm,
            content=ft.Row([
                ft.Container(
                    icon_image("music", 18, 0.88),
                    width=23,
                    height=23,
                    border_radius=12,
                    bgcolor=ft.Colors.with_opacity(0.24, C["lotus"]),
                    alignment=ft.Alignment.CENTER,
                ),
                self.bgm_button_label,
            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER),
        )

        top_bar = ft.Container(
            padding=ft.Padding(left=18, right=18, top=10, bottom=10),
            content=ft.Row([
                ft.Row([
                    ft.Container(icon_image("app_logo", 34), width=42, height=42, border_radius=16, bgcolor=ft.Colors.with_opacity(0.36, "#F7ECEE"), alignment=ft.Alignment.CENTER),
                    ft.Column([
                        ft.Text("星光练习室", size=22, weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN),
                        ft.Text("Starlight Practice Room", size=11, italic=True, color=C["lavender"], font_family=FONT_EN),
                    ], spacing=0),
                    self.mini_chip(f"{route.turn_kind if route else '准备中'}", C["lotus"]),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Container(expand=True),
                self.character_identity_card(),
                ft.Container(expand=True),
                ft.Row([
                    self.bgm_button,
                    top_nav_button("设置", "settings", lambda e: self.show_settings()),
                    top_nav_button("存档", "save_archive", lambda e: self.show_save_list()),
                    top_nav_button("首页", "app_logo", lambda e: self.show_home(), active=True),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )

        self.thinking_banner = ft.Container(
            visible=False,
            padding=ft.Padding(left=16, right=16, top=12, bottom=12),
            border_radius=18,
            bgcolor=ft.Colors.with_opacity(0.90, "#FFF9F3"),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.50, C["lotus"])),
            content=ft.Row([
                ft.ProgressRing(width=20, height=20, stroke_width=3, color=C["lavender"]),
                ft.Text("星光正在生成中……请等待本回合完成，不要重复提交。", size=13, color=C["ink"], font_family=FONT_CN),
            ], spacing=10),
        )

        main_row = ft.Row([
            self.soft_card(self.left_panel, padding=14, radius=26, bgcolor=ft.Colors.with_opacity(0.72, ft.Colors.WHITE), width=322),
            ft.Container(content=self.story_view, expand=True, padding=ft.Padding(left=10, right=10, top=4, bottom=4)),
            self.soft_card(self.right_panel, padding=14, radius=26, bgcolor=ft.Colors.with_opacity(0.72, ft.Colors.WHITE), width=342),
        ], expand=True, spacing=14, vertical_alignment=ft.CrossAxisAlignment.STRETCH)

        bottom = self.soft_card(self.choice_row, padding=14, radius=24, bgcolor=ft.Colors.with_opacity(0.78, ft.Colors.WHITE))

        game_content = ft.Container(
            expand=True,
            padding=ft.Padding(left=16, right=16, top=10, bottom=14),
            content=ft.Column([top_bar, self.thinking_banner, self.pinned_alerts, main_row, bottom], expand=True, spacing=10),
        )
        game_bg = ft.Stack([
            ft.Image(src=asset("backgrounds/game_bg.png"), fit="cover", expand=True, opacity=1.0),
            ft.Container(expand=True, bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE)),
            game_content,
        ], expand=True)
        self.page.add(game_bg)
        self.page.update()

    def refresh_panels(self) -> None:
        assert self.state is not None
        s = self.state
        self.left_panel.controls.clear()
        self.right_panel.controls.clear()
        self.refresh_pinned_alerts()

        body = s.body or {}
        mind = s.mind or {}
        career = s.career or {}
        company = s.company or {}
        team = s.team or {}
        fans = s.fans or {}
        risks = s.risks or {}
        talents = getattr(s, "talents", {}) or {}
        abilities = list(getattr(s, "abilities", []) or [])
        route = s.route_history[-1] if s.route_history else None

        overview_children = [
            self.text_line("回合", s.turn, "schedule", C["lotus"]),
            self.text_line("阶段", s.current_stage, "stage", C["lavender"]),
            self.text_line("主线", s.current_mainline, "diary", C["jade"]),
            self.text_line("行程", s.current_schedule, "calendar" if False else "schedule", C["apricot"]),
            self.text_line("日期", s.time.get("current_date"), "schedule", C["jade"]),
            self.text_line("本回合", f"{s.time.get('turn_duration_days')} 天", "schedule", C["lotus"]),
            self.text_line("年龄段", f"{s.age_context.get('age_group')} / 未成年：{s.age_context.get('is_minor')}", "new_character", C["lavender"]),
            self.text_line("考核倒计时", f"{s.time.get('next_evaluation_days')} 天", "stage", C["apricot"]),
        ]

        schedule_profile = getattr(s, "schedule_profile", {}) or {}
        current_profile = schedule_profile.get("current_profile", {}) or {}
        schedule_children = [
            self.text_line("当前节奏", schedule_profile.get("stage_mode", "trainee"), "schedule", C["lotus"]),
            self.metric_bar("训练空缺", schedule_profile.get("practice_quota_need", 0), "training", C["rouge"], danger_high=True),
            self.metric_bar("行程负荷", schedule_profile.get("workload_pressure", 0), "schedule", C["apricot"], danger_high=True),
            self.chip_wrap([f"{k} {v}%" for k, v in list(current_profile.items())], C["jade"], "暂无日程结构"),
        ]

        body_children = [
            self.metric_bar("体力", body.get("体力"), "health", C["jade"]),
            self.metric_bar("睡眠质量", body.get("睡眠质量"), "schedule", C["celadon"]),
            self.metric_bar("免疫状态", body.get("免疫状态"), "health", C["jade"]),
            self.metric_bar("肌肉疲劳", body.get("肌肉疲劳"), "training", C["apricot"], danger_high=True),
            self.metric_bar("伤病风险", body.get("伤病风险"), "safety", C["rouge"], danger_high=True),
            self.metric_bar("旧伤负担", body.get("旧伤负担"), "health", C["rouge"], danger_high=True),
            self.metric_bar("嗓音状态", body.get("嗓音状态"), "vocal", C["jade"]),
            self.metric_bar("饮食稳定度", body.get("饮食稳定度"), "family", C["celadon"]),
            self.metric_bar("体重管理压力", body.get("体重管理压力"), "staff_boundary", C["rouge"], danger_high=True),
        ]

        mind_children = [
            self.metric_bar("心情", mind.get("心情"), "diary", C["lotus"]),
            self.metric_bar("精神压力", mind.get("精神压力"), "crisis_pr", C["rouge"], danger_high=True),
            self.metric_bar("孤独感", mind.get("孤独感"), "family", C["apricot"], danger_high=True),
            self.metric_bar("职业倦怠", mind.get("职业倦怠"), "schedule", C["rouge"], danger_high=True),
            self.metric_bar("自我认同", mind.get("自我认同"), "app_logo", C["lavender"]),
            self.metric_bar("边界感", mind.get("边界感"), "staff_boundary", C["jade"]),
        ]

        career_children = [
            self.metric_bar("舞蹈实力", career.get("舞蹈实力"), "dance", C["jade"]),
            self.metric_bar("声乐实力", career.get("声乐实力"), "vocal", C["lotus"]),
            self.metric_bar("RAP能力", career.get("RAP能力"), "rap", C["apricot"]),
            self.metric_bar("舞台感染力", career.get("舞台感染力"), "stage", C["lavender"]),
            self.metric_bar("综艺感", career.get("综艺感"), "fans", C["celadon"]),
            self.metric_bar("语言能力", career.get("语言能力"), "market", C["jade"]),
            self.metric_bar("形象指数", career.get("形象指数"), "camera", C["lotus"]),
            self.metric_bar("演技潜力", career.get("演技潜力"), "stage", C["apricot"]),
            self.metric_bar("创作能力", career.get("创作能力"), "music", C["lavender"]),
            self.metric_bar("制作人能力", career.get("制作人能力"), "comeback", C["jade"]),
            ft.Divider(color=ft.Colors.with_opacity(0.28, C["line"])),
            ft.Text("练习积累", size=12, weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN),
            self.text_line("舞蹈", f"{s.progression.get('skill_xp', {}).get('dance', 0)} xp", "dance", C["jade"]),
            self.text_line("声乐", f"{s.progression.get('skill_xp', {}).get('vocal', 0)} xp", "vocal", C["lotus"]),
            self.text_line("舞台", f"{s.progression.get('skill_xp', {}).get('stage', 0)} xp", "stage", C["lavender"]),
            self.text_line("创作", f"{s.progression.get('skill_xp', {}).get('creative', 0)} xp", "music", C["apricot"]),
            
        ]

        talent_children = []
        for key in ["舞蹈天赋", "声乐天赋", "RAP天赋", "镜头天赋", "综艺天赋", "语言天赋", "演技天赋", "创作天赋", "抗压天赋"]:
            talent_children.append(self.metric_bar(key, talents.get(key), "app_logo", C["lotus"]))
        talent_children.append(self.text_line("已解锁能力", f"{len(abilities)} 个", "app_logo", C["jade"]))
        talent_children.append(self.chip_wrap(abilities, C["lavender"], "尚未解锁能力"))

        if not s.period.get("enabled", False) or s.period.get("mode") == "关闭":
            period_children = [
                self.text_line("系统状态", "已关闭", "period", C["lotus"]),
                ft.Text("该存档不会推进生理周期，也不会触发生理期事件。", size=11, color=C["sub"], font_family=FONT_CN),
                
            ]
            period_summary = "已关闭"
        else:
            period_children = [
                self.text_line("周期阶段", f"{s.period.get('phase')} · Day {s.period.get('cycle_day')}", "period", C["lotus"]),
                self.metric_bar("痛感", s.period.get("pain_level"), "period", C["rouge"], danger_high=True),
                self.metric_bar("经期压力", s.period.get("flow_pressure"), "period", C["apricot"], danger_high=True),
                self.metric_bar("周期不规律风险", s.period.get("irregularity_risk"), "health", C["rouge"], danger_high=True),
                self.text_line("应急用品", "有" if s.period.get("has_supplies") else "缺少", "safety", C["jade"]),
                self.text_line("已告知经纪人", "是" if s.period.get("told_manager") else "否", "staff_boundary", C["lotus"]),
                self.text_line("已告知队友", "是" if s.period.get("told_teammate") else "否", "friendship", C["jade"]),
                
            ]
            period_summary = f"{s.period.get('phase')} / Day {s.period.get('cycle_day')} / 痛感 {s.period.get('pain_level')}"

        social_children = [
            self.text_line("国籍", s.social_context.get("nationality"), "market", C["jade"]),
            self.metric_bar("语言压力", s.social_context.get("language_barrier"), "market", C["apricot"], danger_high=True),
            self.metric_bar("文化适应", s.social_context.get("cultural_adaptation"), "hierarchy", C["jade"]),
            self.metric_bar("签证压力", s.social_context.get("visa_pressure"), "contract", C["rouge"], danger_high=True),
            self.metric_bar("学校出勤压力", s.school.get("attendance_pressure"), "school", C["rouge"], danger_high=True),
            self.metric_bar("考试压力", s.school.get("exam_pressure"), "school", C["apricot"], danger_high=True),
            self.metric_bar("作业压力", s.school.get("homework_pressure"), "school", C["apricot"], danger_high=True),
            self.metric_bar("家庭支持", s.family.get("emotional_support"), "family", C["jade"]),
            self.metric_bar("家庭冲突", s.family.get("conflict_level"), "family", C["rouge"], danger_high=True),
            self.metric_bar("控制欲", s.family.get("control_level"), "family", C["apricot"], danger_high=True),
            self.metric_bar("敬语适应", s.hierarchy.get("honorific_adaptation"), "hierarchy", C["jade"]),
            self.metric_bar("礼仪压力", s.hierarchy.get("etiquette_pressure"), "hierarchy", C["rouge"], danger_high=True),
        ]

        self.left_panel.controls.extend([
            self.foldout_section("overview", "new_character", "角色总览", f"{s.character.get('艺名') or s.save_name} · {s.current_mainline}", overview_children, True),
            self.foldout_section("schedule_profile", "schedule", "阶段日程", f"{schedule_profile.get('stage_mode', 'trainee')} / 训练缺口 {schedule_profile.get('practice_quota_need', 0)}", schedule_children, False),
            self.foldout_section("body", "health", "身体状态", f"体力 {body.get('体力')} / 伤病 {body.get('伤病风险')} / 嗓音 {body.get('嗓音状态')}", body_children, True),
            self.foldout_section("mind", "diary", "心理状态", f"心情 {mind.get('心情')} / 压力 {mind.get('精神压力')} / 孤独 {mind.get('孤独感')}", mind_children, True),
            self.foldout_section("career", "stage", "职业属性", f"舞 {career.get('舞蹈实力')} / 声 {career.get('声乐实力')} / 创作 {career.get('创作能力')}", career_children, False),
            self.foldout_section("talents", "app_logo", "天赋与能力", f"能力 {len(abilities)} 个 / 抗压天赋 {talents.get('抗压天赋')}", talent_children, False),
            self.foldout_section("period", "period", "生理周期", period_summary, period_children, False),
            self.foldout_section("social_env", "school", "社会环境", f"语言压力 {s.social_context.get('language_barrier')} / 家庭冲突 {s.family.get('conflict_level')}", social_children, False),
        ])

        company_children = [
            self.metric_bar("公司满意度", company.get("公司满意度"), "contract", C["jade"]),
            self.metric_bar("公司信任度", company.get("公司信任度"), "staff_boundary", C["celadon"]),
            self.metric_bar("主推指数", company.get("主推指数"), "stage", C["lavender"]),
            self.metric_bar("资源倾斜度", company.get("资源倾斜度"), "market", C["jade"]),
            self.metric_bar("危机关注度", company.get("危机关注度"), "crisis_pr", C["rouge"], danger_high=True),
            self.metric_bar("合约稳定度", company.get("合约稳定度"), "contract", C["celadon"]),
            self.metric_bar("个人议价权", company.get("个人议价权"), "contract", C["apricot"]),
            self.metric_bar("续约倾向", company.get("续约倾向"), "contract", C["jade"]),
        ]
        team_children = [
            self.metric_bar("团队默契", self.vget(team, "团队默契度", "团队默契"), "friendship", C["jade"]),
            self.metric_bar("队内信任度", team.get("队内信任度"), "friendship", C["celadon"]),
            self.metric_bar("队内竞争度", team.get("队内竞争度"), "stage", C["apricot"], danger_high=True),
            self.metric_bar("队内资源平衡", team.get("队内资源平衡"), "market", C["jade"]),
            self.metric_bar("镜头/part矛盾", self.vget(team, "镜头/part矛盾", "镜头前和谐度"), "camera", C["rouge"], danger_high=True),
            self.metric_bar("真实关系温度", team.get("真实关系温度"), "friendship", C["lotus"]),
            self.metric_bar("宿舍安全感", team.get("宿舍安全感"), "safety", C["jade"]),
            self.metric_bar("营业疲劳", team.get("营业疲劳"), "camera", C["rouge"], danger_high=True),
        ]
        fans_children = [
            self.metric_bar("个人粉丝", self.vget(fans, "个人粉丝", "个人粉丝数"), "fans", C["jade"]),
            self.metric_bar("团体粉丝", self.vget(fans, "团体粉丝", "团体粉丝数"), "fans", C["celadon"]),
            self.metric_bar("团粉稳定度", fans.get("团粉稳定度"), "fans", C["jade"]),
            self.metric_bar("唯粉攻击性", fans.get("唯粉攻击性"), "crisis_pr", C["rouge"], danger_high=True),
            self.metric_bar("CP粉规模", fans.get("CP粉规模"), "romance", C["lotus"], danger_high=True),
            self.metric_bar("路人好感", fans.get("路人好感"), "market", C["celadon"]),
            self.metric_bar("黑粉活跃度", fans.get("黑粉活跃度"), "crisis_pr", C["rouge"], danger_high=True),
            self.metric_bar("站姐稳定度", fans.get("站姐稳定度"), "camera", C["jade"]),
            self.metric_bar("粉丝信任基础", fans.get("粉丝信任基础"), "fans", C["jade"]),
            self.metric_bar("粉圈撕裂度", fans.get("粉圈撕裂度"), "crisis_pr", C["rouge"], danger_high=True),
        ]
        risk_children = [
            self.metric_bar("恋爱风险", risks.get("恋爱风险"), "romance", C["rouge"], danger_high=True),
            self.metric_bar("私生风险", risks.get("私生风险"), "safety", C["rouge"], danger_high=True),
            self.metric_bar("行程泄露风险", risks.get("行程泄露风险"), "camera", C["rouge"], danger_high=True),
            self.metric_bar("性骚扰风险", risks.get("性骚扰风险"), "staff_boundary", C["rouge"], danger_high=True),
            self.metric_bar("霸凌排挤风险", risks.get("霸凌排挤风险"), "friendship", C["rouge"], danger_high=True),
            self.metric_bar("队内不和曝光风险", risks.get("队内不和曝光风险"), "crisis_pr", C["rouge"], danger_high=True),
            self.metric_bar("伤病爆发风险", risks.get("伤病爆发风险"), "health", C["rouge"], danger_high=True),
            self.metric_bar("公关危机风险", risks.get("公关危机风险"), "crisis_pr", C["rouge"], danger_high=True),
        ]
        relationship_children = [
            ft.Text(relationship_ui_summary(name, rel, s), size=11, color=C["sub"], font_family=FONT_CN)
            for name, rel in list(s.relationships.items())[:12]
        ] or [ft.Text("暂无关系记录", size=12, color=C["sub"], font_family=FONT_CN)]
        crisis_children = []
        debut = getattr(s, "debut", {}) or {}
        ending = getattr(s, "ending", {}) or {}
        crisis_children.append(ft.Text("出道 / 结局窗口", size=12, weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN))
        crisis_children.append(self.text_line("出道可能性", f"{debut.get('readiness', 0)} / 概率 {debut.get('probability', 0)}%", "stage", C["lavender"]))
        crisis_children.append(self.text_line("出道动向", self.player_debut_status(debut), "stage", C["apricot"]))
        top_ending = (ending.get("candidate_endings") or [{}])[0] if isinstance(ending.get("candidate_endings"), list) and ending.get("candidate_endings") else {}
        crisis_children.append(self.text_line("未来方向", self.player_ending_status(ending, top_ending), "contract", C["jade"]))
        crisis_children.append(ft.Divider(color=ft.Colors.with_opacity(0.35, C["line"])))

        if route:
            crisis_children.append(self.text_line("服务商", self.config.provider_label(), "api", C["jade"]))
            crisis_children.append(self.text_line("叙事模式", self.config.model_policy, "api", C["jade"]))
            crisis_children.append(self.text_line("当前线路", route.actual_model, "api", C["lotus"]))
            crisis_children.append(self.text_line("最近状态", route.turn_kind, "schedule", C["apricot"]))
        active_crises = [c for c in (getattr(s, "active_crises", []) or []) if getattr(c, "stage", "") not in {"closed", "converted"}]
        if active_crises:
            for c in active_crises:
                crisis_children.append(ft.Text(f"• {c.title} / {c.stage}", size=12, color=C["rouge"], font_family=FONT_CN))
        else:
            crisis_children.append(ft.Text("当前没有打开的重大危机窗口。", size=12, color=C["sub"], font_family=FONT_CN))
        crisis_children.append(ft.Divider(color=ft.Colors.with_opacity(0.35, C["line"])))
        crisis_children.append(ft.Text("长期记录", size=12, weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN))
        crisis_children.append(self.chip_wrap([str(x) for x in list(getattr(s, "flags", []) or [])[-16:]], C["lotus"], "暂无长期 Flag"))
        crisis_children.append(ft.Text("已解决记录", size=12, weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN))
        crisis_children.append(self.chip_wrap([str(x) for x in list(getattr(s, "resolved_flags", []) or [])[-10:]], C["jade"], "暂无已解决 Flag"))
        crisis_children.append(ft.Text("重大事件", size=12, weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN))
        crisis_children.append(self.chip_wrap([str(x) for x in list(getattr(s, "major_events", []) or [])[-10:]], C["apricot"], "暂无重大事件记录"))

        self.right_panel.controls.extend([
            self.foldout_section("company", "contract", "公司与合约", f"满意 {company.get('公司满意度')} / 信任 {company.get('公司信任度')} / 资源 {company.get('资源倾斜度')}", company_children, True),
            self.foldout_section("team", "friendship", "团队关系", f"默契 {team.get('团队默契')} / 信任 {team.get('队内信任度')} / 疲劳 {team.get('营业疲劳')}", team_children, True),
            self.foldout_section("fans", "fans", "粉丝与舆论", f"黑粉 {fans.get('黑粉活跃度')} / 路人 {fans.get('路人好感')} / 撕裂 {fans.get('粉圈撕裂度')}", fans_children, False),
            self.foldout_section("risks", "safety", "风险系统", f"恋爱 {risks.get('恋爱风险')} / 私生 {risks.get('私生风险')} / 公关 {risks.get('公关危机风险')}", risk_children, True),
            self.foldout_section("relationships", "romance", "关系状态", f"记录 {len(s.relationships)} 人 / 工作人员不进入 CP", relationship_children, False),
            self.foldout_section("crisis_flags", "crisis_pr", "危机与长期记录", f"活跃危机 {len(active_crises)} / Flag {len(getattr(s, 'flags', []) or [])}", crisis_children, True),
        ])

    def choice_card(self, choice: Choice):
        card = ft.ElevatedButton(
            content=ft.Row([
                ft.Container(ft.Text(choice.id, size=13, weight=ft.FontWeight.W_700, color=C["lavender"], font_family=FONT_EN), width=28, height=28, border_radius=14, bgcolor=ft.Colors.with_opacity(0.16, C["lotus"]), alignment=ft.Alignment.CENTER),
                ft.Text(choice.text, size=13, color=C["ink"], font_family=FONT_CN, expand=True),
            ], spacing=8),
            on_click=lambda e, c=choice: self.submit_action(f"{c.id}. {c.text}"),
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.with_opacity(0.82, ft.Colors.WHITE),
                color=C["ink"],
                padding=ft.Padding(left=12, right=12, top=10, bottom=10),
                shape=ft.RoundedRectangleBorder(radius=18),
                elevation=0,
            ),
        )
        self.choice_buttons.append(card)
        return card

    def refresh_choices(self) -> None:
        assert self.state is not None
        self.choice_row.controls.clear()
        self.choice_buttons = []
        cards = []
        for choice in self.state.current_choices:
            if choice.id.upper() == "E":
                continue
            cards.append(self.choice_card(choice))
        self.submit_button = ft.ElevatedButton(
            "提交行动",
            icon=icon("SEND"),
            on_click=self.submit_custom_action,
            style=ft.ButtonStyle(bgcolor=C["lavender"], color=ft.Colors.WHITE, shape=ft.RoundedRectangleBorder(radius=18), padding=ft.Padding(left=18, right=18, top=14, bottom=14)),
        )
        self.choice_row.controls.extend([
            ft.Row([self.section_title("schedule", "下一步选择", "选择卡片或写下自定义行动")], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row(cards, wrap=True, spacing=8, run_spacing=8),
            ft.Row([self.custom_input, self.submit_button], spacing=10, vertical_alignment=ft.CrossAxisAlignment.END),
        ])

    def submit_custom_action(self, e) -> None:
        if self.is_generating:
            self.snack("本回合正在生成中，请等待完成。")
            return
        text = (self.custom_input.value or "").strip()
        if not text:
            self.snack("请输入自定义行动。")
            return
        self.submit_action(f"E. {text}")

    def submit_action(self, action: str) -> None:
        if self.is_generating:
            self.snack("本回合正在生成中，请等待完成。")
            return
        if self.state is None or self.save_id is None:
            self.snack("没有可用存档。")
            return

        self.set_generating(True)
        current_state = self.state
        current_save_id = self.save_id

        def worker() -> None:
            try:
                engine = TurnEngine(self.storage, self.config)
                state, response, applied, route_info, system_events, validation = engine.run_turn(current_save_id, current_state, action)
                self.state = state
                summary = self.build_turn_summary(applied=applied, system_events=system_events, validation=validation, route_info=route_info, action=action)
                narrative_text = self.display_narrative_from_response(response)
                logger.info(f"UI narrative visible chars={len(str(narrative_text or ''))}, preview={str(narrative_text or '').replace(chr(10), ' ')[:220]}")
                if not self.normalize_visible_text(narrative_text):
                    narrative_text = "这一回合已经记录下来。练习室的灯还亮着，你可以先查看本回合总结，再决定下一步。"
                self.set_story_pair(narrative_text, summary)
                self.refresh_panels()
                self.refresh_choices()
                self.custom_input.value = ""
            except ActionBlockedError as exc:
                suggestions = ft.Column([ft.Text(exc.message, size=14, color=C["rouge"], font_family=FONT_CN, selectable=True)], spacing=8)
                if exc.suggestions:
                    suggestions.controls.append(ft.Text("可以改成：" + "；".join(exc.suggestions[:4]), size=13, color=C["sub"], font_family=FONT_CN))
                self.story_view.controls.append(self.story_block("行动未执行", "不消耗回合，也不会写入存档", "safety", suggestions, C["rouge"]))
            except LLMError as exc:
                self.story_view.controls.append(self.story_block("生成失败", "本回合未写入存档，请检查 API 设置后重试", "api", ft.Text(str(exc), size=13, color=C["rouge"], font_family=FONT_CN, selectable=True), C["rouge"]))
            except Exception as exc:
                logger.exception("submit_action failed")
                self.story_view.controls.append(self.story_block("程序错误", "本回合未完成", "crisis_pr", ft.Text(str(exc), size=13, color=C["rouge"], font_family=FONT_CN, selectable=True), C["rouge"]))
            finally:
                self.set_generating(False)
                self.page.update()

        self.run_in_background(worker)

    def snack(self, message: str) -> None:
        self.page.snack_bar = ft.SnackBar(ft.Text(message))
        self.page.snack_bar.open = True
        self.page.update()


def main(page: ft.Page) -> None:
    KpopApp(page).run()


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
