from __future__ import annotations

from ui.shared import *


class ContractMixin:
    def profile_table_row(self, label: str, value: Any, icon_name: str = "app_logo", color: str = "#9A8FC4"):
        val = "" if value is None else str(value)
        return ft.Container(
            padding=ft.Padding(left=9, right=9, top=6, bottom=6),
            border_radius=12,
            bgcolor=ft.Colors.with_opacity(0.44, ft.Colors.WHITE),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.32, C["line"])),
            content=ft.Row([
                ft.Container(icon_image(icon_name, 15, 0.88), width=20, height=20, border_radius=10, bgcolor=ft.Colors.with_opacity(0.20, color), alignment=ft.Alignment.CENTER),
                ft.Text(label, width=82, size=self.ui_size(10), color=C["sub"], font_family=FONT_CN),
                ft.Text(val or "—", size=self.ui_size(11), color=C["ink"], weight=ft.FontWeight.W_600, font_family=FONT_CN, expand=True, selectable=True),
            ], spacing=7, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )



    def profile_sheet_section(self, title: str, subtitle: str, icon_name: str, rows: list[tuple], expand: bool = True):
        return ft.Container(
            expand=expand,
            padding=14,
            border_radius=22,
            bgcolor=ft.Colors.with_opacity(0.48, ft.Colors.WHITE),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.42, C["line"])),
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        icon_image(icon_name, 18, 0.88),
                        width=28,
                        height=28,
                        border_radius=14,
                        bgcolor=ft.Colors.with_opacity(0.26, C["lotus"]),
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Column([
                        ft.Text(title, size=self.ui_size(14), weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN),
                        ft.Text(subtitle, size=self.ui_size(10), color=C["sub"], font_family=FONT_CN),
                    ], spacing=0, expand=True),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                self.profile_table(rows),
            ], spacing=10),
        )

    def profile_sheet_panel(self, s: GameState, basic_rows: list[tuple], career_rows: list[tuple], body_mind_rows: list[tuple], social_rows: list[tuple], relation_rows: list[tuple], layout: Dict[str, int]):
        """A single resume sheet instead of scattered floating cards."""
        return ft.Container(
            expand=True,
            padding=18,
            border_radius=34,
            bgcolor=ft.Colors.with_opacity(0.76, ft.Colors.WHITE),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.74, ft.Colors.WHITE)),
            shadow=ft.BoxShadow(
                blur_radius=30,
                spread_radius=0,
                color=ft.Colors.with_opacity(0.11, C["dai"]),
                offset=ft.Offset(0, 10),
            ),
            content=ft.Column([
                ft.Container(content=self.resume_header_card(s)),
                ft.Row([
                    self.profile_sheet_section("基础信息", "身份、组合与当前阶段", "new_character", basic_rows),
                    self.profile_sheet_section("职业能力", "练习、舞台与镜头相关属性", "stage", career_rows),
                ], spacing=14, vertical_alignment=ft.CrossAxisAlignment.START),
                ft.Row([
                    self.profile_sheet_section("身体与心理", "状态、压力与恢复", "health", body_mind_rows),
                    self.profile_sheet_section("社会环境", "国籍、学校、家庭与适应压力", "school", social_rows),
                    self.profile_sheet_section("关系概览", "团队、粉丝与外部反馈", "friendship", relation_rows),
                ], spacing=14, vertical_alignment=ft.CrossAxisAlignment.START),
            ], spacing=14, scroll=ft.ScrollMode.AUTO, expand=True),
        )

    def profile_grid_card(self, title: str, subtitle: str, icon_name: str, rows: list[tuple], width: int):
        return self.static_page_card(
            title,
            subtitle,
            icon_name,
            self.profile_table(rows),
            width=width,
        )

    def contract_layout_sizes(self) -> Dict[str, int]:
        """Compute fixed card widths so the profile page does not form a broken masonry layout."""
        try:
            vw = int(self.page.width or 1360)
        except Exception:
            vw = 1360
        # subpage horizontal padding is about 48. Left nav + right summary + 2 spacings.
        main_w = max(780, vw - 48 - 298 - 298 - 36)
        w3 = max(270, min(350, int((main_w - 36) / 3)))
        w2 = max(420, min(560, int((main_w - 18) / 2)))
        return {"side": 286, "summary": 286, "main": main_w, "w3": w3, "w2": w2}

    def profile_table(self, rows: list[tuple], empty: str = "暂无数据"):
        if not rows:
            return ft.Text(empty, size=self.ui_size(12), color=C["sub"], font_family=FONT_CN)
        controls = []
        for row in rows:
            label = row[0]
            value = row[1] if len(row) > 1 else ""
            icon_name = row[2] if len(row) > 2 else "app_logo"
            color = row[3] if len(row) > 3 else C["lotus"]
            controls.append(self.profile_table_row(label, value, icon_name, color))
        return ft.Column(controls, spacing=6)

    def resume_header_card(self, s: GameState):
        p = s.player
        art_name = str(p.stage_name or p.name or s.save_name or "练习生")
        real_name = str(p.name or "").strip()
        nationality = str(p.nationality or "未填写")
        age = self.age_status_text(s)
        identity = str(p.identity_source or "练习生")
        mbti = str(p.mbti or "未设定")
        group_name = self.display_group_name(s)

        return ft.Container(
            padding=22,
            border_radius=30,
            bgcolor=ft.Colors.with_opacity(0.84, ft.Colors.WHITE),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.70, ft.Colors.WHITE)),
            shadow=ft.BoxShadow(blur_radius=28, color=ft.Colors.with_opacity(0.10, C["dai"]), offset=ft.Offset(0, 10)),
            content=ft.Row([
                ft.Stack([
                    ft.Container(
                        content=ft.Image(src=self.get_character_avatar_src(), width=96, height=96, fit="cover"),
                        width=96,
                        height=96,
                        border_radius=30,
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                        border=ft.Border.all(2, ft.Colors.with_opacity(0.70, ft.Colors.WHITE)),
                    ),
                    ft.Container(
                        content=ft.Image(src=flag_src_from_nationality(nationality), width=26, height=26, fit="cover"),
                        width=32,
                        height=32,
                        border_radius=16,
                        bgcolor=ft.Colors.WHITE,
                        alignment=ft.Alignment.CENTER,
                        left=70,
                        top=70,
                    ),
                ], width=108, height=108),
                ft.Column([
                    ft.Row([
                        ft.Text(art_name, size=self.ui_size(26), weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN, max_lines=1),
                        self.mini_chip(group_name, C["apricot"]),
                        self.mini_chip(str(nationality), C["jade"]),
                        self.mini_chip(age, C["lotus"]),
                        self.mini_chip(mbti, C["lavender"]),
                    ], spacing=8, wrap=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Text(
                        f"{real_name + ' · ' if real_name and real_name != art_name else ''}{identity}",
                        size=self.ui_size(13),
                        color=C["sub"],
                        font_family=FONT_CN,
                    ),
                    ft.Text(
                        f"{self.stage_label(s)} · {self.turn_status_text(s)} · {s.time.current_date} · 练习生第 {s.time.trainee_day} 天",
                        size=self.ui_size(12),
                        color=C["dai"],
                        font_family=FONT_CN,
                        max_lines=2,
                    ),
                ], spacing=6, expand=True),
            ], spacing=18, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )

    def contract_tab_button(self, label: str, icon_name: str, active: bool, handler):
        color = C["jade"] if active else C["lotus"]
        return ft.Container(
            padding=ft.Padding(left=14, right=14, top=10, bottom=10),
            border_radius=20,
            bgcolor=ft.Colors.with_opacity(0.86 if active else 0.68, color if active else ft.Colors.WHITE),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.52, color)),
            ink=True,
            on_click=handler,
            content=ft.Row([
                icon_image(icon_name, 18, 0.92),
                ft.Text(label, size=self.ui_size(12), color=C["ink"] if active else C["dai"], weight=ft.FontWeight.W_700, font_family=FONT_CN),
            ], spacing=7, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )

    def show_contract_page(self, tab: str = "profile") -> None:
        if not self.load_latest_for_static_page():
            self.static_empty_page("档案与合约中心", "个人档案、公司合约与边界规则", "contract")
            return
        self.subpage_resize_refresh("contract")

        s = self.state
        p = s.player
        company = s.company
        c = s.condition
        group_name = self.display_group_name(s)
        layout = self.contract_layout_sizes()

        contract_name = "练习生协议"
        contract_phase = "训练观察期"
        activity_limit = "外出、公开社交、外部合作均需公司确认"

        top_info = ft.Container(
            width=layout["side"],
            padding=16,
            border_radius=28,
            bgcolor=ft.Colors.with_opacity(0.82, ft.Colors.WHITE),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.68, ft.Colors.WHITE)),
            shadow=ft.BoxShadow(blur_radius=24, color=ft.Colors.with_opacity(0.10, C["dai"]), offset=ft.Offset(0, 8)),
            content=ft.Column([
                ft.Row([
                    ft.Container(icon_image("contract", 24, 0.9), width=38, height=38, border_radius=19, bgcolor=ft.Colors.with_opacity(0.32, C["lotus"]), alignment=ft.Alignment.CENTER),
                    ft.Column([
                        ft.Text("档案导航", size=self.ui_size(17), weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN),
                        ft.Text(p.stage_name or p.name or s.save_name, size=self.ui_size(11), color=C["sub"], font_family=FONT_CN),
                    ], spacing=1, expand=True),
                ], spacing=10),
                ft.Divider(height=14, color=ft.Colors.with_opacity(0.30, C["line"])),
                self.text_line("组合名", group_name, "stage", C["apricot"]),
                self.text_line("当前合约", contract_name, "contract", C["jade"]),
                self.text_line("合约阶段", contract_phase, "schedule", C["lavender"]),
                ft.Divider(height=14, color=ft.Colors.with_opacity(0.30, C["line"])),
                self.contract_tab_button("个人档案", "new_character", tab == "profile", lambda e: self.show_contract_page("profile")),
                self.contract_tab_button("合同信息", "contract", tab == "contract", lambda e: self.show_contract_page("contract")),
            ], spacing=8),
        )

        risk_side = self.static_page_card(
            "快速摘要",
            "公司视角下的当前状态",
            "safety",
            ft.Column([
                self.text_line("公司规模", company.size, "contract", C["lavender"]),
                self.metric_bar("资源水平", company.resource_level, "market", C["jade"]),
                self.metric_bar("训练强度", company.training_intensity, "training", C["apricot"], danger_high=True),
                self.metric_bar("公司评价", s.trainee.company_evaluation, "contract", C["jade"]),
                self.metric_bar("纪律", s.trainee.discipline, "training", C["apricot"], danger_high=True),
                self.metric_bar("伤病风险", c.injury_risk, "crisis_pr", C["rouge"], danger_high=True),
                self.metric_bar("精神压力", c.stress, "crisis_pr", C["rouge"], danger_high=True),
            ], spacing=7),
            width=layout["summary"],
        )

        if tab == "contract":
            clause_text = "\n".join([
                f"• 活动限制：{activity_limit}",
                "• 住宿管理：宿舍、门禁、夜间外出和访客管理由公司统一记录。",
                "• 训练考核：日常培养权重、训练强度与公司评价会影响资源投入。",
                "• 社交媒体：公开发声、照片发布、直播内容需遵守公司边界。",
                "• 私人关系：恋爱、暧昧、工作人员越界、同龄关系曝光都会进入风险系统。",
                "• 学业与监护：未成年、海外成员会额外涉及监护人、学校、签证与家庭沟通。",
                "• 伤病上报：伤病、睡眠失衡与心理压力会影响训练安排和合同风险。",
            ])
            contract_body = ft.Column([
                ft.Row([
                    self.static_page_card(
                        "当前合同概况",
                        "合同类型、阶段和公司绑定关系",
                        "contract",
                        self.profile_table([
                            ("组合名", group_name, "stage", C["apricot"]),
                            ("合同类型", contract_name, "contract", C["jade"]),
                            ("签约阶段", contract_phase, "schedule", C["lavender"]),
                            ("所属公司", company.name or "未填写", "market", C["jade"]),
                            ("公司规模", company.size, "contract", C["lavender"]),
                            ("培养路线", company.training_style, "market", C["jade"]),
                            ("训练强度", company.training_intensity, "training", C["jade"]),
                            ("资源水平", company.resource_level, "market", C["celadon"]),
                            ("公司评价", s.trainee.company_evaluation, "stage", C["lavender"]),
                        ]),
                        width=layout["w2"],
                    ),
                    self.static_page_card(
                        "身体与心理",
                        "当前状态摘要",
                        "safety",
                        ft.Column([
                            self.metric_bar("体力", c.energy, "schedule", C["jade"]),
                            self.metric_bar("睡眠状态", c.sleep_condition, "safety", C["jade"]),
                            self.metric_bar("肌肉疲劳", c.muscle_fatigue, "training", C["rouge"], danger_high=True),
                            self.metric_bar("伤病风险", c.injury_risk, "health", C["rouge"], danger_high=True),
                            self.metric_bar("心情", c.mood, "romance", C["lotus"]),
                            self.metric_bar("精神压力", c.stress, "staff_boundary", C["rouge"], danger_high=True),
                        ], spacing=7),
                        width=layout["w2"],
                    ),
                ], spacing=18, alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.START),
                self.static_page_card("核心条款", "练习生阶段合同条款", "staff_boundary", self.static_text_block(clause_text, 8, 16)),
            ], spacing=18, scroll=ft.ScrollMode.AUTO, expand=True)
            main_panel = ft.Container(expand=True, content=contract_body)
        else:
            height_text = f"{p.height_cm}cm" if p.height_cm is not None else "未填写"
            basic_rows = [
                ("本名", p.name or "未填写", "new_character", C["lotus"]),
                ("艺名", p.stage_name or "未填写", "stage", C["lavender"]),
                ("组合名", group_name, "stage", C["apricot"]),
                ("身份", p.identity_source or "练习生", "contract", C["jade"]),
                ("MBTI", p.mbti or "未设定", "diary", C["lavender"]),
                ("年龄", self.age_status_text(s), "new_character", C["lotus"]),
                ("国籍", p.nationality or "未填写", "market", C["jade"]),
                ("身高", height_text, "new_character", C["jade"]),
                ("当前阶段", self.stage_label(s), "schedule", C["lavender"]),
                ("练习生第", f"{s.time.trainee_day} 天", "diary", C["jade"]),
                ("当前日期", s.time.current_date.isoformat(), "schedule", C["apricot"]),
                ("入社日期", s.trainee.joined_date.isoformat(), "diary", C["jade"]),
            ]
            career_rows = [
                ("舞蹈", s.skills.dance.value, "dance", C["jade"]),
                ("声乐", s.skills.vocal.value, "vocal", C["lotus"]),
                ("RAP", s.skills.rap.value, "rap", C["apricot"]),
                ("舞台", s.skills.stage.value, "stage", C["lavender"]),
                ("镜头", s.skills.camera.value, "camera", C["celadon"]),
                ("语言", s.skills.language.value, "market", C["jade"]),
                ("演技（未解锁）", "隐藏", "stage", C["apricot"]),
                ("创作（未解锁）", "隐藏", "music", C["apricot"]),
            ]
            body_mind_rows = [
                ("体力", c.energy, "health", C["jade"]),
                ("睡眠状态", c.sleep_condition, "schedule", C["celadon"]),
                ("嗓音状态", c.voice_condition, "vocal", C["jade"]),
                ("肌肉疲劳", c.muscle_fatigue, "training", C["apricot"]),
                ("伤病风险", c.injury_risk, "safety", C["rouge"]),
                ("心情", c.mood, "diary", C["lotus"]),
                ("自信", c.confidence, "app_logo", C["lavender"]),
                ("精神压力", c.stress, "crisis_pr", C["rouge"]),
            ]
            social_rows = [
                ("身高", f"{p.height_cm}cm" if p.height_cm is not None else "未填写", "new_character", C["jade"]),
                ("特长", p.strengths or "未填写", "stage", C["jade"]),
                ("弱项", p.weak_points or "未填写", "health", C["apricot"]),
                ("家庭背景", p.family_background or "未填写", "family", C["jade"]),
                ("练习生经历", p.background or "未填写", "contract", C["jade"]),
                ("训练等级", f"Lv.{s.trainee.training_level}", "stage", C["lavender"]),
                ("出勤", s.trainee.attendance, "schedule", C["jade"]),
                ("老师印象", s.trainee.teacher_impression, "stage", C["lotus"]),
            ]
            relation_rows = [
                ("关系记录", f"{len(s.relationships)} 人", "friendship", C["jade"]),
            ]
            for name, rel in list(s.relationships.items())[:6]:
                relation_rows.append((str(name), f"熟悉 {rel.familiarity} / 信任 {rel.trust} / 亲近 {rel.closeness} / 张力 {rel.tension}", "friendship", C["jade"]))

            main_panel = ft.Container(
                expand=True,
                content=self.profile_sheet_panel(
                    s,
                    basic_rows,
                    career_rows,
                    body_mind_rows,
                    social_rows,
                    relation_rows,
                    layout,
                ),
            )


        mode = self.subpage_layout_mode()
        if mode == "narrow":
            body = ft.Column(
                [top_info, main_panel, risk_side],
                spacing=18,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        else:
            body = ft.Row(
                [top_info, main_panel, risk_side],
                spacing=18,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                expand=True,
            )

        self.subpage_shell("档案与合约中心", self.active_character_label(), "contract", body)


