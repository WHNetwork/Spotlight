from __future__ import annotations

from ui.shared import *


class HomeMixin:
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


    def load_latest(self) -> None:
        """Load the latest save and enter the game page.

        Home page's Continue button calls this method. It is deliberately
        separate from load_latest_for_static_page(), which only prepares
        state for diary/contract/schedule pages without navigation.
        """
        save_id = self.storage.latest_save_id()
        if save_id is None:
            self.show_home()
            return
        try:
            self.save_id = save_id
            self.state = self.storage.load_save(save_id)
            self.show_game()
        except Exception as exc:
            logger.exception("load_latest failed")
            self.clear()
            self.page.add(
                ft.Container(
                    expand=True,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Container(
                        padding=24,
                        border_radius=24,
                        bgcolor=ft.Colors.with_opacity(0.86, ft.Colors.WHITE),
                        border=ft.Border.all(1, ft.Colors.with_opacity(0.55, C["line"])),
                        content=ft.Column([
                            ft.Text("读取存档失败", size=self.ui_size(20), weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN),
                            ft.Text(str(exc), size=self.ui_size(12), color=ft.Colors.RED, font_family=FONT_CN),
                            ft.TextButton("返回首页", on_click=lambda e: self.show_home()),
                        ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    ),
                )
            )
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

    def parse_age_value(self, value: Any) -> Optional[int]:
        text = str(value or "").strip()
        if not text:
            return None
        m = re.search(r"\d{1,2}", text)
        if not m:
            return None
        try:
            age = int(m.group(0))
        except Exception:
            return None
        return age if 1 <= age <= 80 else None

    def sync_runtime_context(self, state: GameState | None = None) -> None:
        s = state or self.state
        if s is None:
            return

        ch = s.character if isinstance(s.character, dict) else {}
        char_age = self.parse_age_value(ch.get("年龄"))
        time_age = None
        if isinstance(s.time, dict):
            time_age = self.parse_age_value(s.time.get("age_years"))

        age = time_age if time_age is not None else char_age
        if age is not None:
            try:
                if age < 12:
                    group = "儿童"
                elif age < 16:
                    group = "青少年早期"
                elif age < 18:
                    group = "青少年"
                elif age < 21:
                    group = "青年"
                elif age < 26:
                    group = "成年"
                else:
                    group = "成熟"
                is_minor = age < 18
                s.age_context = {
                    "age": age,
                    "age_group": group,
                    "is_minor": is_minor,
                    "guardian_required": is_minor,
                    "romance_allowed": age >= 18,
                }
            except Exception:
                pass
            try:
                if isinstance(s.time, dict):
                    s.time["age_years"] = age
                    if s.time.get("age_months") is None:
                        s.time["age_months"] = age * 12
            except Exception:
                pass

    def completed_turn_count(self, state: GameState | None = None) -> int:
        s = state or self.state
        if s is None:
            return 0
        try:
            return max(0, int(getattr(s, "turn", 0) or 0))
        except Exception:
            return 0

    def current_turn_number(self, state: GameState | None = None) -> int:
        return self.completed_turn_count(state) + 1

    def turn_status_text(self, state: GameState | None = None) -> str:
        done = self.completed_turn_count(state)
        return f"第 {done + 1} 回合 / 已完成 {done} 回合"

    def age_status_text(self, state: GameState | None = None) -> str:
        s = state or self.state
        if s is None:
            return "年龄未知"
        self.sync_runtime_context(s)
        age = s.age_context.get("age")
        group = s.age_context.get("age_group") or "未知"
        adult = "未成年" if s.age_context.get("is_minor") else "成年"
        if age is None:
            return f"{group} / {adult}"
        return f"{age}岁 / {group} / {adult}"

    def active_character_label(self) -> str:
        if self.state is None:
            return "未读取角色"
        self.sync_runtime_context(self.state)
        ch = self.state.character if isinstance(self.state.character, dict) else {}
        name = ch.get("艺名") or ch.get("本名") or self.state.save_name or "当前角色"
        stage = self.state.current_stage or "当前阶段"
        return f"{name} · {stage} · {self.turn_status_text(self.state)}"


    def display_group_name(self, state: GameState | None = None) -> str:
        s = state or self.state
        if s is None:
            return "练习生"
        ch = s.character if isinstance(s.character, dict) else {}
        debut = getattr(s, "debut", {}) or {}

        if s.is_trainee_stage():
            return "练习生"

        candidates = []
        for source in [ch, debut]:
            if isinstance(source, dict):
                for key in ["组合名", "团名", "出道组合", "组合", "group_name", "debut_group", "team_name"]:
                    val = str(source.get(key) or "").strip()
                    if val:
                        candidates.append(val)

        for flag in list(getattr(s, "flags", []) or []):
            text = str(flag)
            for prefix in ["组合名：", "组合：", "出道组合：", "团名："]:
                if text.startswith(prefix):
                    candidates.append(text.replace(prefix, "", 1).strip())

        return candidates[0] if candidates else "出道组合未定"

