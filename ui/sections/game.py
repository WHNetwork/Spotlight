from __future__ import annotations

from ui.shared import *


class GameMixin:
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

    def relationship_card(self, name: str, rel: Dict[str, Any]) -> ft.Container:
        s = self.state
        role = str(rel.get("role") or "剧情人物")
        label = public_relationship_label(rel, s) if s is not None else str(rel.get("public_relation_state") or "关系")
        cp_allowed = bool(s is not None and is_cp_eligible(rel, s))
        metrics = [
            self.relationship_metric_bar("友情", rel.get("friendship"), C["jade"]),
            self.relationship_metric_bar("信任", rel.get("trust"), C["celadon"]),
            self.relationship_metric_bar("竞争", rel.get("rivalry"), C["apricot"], danger_high=True),
            self.relationship_metric_bar("边界", rel.get("boundary_clarity"), C["lavender"]),
            self.relationship_metric_bar("误读风险", rel.get("relationship_risk"), C["rouge"], danger_high=True),
        ]
        if cp_allowed:
            metrics.append(self.relationship_metric_bar("营业 CP", rel.get("business_cp_level"), C["lotus"], danger_high=True))
        else:
            metrics.append(self.relationship_metric_bar("职业边界", rel.get("professional_boundary_pressure"), C["dai"], danger_high=True))
        last_signals = [str(x) for x in list(rel.get("last_signals") or [])[-3:]]
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
                        ft.Text(f"{role} / {label}", size=10, color=C["sub"], font_family=FONT_CN, max_lines=1),
                    ], spacing=0, expand=True),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                *metrics,
                self.chip_wrap(last_signals, C["lotus"], "暂无最近关系信号"),
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
        self.sync_runtime_context(s)
        age_value = s.age_context.get("age")
        age = f"{age_value}岁" if age_value is not None else str(ch.get("年龄") or "未知")
        nationality = str(ch.get("国籍") or "未填写")
        identity = str(ch.get("身份") or "练习生")
        mbti = str(ch.get("MBTI") or "未设定")
        group_name = self.display_group_name(s)
        mainline = str(s.current_mainline or "日常推进")
        exam_countdown = "考核未知"
        try:
            if isinstance(s.time, dict):
                exam_countdown = f"考核 {s.time.get('next_evaluation_days', s.time.get('assessment_countdown_days', '未知'))} 天"
        except Exception:
            pass

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
                        f"{s.current_stage} · {self.turn_status_text(s)} · {exam_countdown} · {mainline}",
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

        adult_label = "未成年" if s.age_context.get("is_minor") else "成年"
        guardian_label = "需要监护沟通" if s.age_context.get("guardian_required") else "无特殊监护限制"
        overview_children = [
            self.text_line("当前回合", f"第 {self.current_turn_number(s)} 回合", "schedule", C["lotus"]),
            self.text_line("已完成", f"{self.completed_turn_count(s)} 回合", "schedule", C["lotus"]),
            self.text_line("阶段", s.current_stage, "stage", C["lavender"]),
            self.text_line("主线", s.current_mainline, "diary", C["jade"]),
            self.text_line("行程", s.current_schedule, "calendar" if False else "schedule", C["apricot"]),
            self.text_line("日期", s.time.get("current_date"), "schedule", C["jade"]),
            self.text_line("本回合推进", f"{s.time.get('turn_duration_days')} 天", "schedule", C["lotus"]),
            self.text_line("年龄", self.age_status_text(s), "new_character", C["lavender"]),
            self.text_line("年龄状态", adult_label, "new_character", C["lotus"]),
            self.text_line("监护限制", guardian_label, "safety", C["apricot"]),
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

        life_context_children = [
            ft.Text("生理周期", size=12, weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN),
            *period_children,
            ft.Divider(color=ft.Colors.with_opacity(0.28, C["line"])),
            ft.Text("社会环境", size=12, weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN),
            *social_children,
        ]

        self.left_panel.controls.extend([
            self.foldout_section("overview", "new_character", "角色总览", f"{s.character.get('艺名') or s.save_name} · {self.display_group_name(s)}", overview_children, True),
            self.foldout_section("schedule_profile", "schedule", "阶段日程", f"{schedule_profile.get('stage_mode', 'trainee')} / 训练缺口 {schedule_profile.get('practice_quota_need', 0)}", schedule_children, False),
            self.foldout_section("body", "health", "身体状态", f"体力 {body.get('体力')} / 伤病 {body.get('伤病风险')} / 嗓音 {body.get('嗓音状态')}", body_children, True),
            self.foldout_section("mind", "diary", "心理状态", f"心情 {mind.get('心情')} / 压力 {mind.get('精神压力')} / 孤独 {mind.get('孤独感')}", mind_children, True),
            self.foldout_section("career", "stage", "职业属性", f"舞 {career.get('舞蹈实力')} / 声 {career.get('声乐实力')} / 创作 {career.get('创作能力')}", career_children, False),
            self.foldout_section("talents", "app_logo", "天赋与能力", f"能力 {len(abilities)} 个 / 抗压天赋 {talents.get('抗压天赋')}", talent_children, False),
            self.foldout_section("life_context", "period", "生理周期 / 社会环境", f"{period_summary} / 语言压力 {s.social_context.get('language_barrier')}", life_context_children, False),
        ])

        company_children = [
            self.text_line("公司规模", company.get("公司规模", "中型公司"), "contract", C["lavender"]),
            self.text_line("公司路线", company.get("公司路线", "均衡培养"), "market", C["jade"]),
            self.metric_bar("资源池", company.get("资源池", 50), "market", C["jade"]),
            self.metric_bar("出道窗口压力", company.get("出道窗口压力", 45), "stage", C["apricot"], danger_high=True),
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
            self.relationship_card(name, rel)
            for name, rel in list(s.relationships.items())[:16]
        ] or [ft.Text("暂无已解锁人物。新人物出现在剧情或 NPC 反应里后，才会建立个人关系档案。", size=12, color=C["sub"], font_family=FONT_CN)]

        debut = getattr(s, "debut", {}) or {}
        ending = getattr(s, "ending", {}) or {}
        top_ending = (ending.get("candidate_endings") or [{}])[0] if isinstance(ending.get("candidate_endings"), list) and ending.get("candidate_endings") else {}
        debut_ending_children = [
            self.text_line("组合名", self.display_group_name(s), "stage", C["apricot"]),
            self.text_line("出道可能性", f"{debut.get('readiness', 0)} / 概率 {debut.get('probability', 0)}%", "stage", C["lavender"]),
            self.text_line("出道动向", self.player_debut_status(debut), "stage", C["apricot"]),
            self.text_line("窗口倒计时", f"{debut.get('window_turns_left', 0)} 回合", "schedule", C["jade"]),
            self.text_line("候选尝试", debut.get("candidate_attempts", 0), "contract", C["lotus"]),
            self.text_line("最近结果", debut.get("last_result") or "暂无", "diary", C["dai"]),
            ft.Divider(color=ft.Colors.with_opacity(0.35, C["line"])),
            self.text_line("结局窗口", ending.get("window") or ending.get("status") or "closed", "contract", C["jade"]),
            self.text_line("未来方向", self.player_ending_status(ending, top_ending), "contract", C["jade"]),
        ]

        crisis_children = []
        if route:
            crisis_children.append(self.text_line("服务商", self.config.provider_label(), "api", C["jade"]))
            crisis_children.append(self.text_line("叙事模式", self.config.model_policy, "api", C["jade"]))
            crisis_children.append(self.text_line("当前线路", route.actual_model, "api", C["lotus"]))
            crisis_children.append(self.text_line("最近状态", route.turn_kind, "schedule", C["apricot"]))
            crisis_children.append(ft.Divider(color=ft.Colors.with_opacity(0.35, C["line"])))
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
            self.foldout_section("company", "contract", "公司与合约", f"{company.get('公司规模', '中型公司')} / 满意 {company.get('公司满意度')} / 资源池 {company.get('资源池', 50)}", company_children, True),
            self.foldout_section("team", "friendship", "团队关系", f"默契 {team.get('团队默契')} / 信任 {team.get('队内信任度')} / 疲劳 {team.get('营业疲劳')}", team_children, True),
            self.foldout_section("fans", "fans", "粉丝与舆论", f"黑粉 {fans.get('黑粉活跃度')} / 路人 {fans.get('路人好感')} / 撕裂 {fans.get('粉圈撕裂度')}", fans_children, False),
            self.foldout_section("risks", "safety", "风险系统", f"恋爱 {risks.get('恋爱风险')} / 私生 {risks.get('私生风险')} / 公关 {risks.get('公关危机风险')}", risk_children, True),
            self.foldout_section("relationships", "romance", "关系状态", f"记录 {len(s.relationships)} 人 / 工作人员不进入 CP", relationship_children, False),
            self.foldout_section("crisis_flags", "crisis_pr", "危机与长期记录", f"活跃危机 {len(active_crises)} / Flag {len(getattr(s, 'flags', []) or [])}", crisis_children, True),
            self.foldout_section("debut_ending", "stage", "出道 / 结局进度", f"{self.display_group_name(s)} / 准备 {debut.get('readiness', 0)} / {self.player_ending_status(ending, top_ending)}", debut_ending_children, True),
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


