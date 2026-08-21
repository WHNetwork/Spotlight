from __future__ import annotations

from ui.shared import *


class DiaryScheduleSettingsMixin:
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
                    "不写宏大抽象词（命运、宿命、救赎、破碎、深渊），不写模板化抒情（这一刻、终于明白、像被击中、心脏漏拍）。"
                    "情绪藏在具体细节里：衣服上的汗碱、镜面里的倒影、手机屏幕暗掉又亮起来、走廊里谁在谁不在。"
                    "日记语气要受角色MBTI影响：MBTI只影响表达倾向和内在归因，不要写成刻板人格说明。"
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
                        "mbti": ch.get("MBTI"),
                        "mbti_profile": ch.get("MBTI人格倾向"),
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
        # 右上角功能页统一背景：设置 / 存档 / 日记 / 合同 / 行程保持同一套视觉。
        return self.static_page_bg()


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


