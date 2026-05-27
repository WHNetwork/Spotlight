from __future__ import annotations

from typing import Optional, Dict, Any

import flet as ft
from loguru import logger

from core.config import AppConfig
from core.engine import TurnEngine
from core.llm import LLMError, DeepSeekProvider
from core.models import GameState, Choice
from core.storage import SaveStorage
from core.action_validator import ActionBlockedError
from core.character_validator import validate_character_input, CharacterValidationError
from core.relationship_system import relationship_ui_summary


def icon(name: str):
    return getattr(ft.Icons, name, None)


def asset(path: str) -> str:
    return path.replace("\\", "/")


def icon_image(name: str, size: int = 24, opacity: float = 1.0) -> ft.Image:
    return ft.Image(src=asset(f"icons/{name}.png"), width=size, height=size, fit=ft.ImageFit.CONTAIN, opacity=opacity)

def glass_color(opacity: float = 0.72) -> str:
    return ft.Colors.with_opacity(opacity, ft.Colors.WHITE)


class KpopApp:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.page.title = "星光练习室"
        self.page.window_width = 1320
        self.page.window_height = 860
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.config = AppConfig()
        self.storage = SaveStorage()
        self.save_id: Optional[int] = None
        self.state: Optional[GameState] = None
        self.story_view = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)
        self.left_panel = ft.Column(width=300, scroll=ft.ScrollMode.AUTO)
        self.right_panel = ft.Column(width=340, scroll=ft.ScrollMode.AUTO)
        self.choice_row = ft.Column()
        self.custom_input = ft.TextField(label="自定义行动", multiline=True, min_lines=2, max_lines=4, expand=True)

    def run(self) -> None:
        self.show_home()

    def clear(self) -> None:
        self.page.controls.clear()

    def show_home(self) -> None:
        self.clear()
        self.page.padding = 0
        self.page.bgcolor = ft.Colors.WHITE
        latest_id = self.storage.latest_save_id()

        def top_icon(name: str, tooltip: str, handler):
            return ft.Container(
                content=icon_image(name, 28),
                width=54,
                height=54,
                bgcolor=glass_color(0.64),
                border=ft.border.all(1, ft.Colors.with_opacity(0.55, ft.Colors.WHITE)),
                border_radius=18,
                alignment=ft.alignment.center,
                tooltip=tooltip,
                on_click=handler,
                ink=True,
                shadow=ft.BoxShadow(blur_radius=22, spread_radius=0, color=ft.Colors.with_opacity(0.12, ft.Colors.BLUE_GREY), offset=ft.Offset(0, 8)),
            )

        def menu_button(title: str, subtitle: str, icon_name: str, english: str, handler, disabled: bool = False):
            bg = ft.Colors.with_opacity(0.78 if not disabled else 0.42, ft.Colors.WHITE)
            fg = "#56617A" if not disabled else "#9AA0B5"
            return ft.Container(
                width=430,
                height=76,
                padding=ft.padding.symmetric(horizontal=22, vertical=10),
                border_radius=38,
                bgcolor=bg,
                border=ft.border.all(1, ft.Colors.with_opacity(0.82, "#FFFFFF")),
                shadow=ft.BoxShadow(blur_radius=28, spread_radius=0, color=ft.Colors.with_opacity(0.12, "#536B89"), offset=ft.Offset(0, 10)),
                opacity=0.62 if disabled else 1,
                on_click=None if disabled else handler,
                ink=not disabled,
                content=ft.Row([
                    ft.Container(icon_image(icon_name, 36, 0.95 if not disabled else 0.4), width=48, height=48, border_radius=24, bgcolor=ft.Colors.with_opacity(0.52, "#F7ECEE"), alignment=ft.alignment.center),
                    ft.Column([
                        ft.Text(title, size=18, weight=ft.FontWeight.W_600, color=fg),
                        ft.Text(subtitle, size=11, color=ft.Colors.with_opacity(0.70, fg)),
                    ], spacing=2, expand=True),
                    ft.Text(english, size=10, color=ft.Colors.with_opacity(0.48, fg), italic=True),
                ], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            )

        profile_card = ft.Container(
            width=320,
            height=126,
            padding=18,
            border_radius=24,
            bgcolor=glass_color(0.60),
            border=ft.border.all(1, ft.Colors.with_opacity(0.72, ft.Colors.WHITE)),
            shadow=ft.BoxShadow(blur_radius=26, color=ft.Colors.with_opacity(0.10, "#536B89"), offset=ft.Offset(0, 10)),
            content=ft.Row([
                ft.Container(icon_image("app_logo", 72), width=78, height=78, border_radius=39, bgcolor=ft.Colors.with_opacity(0.55, "#F7ECEE"), alignment=ft.alignment.center),
                ft.Column([
                    ft.Text("星光练习室", size=18, weight=ft.FontWeight.W_700, color="#56617A"),
                    ft.Text("Starlight Practice Room", size=11, italic=True, color="#8C88A6"),
                    ft.Container(height=6),
                    ft.Text("最新存档可读取" if latest_id is not None else "尚未开始旅程", size=12, color="#7D8CA0"),
                ], spacing=1),
            ], spacing=12),
        )

        news_card = ft.Container(
            width=410,
            padding=22,
            border_radius=24,
            bgcolor=glass_color(0.56),
            border=ft.border.all(1, ft.Colors.with_opacity(0.72, ft.Colors.WHITE)),
            shadow=ft.BoxShadow(blur_radius=24, color=ft.Colors.with_opacity(0.10, "#536B89"), offset=ft.Offset(0, 10)),
            content=ft.Column([
                ft.Row([icon_image("diary", 22), ft.Text("星光日报", size=16, weight=ft.FontWeight.W_700, color="#6A6684")], spacing=8),
                ft.Text("今日行程更新", size=13, color="#7D8CA0"),
                ft.Text("· 个人档案：开启角色创建", size=13, color="#7D8CA0"),
                ft.Text("· 存档：支持 DeepSeek 正式回合", size=13, color="#7D8CA0"),
                ft.Text("· UI：主页视觉重制中", size=13, color="#7D8CA0"),
            ], spacing=6),
        )

        title_block = ft.Column([
            ft.Text("✦", size=36, color="#B7A6D8", text_align=ft.TextAlign.CENTER),
            ft.Text("星光练习室", size=64, weight=ft.FontWeight.W_700, color="#8E88B8", text_align=ft.TextAlign.CENTER),
            ft.Text("Starlight Practice Room", size=18, italic=True, color="#9A96B7", text_align=ft.TextAlign.CENTER),
            ft.Text("少女偶像人生模拟器", size=16, color="#7D8CA0", text_align=ft.TextAlign.CENTER),
        ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

        menu = ft.Column([
            menu_button("继续旅程", "读取最近一次存档，回到练习室", "app_logo", "CONTINUE", lambda e: self.load_latest(), disabled=latest_id is None),
            menu_button("新的人生", "创建角色，从第一天报到开始", "new_character", "NEW GAME", lambda e: self.show_character_create()),
            menu_button("读取存档", "查看所有保存的故事线", "save_archive", "LOAD GAME", lambda e: self.show_save_list()),
            menu_button("系统设置", "配置 DeepSeek 模型与 API", "settings", "SETTINGS", lambda e: self.show_settings()),
        ], spacing=22, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

        home = ft.Stack([
            ft.Image(src=asset("backgrounds/home_bg.png"), fit=ft.ImageFit.COVER, expand=True),
            ft.Container(expand=True, bgcolor=ft.Colors.with_opacity(0.16, ft.Colors.WHITE)),
            ft.Container(
                expand=True,
                padding=ft.padding.only(left=42, right=42, top=30, bottom=34),
                content=ft.Column([
                    ft.Row([
                        profile_card,
                        ft.Container(expand=True),
                        top_icon("contract", "合同/说明", lambda e: self.snack("主页 UI 阶段：合同页稍后设计。")),
                        top_icon("diary", "星光日记", lambda e: self.snack("主页 UI 阶段：日记页稍后设计。")),
                        top_icon("schedule", "行程", lambda e: self.snack("主页 UI 阶段：行程页稍后设计。")),
                        top_icon("settings", "设置", lambda e: self.show_settings()),
                    ], spacing=14, vertical_alignment=ft.CrossAxisAlignment.START),
                    ft.Container(expand=True),
                    ft.Row([
                        ft.Container(width=430),
                        ft.Column([title_block, ft.Container(height=34), menu], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
                        ft.Container(width=430),
                    ], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Container(expand=True),
                    ft.Row([
                        news_card,
                        ft.Container(expand=True),
                        ft.Container(
                            width=470,
                            padding=ft.padding.symmetric(horizontal=20, vertical=14),
                            border_radius=20,
                            bgcolor=ft.Colors.with_opacity(0.36, ft.Colors.WHITE),
                            content=ft.Text("“每一束星光，都始于练习室的微光。”", size=24, color="#8E88B8", italic=True, text_align=ft.TextAlign.RIGHT),
                        ),
                    ], vertical_alignment=ft.CrossAxisAlignment.END),
                ], expand=True),
            ),
        ], expand=True)

        self.page.add(home)
        self.page.update()

    def show_settings(self) -> None:
        self.clear()
        api_key = ft.TextField(label="DeepSeek API Key", password=True, can_reveal_password=True, value="", hint_text="sk-...", width=660)
        base_url = ft.TextField(label="Base URL", value=self.config.base_url, width=660)
        model_policy = ft.Dropdown(label="模型策略", width=660, value=self.config.model_policy, options=[ft.dropdown.Option("auto"), ft.dropdown.Option("flash"), ft.dropdown.Option("pro"), ft.dropdown.Option("custom")])
        flash_model = ft.TextField(label="Flash Model", value=self.config.flash_model, width=660)
        pro_model = ft.TextField(label="Pro Model", value=self.config.pro_model, width=660)
        custom_model = ft.TextField(label="Custom Model", value=self.config.custom_model, width=660)
        status = ft.Text("", color=ft.Colors.GREEN)

        def save_settings(e):
            self.config.save(base_url.value or "https://api.deepseek.com", model_policy.value or "auto", flash_model.value or "deepseek-v4-flash", pro_model.value or "deepseek-v4-pro", custom_model.value or "deepseek-chat")
            if api_key.value:
                self.config.set_api_key(api_key.value)
            status.color = ft.Colors.GREEN
            status.value = "设置已保存。"
            self.page.update()

        def test_model(e, tier: str):
            save_settings(e)
            model = self.config.model_for_tier(tier)
            status.color = ft.Colors.BLUE
            status.value = f"正在测试 DeepSeek API：{model}"
            self.page.update()
            try:
                provider = DeepSeekProvider(self.config)
                raw = provider.generate([{"role": "system", "content": "你是一个简洁的中文助手。"}, {"role": "user", "content": "请只回复：DeepSeek API 连接成功。"}], model=model)
                status.color = ft.Colors.GREEN
                status.value = f"✅ 调用成功。模型：{model}。返回：{raw[:120]}"
            except Exception as exc:
                status.color = ft.Colors.RED
                status.value = f"❌ 调用失败：{exc}"
            self.page.update()

        self.page.add(ft.Container(content=ft.Column([
            ft.Text("设置", size=28, weight=ft.FontWeight.BOLD),
            ft.Text("auto：普通回合用 Flash，重大剧情/危机/公关/续约/恋爱曝光用 Pro。正式回合必须调用 DeepSeek。"),
            api_key, base_url, model_policy, flash_model, pro_model, custom_model,
            ft.Row([
                ft.ElevatedButton("保存设置", icon=icon("SAVE"), on_click=save_settings),
                ft.ElevatedButton("测试 Flash", on_click=lambda e: test_model(e, "flash")),
                ft.ElevatedButton("测试 Pro", on_click=lambda e: test_model(e, "pro")),
                ft.OutlinedButton("返回首页", on_click=lambda e: self.show_home()),
            ], wrap=True),
            status,
        ], spacing=14, scroll=ft.ScrollMode.AUTO), padding=30))
        self.page.update()

    def show_character_create(self) -> None:
        self.clear()
        fields: Dict[str, ft.TextField] = {}
        labels = ["艺名", "本名", "国籍", "年龄", "身高", "外貌特征", "性格", "爱好", "特长", "弱项", "家庭状况", "练习生经历", "在团定位", "你希望观众记住你的什么", "你不希望剧情触碰的内容", "其他补充"]
        for label in labels:
            fields[label] = ft.TextField(label=label, width=470)
        identity = ft.Dropdown(label="身份", width=470, options=[ft.dropdown.Option("素人学生被星探发现"), ft.dropdown.Option("富二代 / 优渥家庭出身"), ft.dropdown.Option("某位 KPOP 顶流爱豆的妹妹 / 亲属"), ft.dropdown.Option("海外追梦练习生"), ft.dropdown.Option("前运动员转型练习生"), ft.dropdown.Option("选秀节目淘汰者"), ft.dropdown.Option("小公司前成员 / 再出道"), ft.dropdown.Option("自定义身份")], value="素人学生被星探发现")
        source_tags = ft.TextField(label="出身来源标签，多个用逗号分隔", width=470, hint_text="街头星探, 校园舞蹈社, 前运动员")
        timeline = ft.Dropdown(label="时间线", width=470, options=[ft.dropdown.Option("练习生阶段"), ft.dropdown.Option("出道前一天"), ft.dropdown.Option("回归瓶颈期"), ft.dropdown.Option("续约前一年")], value="练习生阶段")
        period_mode = ft.Dropdown(label="生理周期系统", width=470, options=[ft.dropdown.Option("简化"), ft.dropdown.Option("开启"), ft.dropdown.Option("关闭")], value="简化")
        status = ft.Text("", color=ft.Colors.RED)

        def create(e):
            raw_character: Dict[str, Any] = {"身份": identity.value, "出身来源标签": [s.strip() for s in (source_tags.value or "").split(",") if s.strip()], "时间线": timeline.value, "生理周期系统": period_mode.value}
            for k, field in fields.items():
                raw_character[k] = field.value or ""
            try:
                normalized = validate_character_input(raw_character)
            except CharacterValidationError as exc:
                status.color = ft.Colors.RED
                status.value = "角色创建信息有误：\n" + "\n".join(f"• {e}" for e in exc.errors)
                self.page.update()
                return
            if normalized.warnings:
                status.color = ft.Colors.ORANGE
                status.value = "提示：\n" + "\n".join(f"• {w}" for w in normalized.warnings)
                self.page.update()

            engine = TurnEngine(self.storage, self.config)
            state = engine.create_initial_state(normalized.data)
            self.save_id = self.storage.create_save(state)
            self.state = state
            self.show_game(initial=True)

        form = ft.Column([ft.Text("🎤 角色创建", size=28, weight=ft.FontWeight.BOLD), identity, source_tags, timeline, period_mode, ft.Divider()], spacing=10, scroll=ft.ScrollMode.AUTO)
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

    def show_game(self, initial: bool = False) -> None:
        if self.state is None:
            self.show_home()
            return
        self.clear()
        self.story_view = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=14)
        self.left_panel = ft.Column(width=310, scroll=ft.ScrollMode.AUTO, spacing=8)
        self.right_panel = ft.Column(width=350, scroll=ft.ScrollMode.AUTO, spacing=8)
        self.choice_row = ft.Column(spacing=8)
        self.custom_input = ft.TextField(label="自定义行动", multiline=True, min_lines=2, max_lines=4, expand=True)
        self.story_view.controls.append(ft.Text("角色已创建。你可以从下方选择第一步行动。" if initial or self.state.turn == 0 else self.state.last_public_summary or "存档已载入。", size=16))
        self.refresh_panels()
        self.refresh_choices()
        top_bar = ft.Row([ft.Row([icon_image("app_logo", 30), ft.Text("星光练习室", size=22, weight=ft.FontWeight.BOLD, color="#56617A")], spacing=8), ft.Container(expand=True), ft.TextButton("设置", on_click=lambda e: self.show_settings()), ft.TextButton("存档", on_click=lambda e: self.show_save_list()), ft.TextButton("首页", on_click=lambda e: self.show_home())])
        main_layout = ft.Column([top_bar, ft.Divider(), ft.Row([ft.Container(self.left_panel, padding=12, bgcolor=ft.Colors.GREY_50, border_radius=10), ft.Container(self.story_view, expand=True, padding=12, bgcolor=ft.Colors.WHITE, border_radius=10), ft.Container(self.right_panel, padding=12, bgcolor=ft.Colors.GREY_50, border_radius=10)], expand=True, vertical_alignment=ft.CrossAxisAlignment.START), ft.Divider(), self.choice_row], expand=True)
        self.page.add(ft.Container(content=main_layout, padding=12, expand=True))
        self.page.update()

    def refresh_panels(self) -> None:
        assert self.state is not None
        s = self.state
        self.left_panel.controls.clear()
        self.right_panel.controls.clear()
        self.left_panel.controls.extend([ft.Text("状态", size=20, weight=ft.FontWeight.BOLD), ft.Text(f"回合：{s.turn}"), ft.Text(f"阶段：{s.current_stage}"), ft.Text(f"主线：{s.current_mainline}"), ft.Text(f"行程：{s.current_schedule}"), ft.Text(f"日期：{s.time.get('current_date')} / 本回合：{s.time.get('turn_duration_days')} 天"), ft.Text(f"年龄段：{s.age_context.get('age_group')} / 未成年：{s.age_context.get('is_minor')} / 考核倒计时：{s.time.get('next_evaluation_days')} 天"), ft.Divider(), ft.Text("社会环境", weight=ft.FontWeight.BOLD), ft.Text(f"国籍：{s.social_context.get('nationality')} / 语言压力：{s.social_context.get('language_barrier')} / 文化适应：{s.social_context.get('cultural_adaptation')}"), ft.Text(f"学校：{s.school.get('school_type')} / 出勤压力：{s.school.get('attendance_pressure')} / 作业压力：{s.school.get('homework_pressure')}"), ft.Text(f"家庭支持：{s.family.get('emotional_support')} / 家庭冲突：{s.family.get('conflict_level')} / 控制欲：{s.family.get('control_level')}"), ft.Divider(), ft.Text("天赋", weight=ft.FontWeight.BOLD), *[ft.Text(f"{k}: {v}") for k, v in s.talents.items()], ft.Divider(), ft.Text("职业属性", weight=ft.FontWeight.BOLD), *[ft.Text(f"{k}: {v}") for k, v in s.career.items()], ft.Divider(), ft.Text("已解锁能力", weight=ft.FontWeight.BOLD), *[ft.Text(f"• {a}") for a in s.abilities[-8:]], ft.Divider(), ft.Text("生理周期", weight=ft.FontWeight.BOLD), ft.Text(f"模式: {s.period.get('mode')} / 阶段: {s.period.get('phase')} / day {s.period.get('cycle_day')}"), ft.Text(f"痛感: {s.period.get('pain_level')} / 压力: {s.period.get('flow_pressure')} / 不规律风险: {s.period.get('irregularity_risk')}"), ft.Divider(), ft.Text("身体状态", weight=ft.FontWeight.BOLD), *[ft.Text(f"{k}: {v}") for k, v in s.body.items()], ft.Divider(), ft.Text("心理状态", weight=ft.FontWeight.BOLD), *[ft.Text(f"{k}: {v}") for k, v in s.mind.items()]])
        route = s.route_history[-1] if s.route_history else None
        self.right_panel.controls.extend([ft.Text("系统", size=20, weight=ft.FontWeight.BOLD), ft.Text(f"模型策略：{self.config.model_policy}"), ft.Text(f"最近模型：{route.actual_model if route else '尚未调用'}"), ft.Text(f"最近回合类型：{route.turn_kind if route else '无'}"), ft.Divider(), ft.Text("公司", weight=ft.FontWeight.BOLD), *[ft.Text(f"{k}: {v}") for k, v in s.company.items()], ft.Divider(), ft.Text("团队", weight=ft.FontWeight.BOLD), *[ft.Text(f"{k}: {v}") for k, v in s.team.items()], ft.Divider(), ft.Text("风险", weight=ft.FontWeight.BOLD), *[ft.Text(f"{k}: {v}") for k, v in s.risks.items()], ft.Divider(), ft.Text("少女心事", weight=ft.FontWeight.BOLD), *[ft.Text(f"{k}: {v}") for k, v in s.inner_life.items()], ft.Text("心事条目", weight=ft.FontWeight.BOLD), *[ft.Text(f"• {sec.get('type')} / {sec.get('target')} / {sec.get('intensity')}") for sec in s.inner_secrets[-5:]], ft.Divider(), ft.Text("关系状态", weight=ft.FontWeight.BOLD), *[ft.Text(f"• {relationship_ui_summary(name, rel, s)}") for name, rel in list(s.relationships.items())[:6]], ft.Divider(), ft.Text("安全/前后辈", weight=ft.FontWeight.BOLD), ft.Text(f"出入许可：{s.safety.get('outing_permission')} / 宿舍安全：{s.safety.get('dorm_security')} / 边界风险：{s.safety.get('boundary_violation_risk')}"), ft.Text(f"敬语适应：{s.hierarchy.get('honorific_adaptation')} / 礼仪压力：{s.hierarchy.get('etiquette_pressure')} / 行业口碑：{s.hierarchy.get('industry_reputation')}"), ft.Divider(), ft.Text("状态效果", weight=ft.FontWeight.BOLD), *[ft.Text(f"• {k}: {v} 回合") for k, v in s.status_effects.items()], ft.Divider(), ft.Text("活跃危机", weight=ft.FontWeight.BOLD), *[ft.Text(f"• {c.title} / {c.stage} / heat={c.heat}") for c in s.active_crises if c.stage not in {'closed','converted'}], ft.Divider(), ft.Text("系统事件", weight=ft.FontWeight.BOLD), *[ft.Text(f"• {e.title} [{e.source_system}]") for e in s.system_events[-6:]], ft.Divider(), ft.Text("长期 Flag", weight=ft.FontWeight.BOLD), *[ft.Text(f"• {flag}") for flag in s.flags[-8:]], ft.Divider(), ft.Text("初始分配摘要", weight=ft.FontWeight.BOLD), *[ft.Text(f"• {line}") for line in s.initial_allocation_log[-6:]]])

    def refresh_choices(self) -> None:
        assert self.state is not None
        self.choice_row.controls.clear()
        buttons = []
        for choice in self.state.current_choices:
            if choice.id.upper() == "E":
                continue
            buttons.append(ft.ElevatedButton(f"{choice.id}. {choice.text}", on_click=lambda e, c=choice: self.submit_action(f"{c.id}. {c.text}")))
        self.choice_row.controls.extend([ft.Row(buttons, wrap=True, spacing=8), ft.Row([self.custom_input, ft.ElevatedButton("提交自定义行动", icon=icon("SEND"), on_click=self.submit_custom_action)], vertical_alignment=ft.CrossAxisAlignment.END)])

    def submit_custom_action(self, e) -> None:
        text = self.custom_input.value.strip()
        if not text:
            self.snack("请输入自定义行动。")
            return
        self.submit_action(f"E. {text}")

    def submit_action(self, action: str) -> None:
        if self.state is None or self.save_id is None:
            self.snack("没有可用存档。")
            return
        self.story_view.controls.append(ft.Divider())
        self.story_view.controls.append(ft.Text(f"你的选择：{action}", weight=ft.FontWeight.BOLD))
        self.story_view.controls.append(ft.Text(f"调用模式：DeepSeek API，策略：{self.config.model_policy}", color=ft.Colors.BLUE, weight=ft.FontWeight.BOLD))
        self.story_view.controls.append(ft.Text("正在生成下一回合……"))
        self.page.update()
        try:
            engine = TurnEngine(self.storage, self.config)
            state, response, applied, route_info, system_events, validation = engine.run_turn(self.save_id, self.state, action)
            self.state = state
            if validation.normalized_action != validation.original_action:
                self.story_view.controls.append(ft.Text("⚠ 行动已被阶段门控修正：", color=ft.Colors.ORANGE, weight=ft.FontWeight.BOLD))
                for w in validation.warnings:
                    self.story_view.controls.append(ft.Text(f"• {w}", color=ft.Colors.ORANGE))
                self.story_view.controls.append(ft.Text(f"实际执行：{validation.normalized_action}", color=ft.Colors.ORANGE))
            self.story_view.controls.append(ft.Text(f"✅ 本回合已调用 DeepSeek API。实际模型：{route_info.actual_model}；回合类型：{route_info.turn_kind}。", color=ft.Colors.GREEN))
            self.story_view.controls.append(ft.Text(f"路由原因：{route_info.reason}", color=ft.Colors.BLUE_GREY))
            if system_events:
                self.story_view.controls.append(ft.Text("Python 系统事件", weight=ft.FontWeight.BOLD))
                for ev in system_events:
                    color = ft.Colors.DEEP_ORANGE if ev.severity in {"warning", "crisis"} else ft.Colors.BLUE_GREY
                    self.story_view.controls.append(ft.Text(f"• {ev.title}：{ev.description}", color=color))
            self.story_view.controls.append(ft.Text(response.narrative, size=16))
            if response.npc_reactions:
                self.story_view.controls.append(ft.Text("NPC 反应", weight=ft.FontWeight.BOLD))
                for r in response.npc_reactions:
                    self.story_view.controls.append(ft.Text(f"{r.name}：{r.reaction}"))
            if applied:
                self.story_view.controls.append(ft.Text("属性变化", weight=ft.FontWeight.BOLD))
                for key, (old, new) in applied.items():
                    sign = "+" if new - old >= 0 else ""
                    self.story_view.controls.append(ft.Text(f"{key}: {old} → {new} ({sign}{new - old})"))
            self.refresh_panels()
            self.refresh_choices()
            self.custom_input.value = ""
            self.page.update()
        except ActionBlockedError as exc:
            self.story_view.controls.append(ft.Text("⛔ 行动被阻止，不消耗回合，也不会调用 DeepSeek。", color=ft.Colors.RED, weight=ft.FontWeight.BOLD))
            self.story_view.controls.append(ft.Text(exc.message, color=ft.Colors.RED))
            if exc.suggestions:
                self.story_view.controls.append(ft.Text("可改为：", weight=ft.FontWeight.BOLD))
                for s in exc.suggestions:
                    self.story_view.controls.append(ft.Text(f"• {s}"))
            self.page.update()
        except LLMError as exc:
            self.story_view.controls.append(ft.Text(f"LLM 错误：{exc}", color=ft.Colors.RED))
            self.page.update()
        except Exception as exc:
            logger.exception("submit_action failed")
            self.story_view.controls.append(ft.Text(f"程序错误：{exc}", color=ft.Colors.RED))
            self.page.update()

    def snack(self, message: str) -> None:
        self.page.snack_bar = ft.SnackBar(ft.Text(message))
        self.page.snack_bar.open = True
        self.page.update()


def main(page: ft.Page) -> None:
    KpopApp(page).run()


if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
