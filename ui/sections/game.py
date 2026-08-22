from __future__ import annotations

from ui.shared import *


class GameMixin:
    def show_save_list(self) -> None:
        self.clear()
        self.page.padding = 0
        self.page.bgcolor = ft.Colors.WHITE

        try:
            saves = self.storage.list_saves()
        except Exception:
            logger.exception("list_saves failed")
            saves = []

        vw = int(self.page.width or 1320)
        vh = int(self.page.height or 860)
        scale = max(0.74, min(1.12, min(vw / 1360, vh / 820)))

        def r(value: float) -> int:
            return max(1, int(value * scale))

        def glass_button(label: str, icon_name: str, handler, fill: str | None = None):
            return ft.Container(
                height=r(42),
                padding=ft.Padding(left=r(14), right=r(16), top=0, bottom=0),
                border_radius=r(21),
                bgcolor=ft.Colors.with_opacity(0.84, fill or ft.Colors.WHITE),
                border=ft.Border.all(1, ft.Colors.with_opacity(0.70, ft.Colors.WHITE)),
                shadow=ft.BoxShadow(
                    blur_radius=r(20),
                    spread_radius=0,
                    color=ft.Colors.with_opacity(0.12, "#536B89"),
                    offset=ft.Offset(0, r(8)),
                ),
                ink=True,
                on_click=handler,
                content=ft.Row([
                    icon_image(icon_name, r(18), 0.9),
                    ft.Text(label, size=r(12), color=C["ink"], weight=ft.FontWeight.W_700, font_family=FONT_CN),
                ], spacing=r(7), alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            )

        def chip(text: str, icon_name: str = "stage", color: str = "#9A8FC4"):
            return ft.Container(
                height=r(30),
                padding=ft.Padding(left=r(9), right=r(11), top=0, bottom=0),
                border_radius=r(15),
                bgcolor=ft.Colors.with_opacity(0.52, ft.Colors.WHITE),
                border=ft.Border.all(1, ft.Colors.with_opacity(0.42, ft.Colors.WHITE)),
                content=ft.Row([
                    ft.Container(
                        icon_image(icon_name, r(14), 0.82),
                        width=r(20),
                        height=r(20),
                        border_radius=r(10),
                        bgcolor=ft.Colors.with_opacity(0.22, color),
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Text(str(text), size=r(10), color=C["dai"], font_family=FONT_CN, max_lines=1),
                ], spacing=r(5), vertical_alignment=ft.CrossAxisAlignment.CENTER),
            )

        def save_card(item: Dict[str, Any]):
            sid = int(item["id"])
            state = None
            try:
                state = self.storage.load_save(sid)
                self.sync_runtime_context(state)
            except Exception:
                logger.exception("load save preview failed")

            p = state.player if state is not None else None
            name = (p.stage_name or p.name or item.get("name") or f"存档 {sid}") if p is not None else (item.get("name") or f"存档 {sid}")
            stage = self.stage_label(state)
            mainline = f"练习生第 {state.time.trainee_day} 天" if state is not None else "暂无主线"
            schedule = f"当前日期 {state.time.current_date}" if state is not None else "暂无行程"
            turn = self.completed_turn_count(state) if state is not None else 0
            age_text = self.age_status_text(state) if state is not None else "年龄未知"
            company_size = "未知公司"
            if state is not None:
                company_size = str(state.company.size or "未知公司")
            updated_at = str(item.get("updated_at") or "")
            created_at = str(item.get("created_at") or "")
            time_label = updated_at or created_at or "未知时间"
            nationality = p.nationality if p is not None else ""
            card_w = max(r(330), min(r(410), int((vw - r(96)) / 3))) if vw >= 1120 else max(r(330), min(r(440), vw - r(56)))

            return ft.Container(
                width=card_w,
                padding=ft.Padding(left=r(18), right=r(18), top=r(18), bottom=r(16)),
                border_radius=r(28),
                bgcolor=ft.Colors.with_opacity(0.78, ft.Colors.WHITE),
                border=ft.Border.all(1, ft.Colors.with_opacity(0.72, ft.Colors.WHITE)),
                shadow=ft.BoxShadow(
                    blur_radius=r(30),
                    spread_radius=0,
                    color=ft.Colors.with_opacity(0.16, "#536B89"),
                    offset=ft.Offset(0, r(12)),
                ),
                ink=True,
                on_click=lambda e, save_id=sid: self.load_save_by_id(save_id),
                content=ft.Column([
                    ft.Row([
                        ft.Container(
                            width=r(74),
                            height=r(74),
                            border_radius=r(26),
                            padding=r(3),
                            bgcolor=ft.Colors.with_opacity(0.50, "#F7ECEE"),
                            border=ft.Border.all(1, ft.Colors.with_opacity(0.68, ft.Colors.WHITE)),
                            content=ft.Image(src=self.avatar_src_for_player(p), fit="cover", border_radius=r(23)),
                        ),
                        ft.Column([
                            ft.Text(str(name), size=r(18), weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN, max_lines=1),
                            ft.Text(str(stage), size=r(12), color=C["lavender"], font_family=FONT_CN, max_lines=1),
                            ft.Row([
                                ft.Container(
                                    ft.Image(src=flag_src_from_nationality(nationality), width=r(18), height=r(18), fit="contain"),
                                    width=r(22),
                                    height=r(22),
                                    border_radius=r(11),
                                    bgcolor=ft.Colors.with_opacity(0.45, ft.Colors.WHITE),
                                    alignment=ft.Alignment.CENTER,
                                ),
                                ft.Text(f"ID {sid:03d}", size=r(10), color=ft.Colors.with_opacity(0.72, C["sub"]), font_family=FONT_EN),
                            ], spacing=r(7), vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ], spacing=r(3), expand=True),
                        ft.Container(
                            width=r(42),
                            height=r(42),
                            border_radius=r(21),
                            bgcolor=ft.Colors.with_opacity(0.42, "#F7ECEE"),
                            alignment=ft.Alignment.CENTER,
                            content=icon_image("save_archive", r(24), 0.92),
                        ),
                    ], spacing=r(14), vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Container(height=r(4)),
                    ft.Text(str(mainline), size=r(14), color=C["ink"], weight=ft.FontWeight.W_600, font_family=FONT_CN, max_lines=1),
                    ft.Text(str(schedule), size=r(12), color=C["sub"], font_family=FONT_CN, max_lines=2),
                    ft.Row([
                        chip(f"已完成 {turn} 回合", "schedule", C["jade"]),
                        chip(age_text, "new_character", C["lotus"]),
                    ], spacing=r(8), wrap=True),
                    ft.Row([
                        chip(company_size, "contract", C["apricot"]),
                        chip(f"更新 {time_label}", "diary", C["peach"]),
                    ], spacing=r(8), wrap=True),
                    ft.Container(
                        height=r(44),
                        border_radius=r(22),
                        bgcolor=ft.Colors.with_opacity(0.78, "#F7ECEE"),
                        border=ft.Border.all(1, ft.Colors.with_opacity(0.56, ft.Colors.WHITE)),
                        alignment=ft.Alignment.CENTER,
                        content=ft.Row([
                            ft.Text("读取这段旅程", size=r(12), color=C["ink"], weight=ft.FontWeight.W_700, font_family=FONT_CN),
                            ft.Text("LOAD", size=r(10), color=ft.Colors.with_opacity(0.62, C["dai"]), font_family=FONT_EN, italic=True),
                        ], spacing=r(8), alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ),
                ], spacing=r(12)),
            )

        cards = [save_card(item) for item in saves]

        header = ft.Container(
            padding=ft.Padding(left=r(34), right=r(34), top=r(26), bottom=r(12)),
            content=ft.Row([
                ft.Container(
                    width=r(66),
                    height=r(66),
                    border_radius=r(22),
                    padding=r(5),
                    bgcolor=ft.Colors.with_opacity(0.56, ft.Colors.WHITE),
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.78, ft.Colors.WHITE)),
                    shadow=ft.BoxShadow(blur_radius=r(22), color=ft.Colors.with_opacity(0.14, "#536B89"), offset=ft.Offset(0, r(8))),
                    content=ft.Image(src=asset("app_icon.png"), fit="cover", border_radius=r(18)),
                ),
                ft.Column([
                    ft.Text("存档剧场", size=r(30), weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN),
                    ft.Text("选择一段已经写下的练习室旅程", size=r(13), color=C["sub"], font_family=FONT_CN),
                ], spacing=2, expand=True),
                glass_button("返回首页", "app_logo", lambda e: self.show_home()),
                glass_button("新的人生", "new_character", lambda e: self.show_character_create(), "#F7ECEE"),
            ], spacing=r(14), vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )

        if cards:
            body = ft.Column([
                ft.Container(
                    padding=ft.Padding(left=r(34), right=r(34), top=r(12), bottom=r(10)),
                    content=ft.Row([
                        ft.Text(f"{len(cards)} 个存档", size=r(12), color=C["dai"], weight=ft.FontWeight.W_700, font_family=FONT_CN),
                        ft.Container(expand=True),
                        ft.Text("点击卡片即可读取", size=r(11), color=ft.Colors.with_opacity(0.72, C["sub"]), font_family=FONT_CN),
                    ]),
                ),
                ft.Container(
                    expand=True,
                    padding=ft.Padding(left=r(34), right=r(34), top=r(4), bottom=r(34)),
                    content=ft.Column([
                        ft.Row(cards, wrap=True, spacing=r(18), run_spacing=r(18)),
                    ], scroll=ft.ScrollMode.AUTO, expand=True),
                ),
            ], expand=True, spacing=0)
        else:
            body = ft.Container(
                expand=True,
                alignment=ft.Alignment.CENTER,
                padding=r(28),
                content=ft.Container(
                    width=min(r(560), vw - r(44)),
                    padding=ft.Padding(left=r(30), right=r(30), top=r(28), bottom=r(28)),
                    border_radius=r(32),
                    bgcolor=ft.Colors.with_opacity(0.78, ft.Colors.WHITE),
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.75, ft.Colors.WHITE)),
                    shadow=ft.BoxShadow(blur_radius=r(32), color=ft.Colors.with_opacity(0.15, "#536B89"), offset=ft.Offset(0, r(12))),
                    content=ft.Column([
                        ft.Container(
                            width=r(92),
                            height=r(92),
                            border_radius=r(32),
                            padding=r(6),
                            bgcolor=ft.Colors.with_opacity(0.48, "#F7ECEE"),
                            content=ft.Image(src=asset("app_icon.png"), fit="cover", border_radius=r(26)),
                        ),
                        ft.Text("还没有存档", size=r(22), weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN, text_align=ft.TextAlign.CENTER),
                        ft.Text("创建角色后，第一段练习室记录会出现在这里。", size=r(13), color=C["sub"], font_family=FONT_CN, text_align=ft.TextAlign.CENTER),
                        ft.Row([
                            glass_button("创建角色", "new_character", lambda e: self.show_character_create(), "#F7ECEE"),
                            glass_button("返回首页", "app_logo", lambda e: self.show_home()),
                        ], spacing=r(10), alignment=ft.MainAxisAlignment.CENTER, wrap=True),
                    ], spacing=r(14), horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                ),
            )

        page = ft.Stack([
            ft.Container(
                left=0,
                top=0,
                right=0,
                bottom=0,
                bgcolor="#F8F6FC",
                image=ft.DecorationImage(src=asset("backgrounds/storage_bg.png"), fit="cover", opacity=1.0),
            ),
            ft.Container(left=0, top=0, right=0, bottom=0, bgcolor=ft.Colors.with_opacity(0.18, ft.Colors.WHITE)),
            ft.Container(
                left=0,
                top=0,
                right=0,
                bottom=0,
                content=ft.Column([header, body], expand=True, spacing=0),
            ),
        ], expand=True)

        def _resize(e):
            self.show_save_list()

        self.page.on_resize = _resize
        self.page.add(page)
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

    def relationship_metric_bar(self, label: str, value, color: str = "#93C9B7", danger_high: bool = False):
        try:
            v = int(value)
        except Exception:
            v = 0
        v = max(0, min(100, v))
        active_color = C["rouge"] if danger_high and v >= 70 else color
        bar_w = max(180, min(260, int((self.page.width or 1320) * 0.15)))
        fill_w = max(4, int(bar_w * v / 100))
        return ft.Column([
            ft.Row([
                ft.Text(label, size=11, color=C["ink"], weight=ft.FontWeight.W_600, font_family=FONT_CN),
                ft.Container(expand=True),
                ft.Text(str(v), size=11, color=C["sub"], font_family=FONT_EN),
            ], spacing=6),
            ft.Stack([
                ft.Container(width=bar_w, height=7, border_radius=8, bgcolor=ft.Colors.with_opacity(0.45, "#E8EAF4")),
                ft.Container(width=fill_w, height=7, border_radius=8, bgcolor=ft.Colors.with_opacity(0.88, active_color)),
            ], width=bar_w, height=7),
        ], spacing=4)

    def relationship_card(self, name: str, rel) -> ft.Container:
        metrics = [
            self.relationship_metric_bar("熟悉度", rel.familiarity, C["jade"]),
            self.relationship_metric_bar("信任", rel.trust, C["celadon"]),
            self.relationship_metric_bar("亲近", rel.closeness, C["lavender"]),
            self.relationship_metric_bar("张力", rel.tension, C["apricot"], danger_high=True),
        ]
        return ft.Container(
            padding=ft.Padding(left=10, right=10, top=10, bottom=10),
            border_radius=16,
            bgcolor=ft.Colors.with_opacity(0.52, ft.Colors.WHITE),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.44, C["line"])),
            content=ft.Column([
                ft.Row([
                    ft.Container(icon_image("romance", 17, 0.88), width=25, height=25, border_radius=13, bgcolor=ft.Colors.with_opacity(0.22, C["lotus"]), alignment=ft.Alignment.CENTER),
                    ft.Column([
                        ft.Text(str(name), size=13, color=C["ink"], weight=ft.FontWeight.W_700, font_family=FONT_CN, max_lines=1),
                        ft.Text(f"ID {rel.npc_id}", size=10, color=C["sub"], font_family=FONT_CN, max_lines=1),
                    ], spacing=0, expand=True),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                *metrics,
            ], spacing=8),
        )

    def mini_chip(self, text: str, color: str = "#9A8FC4"):
        return ft.Container(
            padding=ft.Padding(left=10, right=10, top=5, bottom=5),
            border_radius=14,
            bgcolor=ft.Colors.with_opacity(0.12, color),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.18, color)),
            content=ft.Text(text, size=11, color=C["ink"], font_family=FONT_CN),
        )


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

    def avatar_src_for_player(self, p=None) -> str:
        if p is None:
            p = self.state.player if self.state is not None else None
        if p is None:
            return asset("avatars/avatar_001.png")
        avatar = str(getattr(p, "avatar", "") or "").strip()
        if avatar and asset_exists(avatar):
            return asset(avatar)
        fallback = avatar_src_from_character({"艺名": p.stage_name, "本名": p.name})
        try:
            p.avatar = fallback
        except Exception:
            pass
        return fallback

    def weekday_label(self, t) -> str:
        """真实星期（TimeState.weekday: 周一=0 … 周日=6）映射为中文标签。"""
        try:
            names = ["一", "二", "三", "四", "五", "六", "日"]
            return f"周{names[t.weekday]}"
        except Exception:
            return ""

    def get_character_avatar_src(self) -> str:
        return self.avatar_src_for_player(self.state.player if self.state is not None else None)

    def character_identity_card(self) -> ft.Container:
        s = self.state
        if s is None:
            return ft.Container()
        p = s.player
        art_name = str(p.stage_name or p.name or s.save_name or "练习生")
        real_name = str(p.name or "").strip()
        self.sync_runtime_context(s)
        age_value = self.player_age(s)
        age = f"{age_value}岁" if age_value is not None else "未知"
        nationality = str(p.nationality or "未填写")
        identity = str(p.identity_source or "练习生")
        mbti = str(p.mbti or "未设定")
        group_name = self.display_group_name(s)
        t = s.time
        mainline = f"练习生第 {t.trainee_day} 天 · {self.weekday_label(t)}"
        month_note = "月末" if t.is_month_end else f"距月末 {t.days_until_month_end} 天"

        card_width = max(520, min(640, int((self.page.width or 1320) * 0.46)))
        return ft.Container(
            width=card_width,
            padding=ft.Padding(left=16, right=16, top=10, bottom=10),
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
                        self.mini_chip(group_name, C["apricot"]),
                        self.mini_chip(mbti, C["lavender"]),
                    ], spacing=6, run_spacing=4, wrap=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Text(
                        f"{real_name + ' · ' if real_name and real_name != art_name else ''}{identity} · {group_name} · {mbti}",
                        size=11,
                        color=C["sub"],
                        font_family=FONT_CN,
                        max_lines=2,
                    ),
                    ft.Text(
                        f"{s.time.current_date} · {self.turn_status_text(s)} · {month_note} · {mainline}",
                        size=11,
                        color=C["dai"],
                        font_family=FONT_CN,
                        max_lines=2,
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

        def add(title: str, detail: str, level: str = "warning", icon_name: str = "health"):
            title = (title or "").strip()
            if not title or title in seen:
                return
            seen.add(title)
            alerts.append({"title": title, "detail": detail or "需要优先处理。", "level": level, "icon": icon_name})

        for cond in list(getattr(s.condition, "active_conditions", []) or []):
            add(
                str(getattr(cond, "type", "身体问题")),
                f"严重度 {getattr(cond, 'severity', 0)}，开始于 {getattr(cond, 'started_on', '')}。",
                "crisis" if getattr(cond, "severity", 0) >= 60 else "warning",
                "health",
            )

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
        self.sync_runtime_context(self.state)
        self.clear()
        self.page.padding = 0
        self.page.bgcolor = "#FBFCFF"
        viewport_w = int(self.page.width or 1320)
        panel_width = max(360, min(420, int(viewport_w * 0.29)))
        inner_panel_width = max(320, panel_width - 28)
        self.is_generating = False
        self.choice_buttons = []
        self.story_view = ft.Column(expand=True, spacing=16)
        self.left_panel = ft.Column(width=inner_panel_width, scroll=ft.ScrollMode.AUTO, spacing=12)
        self.right_panel = ft.Column(width=inner_panel_width, scroll=ft.ScrollMode.AUTO, spacing=12)
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
        first_text = "角色创建完成。练习室的灯已经亮起，你可以从下方选择第一步。" if initial or self.state.meta.turn_index == 0 else self.fallback_story_text(getattr(self.state, "last_public_summary", "存档已载入。"))
        if initial or self.state.meta.turn_index == 0:
            self.set_story_pair(first_text)
        else:
            if not self.render_recent_turns(limit=1):
                self.set_story_pair(first_text)
        self.refresh_panels()
        self.refresh_choices()

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

        top_bar = ft.Container(
            padding=ft.Padding(left=18, right=18, top=10, bottom=10),
            content=ft.Row([
                ft.Row([
                    ft.Container(icon_image("app_logo", 34), width=42, height=42, border_radius=16, bgcolor=ft.Colors.with_opacity(0.36, "#F7ECEE"), alignment=ft.Alignment.CENTER),
                    ft.Column([
                        ft.Text("星光练习室", size=22, weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN),
                        ft.Text("Starlight Practice Room", size=11, italic=True, color=C["lavender"], font_family=FONT_EN),
                    ], spacing=0),
                    self.mini_chip("练习生", C["lotus"]),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Container(expand=True),
                self.character_identity_card(),
                ft.Container(expand=True),
                ft.Row([
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
            self.soft_card(self.left_panel, padding=14, radius=26, bgcolor=ft.Colors.with_opacity(0.72, ft.Colors.WHITE), width=panel_width),
            ft.Container(content=self.story_view, expand=True, padding=ft.Padding(left=10, right=10, top=4, bottom=4)),
            self.soft_card(self.right_panel, padding=14, radius=26, bgcolor=ft.Colors.with_opacity(0.72, ft.Colors.WHITE), width=panel_width),
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
        self.sync_runtime_context(self.state)
        s = self.state
        self.left_panel.controls.clear()
        self.right_panel.controls.clear()
        self.refresh_pinned_alerts()

        t = s.time
        p = s.player
        c = s.condition
        age = self.player_age(s)
        adult_label = "未成年" if age is not None and age < 18 else "成年"

        overview_children = [
            self.text_line("当前回合", f"第 {self.current_turn_number(s)} 回合", "schedule", C["lotus"]),
            self.text_line("已完成", f"{self.completed_turn_count(s)} 回合", "schedule", C["lotus"]),
            self.text_line("练习生第", f"{t.trainee_day} 天", "stage", C["lavender"]),
            self.text_line("当前日期", t.current_date.isoformat(), "schedule", C["jade"]),
            self.text_line("星期", self.weekday_label(t), "schedule", C["jade"]),
            self.text_line("月末", "今天是月末" if t.is_month_end else f"还有 {t.days_until_month_end} 天", "stage", C["apricot"]),
            self.text_line("建档日期", t.created_date.isoformat(), "diary", C["lotus"]),
            self.text_line("年龄", self.age_status_text(s), "new_character", C["lavender"]),
            self.text_line("年龄状态", adult_label, "new_character", C["lotus"]),
        ]

        skill_meta = [
            ("dance", "舞蹈", "dance", C["jade"]),
            ("vocal", "声乐", "vocal", C["lotus"]),
            ("rap", "RAP", "rap", C["apricot"]),
            ("stage", "舞台", "stage", C["lavender"]),
            ("camera", "镜头", "camera", C["celadon"]),
            ("language", "语言", "market", C["jade"]),
        ]
        skill_children = []
        for key, label, icon_name, color in skill_meta:
            skill = getattr(s.skills, key)
            skill_children.append(self.metric_bar(label, skill.value, icon_name, color))
        skill_children.append(ft.Divider(color=ft.Colors.with_opacity(0.28, C["line"])))
        skill_children.append(ft.Text("手感", size=12, weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN))
        for key, label, _, color in skill_meta:
            skill = getattr(s.skills, key)
            skill_children.append(self.metric_bar(f"{label}手感", skill.proficiency, "training", color))
        skill_children.append(ft.Divider(color=ft.Colors.with_opacity(0.28, C["line"])))
        skill_children.append(ft.Text("潜在路线", size=12, weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN))
        skill_children.append(self.chip_wrap(["演技（未解锁）", "创作（未解锁）"], C["apricot"], "暂无隐藏路线"))
        if s.skills.traits:
            skill_children.append(ft.Divider(color=ft.Colors.with_opacity(0.28, C["line"])))
            skill_children.append(ft.Text("特殊特质", size=12, weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN))
            skill_children.append(self.chip_wrap([str(x.trait_id) for x in s.skills.traits], C["jade"], "尚未获得任何特质"))

        body_children = [
            self.metric_bar("体力", c.energy, "health", C["jade"]),
            self.metric_bar("睡眠状态", c.sleep_condition, "schedule", C["celadon"]),
            self.metric_bar("嗓音状态", c.voice_condition, "vocal", C["jade"]),
            self.metric_bar("肌肉疲劳", c.muscle_fatigue, "training", C["apricot"], danger_high=True),
            self.metric_bar("伤病风险", c.injury_risk, "safety", C["rouge"], danger_high=True),
        ]
        if c.active_conditions:
            body_children.append(ft.Divider(color=ft.Colors.with_opacity(0.28, C["line"])))
            body_children.append(ft.Text("已发生的身体问题", size=12, weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN))
            for cond in c.active_conditions:
                resolved = "（已恢复）" if cond.resolved_on else ""
                body_children.append(self.text_line(cond.type, f"严重度 {cond.severity}{resolved}", "health", C["rouge"]))
        else:
            body_children.append(ft.Text("当前没有已发生的身体问题。伤病风险只是风险，不代表已经受伤。", size=11, color=C["sub"], font_family=FONT_CN))

        mind_children = [
            self.metric_bar("心情", c.mood, "diary", C["lotus"]),
            self.metric_bar("自信", c.confidence, "app_logo", C["lavender"]),
            self.metric_bar("精神压力", c.stress, "crisis_pr", C["rouge"], danger_high=True),
        ]

        tr = s.trainee
        trainee_children = [
            self.text_line("身份状态", "正式练习生" if tr.status == "active" else str(tr.status), "contract", C["jade"]),
            self.text_line("入社日期", tr.joined_date.isoformat(), "diary", C["lotus"]),
            self.text_line("训练等级", f"Lv.{tr.training_level}", "stage", C["lavender"]),
            self.metric_bar("公司评价", tr.company_evaluation, "contract", C["jade"]),
            self.metric_bar("出勤", tr.attendance, "schedule", C["celadon"]),
            self.metric_bar("纪律", tr.discipline, "training", C["apricot"]),
            self.metric_bar("老师印象", tr.teacher_impression, "stage", C["lotus"]),
        ]

        self.left_panel.controls.extend([
            self.foldout_section("overview", "new_character", "角色总览", f"{p.stage_name or s.save_name} · {self.display_group_name(s)}", overview_children, True),
            self.foldout_section("skills", "stage", "技能", "舞蹈 / 声乐 / RAP / 舞台 / 镜头 / 语言", skill_children, True),
            self.foldout_section("body", "health", "身体状态", f"体力 {c.energy} / 伤病风险 {c.injury_risk} / 嗓音 {c.voice_condition}", body_children, True),
            self.foldout_section("mind", "diary", "心理状态", f"心情 {c.mood} / 压力 {c.stress} / 自信 {c.confidence}", mind_children, True),
            self.foldout_section("trainee", "contract", "练习生身份", f"等级 Lv.{tr.training_level} / 公司评价 {tr.company_evaluation}", trainee_children, True),
        ])

        company = s.company
        w = company.training_weights
        company_children = [
            self.text_line("公司名称", company.name or "未填写", "contract", C["lavender"]),
            self.text_line("公司规模", company.size, "contract", C["jade"]),
            self.text_line("培养路线", company.training_style, "market", C["jade"]),
            self.text_line("管理风格", company.management_style or "待定义", "contract", C["lotus"]),
            self.metric_bar("训练强度", company.training_intensity, "training", C["apricot"], danger_high=True),
            self.metric_bar("资源水平", company.resource_level, "market", C["jade"]),
            ft.Divider(color=ft.Colors.with_opacity(0.28, C["line"])),
            ft.Text("培养权重", size=12, weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN),
            self.metric_bar("舞蹈", int(w.dance * 100), "dance", C["jade"]),
            self.metric_bar("声乐", int(w.vocal * 100), "vocal", C["lotus"]),
            self.metric_bar("RAP", int(w.rap * 100), "rap", C["apricot"]),
            self.metric_bar("舞台", int(w.stage * 100), "stage", C["lavender"]),
            self.metric_bar("镜头", int(w.camera * 100), "camera", C["celadon"]),
            self.metric_bar("语言", int(w.language * 100), "market", C["jade"]),
            self.metric_bar("体能", int(w.fitness * 100), "health", C["jade"]),
        ]

        relationship_children = [
            self.relationship_card(name, rel)
            for name, rel in list(s.relationships.items())[:16]
        ] or [ft.Text("暂无关系记录。关系事件会在后续版本写入关系结果。", size=12, color=C["sub"], font_family=FONT_CN)]

        day_children = [
            self.text_line("时间格数量", "待实现（下一步：1 天 = 8 个 3 小时格）", "schedule", C["lotus"]),
            self.text_line("当前格子", "无" if s.day.current_slot is None else str(s.day.current_slot), "schedule", C["jade"]),
            self.text_line("已完成格子", f"{len(s.day.completed_slots)} 个", "schedule", C["celadon"]),
            self.text_line("今日安排", f"{len(s.day.schedule)} 条", "schedule", C["apricot"]),
            self.chip_wrap([str(x) for x in s.day.completed_slots], C["jade"], "今日尚未完成任何时间格"),
        ]

        self.right_panel.controls.extend([
            self.foldout_section("company", "contract", "公司与培养", f"{company.size} / 资源 {company.resource_level}", company_children, True),
            self.foldout_section("relationships", "romance", "关系状态", f"记录 {len(s.relationships)} 人", relationship_children, False),
            self.foldout_section("day", "schedule", "今日日程", "时间格系统待实现", day_children, True),
        ])

    def refresh_choices(self) -> None:
        """回合引擎重构中：当前不渲染行动选项，仅保留自定义输入。"""
        self.choice_row.controls.clear()

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

    def submit_custom_action(self, e) -> None:
        if self.is_generating:
            self.snack("本回合正在生成中，请等待完成。")
            return
        text = (self.custom_input.value or "").strip()
        if not text:
            self.snack("回合引擎正在重构中。")
            return
        self.submit_action(f"E. {text}")

    def submit_action(self, action: str) -> None:
        self.snack("回合引擎正在重构中，暂时无法提交行动。")

    def snack(self, message: str) -> None:
        self.page.snack_bar = ft.SnackBar(ft.Text(message))
        self.page.snack_bar.open = True
        self.page.update()


