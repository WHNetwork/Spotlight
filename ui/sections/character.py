from __future__ import annotations

from ui.shared import *


class CharacterMixin:
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
                p = state.player
                for raw in [state.save_name, p.stage_name, p.name]:
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

        kr_surnames = ["Kim", "Park", "Choi", "Jung", "Kang", "Han", "Bae", "Yoon", "Shin", "Seo"]
        kr_given = ["Haeun", "Jiyoon", "Seoya", "Yujin", "Dahyun", "Serin", "Minseo", "Chaewon", "Soyeon", "Yerin"]

        jp_surnames = ["Hoshino", "Shiraishi", "Sakurai", "Hanazawa", "Tsukishima", "Morikawa", "Asakura", "Nanase"]
        jp_given = ["Haruka", "Rin", "Mio", "Yuka", "Chihiro", "Sara", "Yui", "Akari"]

        vn_surnames = ["Nguyen", "Tran", "Le", "Pham", "Hoang", "Phan", "Vu", "Dang", "Bui", "Do"]
        vn_given = ["Linh", "Mai Anh", "Thao", "Minh Chau", "Lan Anh", "Bao Han", "Quynh", "Nhu Y", "Tu Anh", "Khanh Linh"]

        th_given = ["Narin", "Kanya", "Arisa", "Mali", "Pimchanok", "Sirinya", "Anong", "Lalana", "Mayuree", "Praewa"]
        th_surnames = ["Chai", "Suwan", "Kittisak", "Wongsa", "Srisai", "Thanakorn", "Rattanakul", "Phanich"]

        ph_given = ["Mika", "Althea", "Sofia", "Andrea", "Bianca", "Ysabel", "Janelle", "Rhea", "Mariel", "Gabriela"]
        ph_surnames = ["Reyes", "Santos", "Cruz", "Garcia", "Mendoza", "Ramos", "Aquino", "Torres"]

        my_given = ["Aina", "Nurul", "Amira", "Siti", "Hana", "Nadia", "Farah", "Alyssa", "Mira", "Izzah"]
        my_surnames = ["Rahman", "Ismail", "Hassan", "Yusof", "Ibrahim", "Aziz", "Zainal", "Othman"]

        sg_given = ["Chloe", "Jia En", "Clarissa", "Mei Lin", "Alyssa", "Rachel", "Xin Yi", "Sabrina", "Nicole", "Joey"]
        sg_surnames = ["Tan", "Lim", "Lee", "Ng", "Ong", "Chua", "Koh", "Goh"]

        diaspora_given = ["Mia", "Lia", "Nina", "Iris", "Luna", "Sena", "Rina", "Ari", "Ena", "Yuna", "Sora", "Mina"]
        diaspora_surnames = ["Chen", "Lin", "Wang", "Zhang", "Liu", "Huang", "Xu", "Zhao", "Song", "Gu"]

        stage_roots = ["Luna", "Sera", "Yuna", "Mina", "Rina", "Aria", "Navi", "Sia", "Lia", "Nari", "Moa", "Ena", "Rhea", "Ivy", "Nell", "Sori"]
        stage_suffix = ["", "", "", "a", "i", "e", "n", "ly", "star", "one"]
        cn_stage = ["星禾", "浅月", "清梨", "知夏", "南音", "白露", "青栀", "月宁"]

        existing = self.existing_character_name_keys()

        def make_real_name() -> str:
            if any(x in text for x in ["韩国", "korea", "korean", "kr", "韩"]):
                return f"{random.choice(kr_given)} {random.choice(kr_surnames)}"
            if any(x in text for x in ["日本", "japan", "japanese", "jp", "日"]):
                return f"{random.choice(jp_given)} {random.choice(jp_surnames)}"
            if any(x in text for x in ["越南", "vietnam", "vietnamese", "vn"]):
                return f"{random.choice(vn_given)} {random.choice(vn_surnames)}"
            if any(x in text for x in ["泰国", "thai", "thailand", "th"]):
                return f"{random.choice(th_given)} {random.choice(th_surnames)}"
            if any(x in text for x in ["菲律宾", "philippines", "filipino", "ph"]):
                return f"{random.choice(ph_given)} {random.choice(ph_surnames)}"
            if any(x in text for x in ["马来西亚", "malaysia", "malaysian", "my"]):
                return f"{random.choice(my_given)} {random.choice(my_surnames)}"
            if any(x in text for x in ["新加坡", "singapore", "singaporean", "sg"]):
                return f"{random.choice(sg_given)} {random.choice(sg_surnames)}"
            if any(x in text for x in ["美国华裔", "加拿大华裔", "澳大利亚华裔", "华裔", "american", "canadian", "australian", "us"]):
                return f"{random.choice(diaspora_given)} {random.choice(diaspora_surnames)}"
            return random.choice(cn_surnames) + random.choice(cn_given)

        for _ in range(120):
            real = make_real_name()
            art = random.choice(stage_roots) + random.choice(stage_suffix)
            if ("中国" in text or text == "") and random.random() < 0.25:
                art = random.choice(cn_stage)
            if (
                self.normalize_character_name_key(real) not in existing
                and self.normalize_character_name_key(art) not in existing
                and self.normalize_character_name_key(real) != self.normalize_character_name_key(art)
            ):
                return {"艺名": art, "本名": real}

        stamp = random.randint(100, 999)
        return {"艺名": f"Stella{stamp}", "本名": f"Trainee {stamp}"}


    def character_create_bg(self):
        return ft.Container(
            left=0,
            top=0,
            right=0,
            bottom=0,
            bgcolor="#F8F6FC",
            image=ft.DecorationImage(
                src=asset("backgrounds/character_create_office_bg_v2.png"),
                fit="cover",
                opacity=0.94,
            ),
        )

    def character_form_field_style(self):
        return {
            "border_radius": 18,
            "border_color": ft.Colors.with_opacity(0.48, C["line"]),
            "focused_border_color": C["dai"],
            "bgcolor": ft.Colors.with_opacity(0.68, ft.Colors.WHITE),
            "content_padding": ft.Padding(left=14, right=14, top=10, bottom=10),
            "text_style": ft.TextStyle(font_family=FONT_CN, color=C["ink"], size=self.ui_size(13)),
            "label_style": ft.TextStyle(font_family=FONT_CN, color=C["sub"], size=self.ui_size(11)),
        }

    def dice_button(self, handler, tooltip: str = "随机生成"):
        return ft.Container(
            width=42,
            height=42,
            border_radius=18,
            bgcolor=ft.Colors.with_opacity(0.78, ft.Colors.WHITE),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.46, C["line"])),
            alignment=ft.Alignment.CENTER,
            ink=True,
            tooltip=tooltip,
            on_click=handler,
            content=icon_image("dice", 22, 0.94),
        )

    def random_character_field_value(self, field_name: str, nationality: str | None = None) -> str:
        text = str(nationality or "").strip().lower()
        pool = {
            "身高": ["158", "160", "162", "164", "166", "168", "170", "172"],
            "外貌特征": ["清冷幼态，镜头里有反差感", "淡颜系，笑起来很有亲和力", "五官干净，舞台妆后冲击力强", "眼神很亮，适合清新和梦幻概念", "骨相利落，适合高冷概念"],
            "性格": ["慢热但很能忍，熟悉后会变得很黏人", "外表安静，胜负欲很强", "敏感细腻，习惯先照顾别人情绪", "有点倔，压力越大越不愿服输", "社交谨慎，但对认可的人很真诚"],
            "爱好": ["拍天空、写短日记、听老歌", "整理手账、看舞台直拍、喝冰美式", "逛文具店、听 demo、夜跑", "看电影、练手势舞、收集香水小样", "做饭、拍胶片、拆解舞台编排"],
            "特长": ["记动作很快，能自己扒舞", "音色清亮，适合副歌和桥段", "节奏感好，rap 咬字干净", "镜头感强，ending 表情稳定", "共情力强，适合综艺和采访"],
            "弱项": ["体能储备不足，连续高强度训练容易崩", "韩语表达慢，临场采访会紧张", "低音区不稳，需要长期声乐训练", "太在意别人评价，容易内耗", "力量不足，大框架动作需要强化"],
            "家庭状况": ["普通家庭，支持有限但情感上愿意理解", "父母现实保守，对出道结果很焦虑", "家里经济压力不小，希望她尽快有结果", "母亲支持，父亲更看重学业稳定", "家庭沟通少，她习惯自己做决定"],
            "练习生经历": ["有舞社基础，但没有系统训练经历", "参加过校园演出，镜头经验很少", "通过线上选拔入社，基础不均衡", "曾短期参加培训班，基本功还在补", "做过伴舞替补，对舞台流程有概念"],
            "在团定位": ["主舞候补", "副主唱候补", "门面候补", "综艺反应位", "忙内线候补", "全能型练习生"],
            "你希望观众记住你的什么": ["她不是最亮的那一个，但每次都会再往前走一点", "看似安静，真正上台时会把人拉进她的情绪里", "她的努力不是口号，是每一天都能看见的变化", "她有一种干净又倔强的生命力", "她能把脆弱和野心同时放进舞台里"],
            "你不希望剧情触碰的内容": ["不写极端暴力和羞辱性情节", "不写过度黑暗的家庭创伤", "不写未成年露骨恋爱描写", "不写强制亲密关系", "不写不可逆的重大身体伤害"],
            "其他补充": ["希望整体路线偏成长流，慢热关系，重视舞台和日常细节。", "希望有友情、竞争和公司压力，但不要每回合都高强度危机。", "希望角色会犯错，也会逐渐学会保护自己。", "希望剧情里多出现练习室、宿舍、考核和舞台前准备。"],
        }
        if field_name == "国籍":
            return random.choice(["中国", "韩国", "日本", "泰国", "越南", "菲律宾", "马来西亚", "新加坡", "美国华裔", "加拿大华裔", "澳大利亚华裔"])
        if field_name == "年龄":
            return random.choice(["15", "16", "17", "18", "19", "20", "21"])
        return random.choice(pool.get(field_name, [""]))


    def mbti_options(self) -> list[str]:
        return [
            "INTJ", "INTP", "ENTJ", "ENTP",
            "INFJ", "INFP", "ENFJ", "ENFP",
            "ISTJ", "ISFJ", "ESTJ", "ESFJ",
            "ISTP", "ISFP", "ESTP", "ESFP",
        ]

    def random_mbti(self) -> str:
        return random.choice(self.mbti_options())

    def mbti_profile(self, mbti: str | None) -> Dict[str, Any]:
        """Narrative/control profile for MBTI.

        MBTI is treated as a game-writing control variable, not as a real psychological diagnosis.
        It gives the model stable reaction tendencies and gives the rules a small initial-stat bias.
        """
        code = str(mbti or "").upper().strip()
        if code not in self.mbti_options():
            code = "INFP"
        e, p, j, l = code[0], code[1], code[2], code[3]
        dimension = {
            "energy": "外向" if e == "E" else "内向",
            "information": "直觉" if p == "N" else "实感",
            "decision": "情感" if j == "F" else "思考",
            "lifestyle": "计划" if l == "J" else "即兴",
        }
        tendency = []
        tags = [f"MBTI:{code}", f"MBTI-{e}", f"MBTI-{p}", f"MBTI-{j}", f"MBTI-{l}"]

        if e == "E":
            tendency.append("更容易主动接触同期、老师和工作人员，综艺反应更外放，但也更容易被镜头和舆论放大。")
            tags += ["社交主动", "综艺潜力"]
        else:
            tendency.append("更倾向先观察再靠近，内心活动密度更高，关系升温慢但黏性强，压力更容易在沉默里累积。")
            tags += ["内向观察", "日记倾向"]
        if p == "N":
            tendency.append("更重视概念理解、舞台叙事和自我表达，适合创作、概念消化和复杂情绪线。")
            tags += ["概念理解", "创作兴趣"]
        else:
            tendency.append("更重视细节复现、训练秩序和身体执行，考核稳定性更强。")
            tags += ["训练纪律", "动作复现"]
        if j == "F":
            tendency.append("更容易共情队友、粉丝和家人，也更容易把冲突归因到自己身上。")
            tags += ["共情敏感", "团队亲和"]
        else:
            tendency.append("更习惯用理性拆解问题，边界感更清楚，关系表达较慢热。")
            tags += ["理性边界", "冲突直面"]
        if l == "J":
            tendency.append("更依赖计划、稳定日程和明确目标，公司信任更容易建立，但责任感压力更强。")
            tags += ["计划性", "责任压力"]
        else:
            tendency.append("更依赖现场反应和即兴调整，舞台灵活性强，但纪律和行程风险更高。")
            tags += ["即兴反应", "纪律波动"]
        return {
            "code": code,
            "dimension": dimension,
            "narrative_tendency": tendency,
            "stat_tags": tags,
            "prompt_rule": "MBTI只作为反应倾向与叙事稳定器，不允许把角色写成刻板人格模板；角色可以成长、矛盾、违背惯性。",
        }

    def infer_source_tags(self, character: Dict[str, Any]) -> list[str]:
        """Rule-based auto tag matching from player-selected identity source and visible fields.

        身份来源是玩家选择的“出身入口”；身份标签是系统根据身份来源、国籍、
        年龄、MBTI和AI生成内容自动匹配出的机制标签。标签会进入初始数值分配器。
        """
        tags: list[str] = []

        def add_tag(tag: str) -> None:
            tag = str(tag or "").strip()
            if tag and tag not in tags:
                tags.append(tag)

        joined = " ".join(str(v) for v in character.values() if v is not None)
        identity_source = str(character.get("身份") or character.get("身份来源") or "").strip()

        # 玩家选择的身份来源先转成确定性身份标签，不交给AI自由猜。
        identity_rules = {
            "素人学生被星探发现": ["素人发掘", "适应期新人", "镜头待开发"],
            "普通学生自投简历": ["普通练习生", "学业压力", "适应期新人"],
            "舞蹈学院学生": ["舞蹈基础", "校园演出经验", "训练适应快"],
            "海外练习生": ["海外练习生", "语言压力", "文化适应压力"],
            "童星转型": ["童星/模特", "表演基础", "镜头优势", "公众审视压力"],
            "选秀遗珠": ["选秀淘汰者", "舞台经验", "黑粉争议风险"],
            "地下舞者": ["舞蹈基础", "舞台经验", "纪律适应风险"],
            "网红转练习生": ["镜头优势", "综艺潜力", "既有流量", "黑粉争议风险"],
            "富裕家庭练习生": ["优渥家庭", "资源基础", "关系户争议风险"],
            "顶流亲属": ["顶流亲属", "既有流量", "公众审视压力", "关系户争议风险"],
            "前运动员转型": ["前运动员", "体能优势", "旧伤风险", "纪律基础"],
            "平面模特转型": ["童星/模特", "视觉优势", "镜头优势", "舞蹈短板"],
            "声乐特招生": ["声乐基础", "训练适应快", "舞蹈短板"],
            "RAP地下社群": ["RAP基础", "创作兴趣", "纪律适应风险"],
            "小公司再出道": ["再出道", "舞台经验", "职业倦怠风险", "公众审视压力"],
        }
        for tag in identity_rules.get(identity_source, []):
            add_tag(tag)

        age = None
        try:
            age = int(str(character.get("年龄") or "").strip())
        except Exception:
            pass

        mbti_profile = self.mbti_profile(character.get("MBTI"))
        for tag in mbti_profile.get("stat_tags", []):
            add_tag(tag)

        nationality = str(character.get("国籍") or "").strip()
        if nationality:
            if "韩国" in nationality:
                add_tag("本土练习生")
            elif any(x in nationality for x in ["中国", "日本", "泰国", "越南", "菲律宾", "马来西亚", "新加坡", "美国", "加拿大", "澳大利亚", "华裔"]):
                add_tag("海外练习生")
                if "韩国" not in nationality:
                    add_tag("语言压力")

        if age is not None:
            if age < 16:
                add_tag("低龄入社")
            elif age >= 20:
                add_tag("大龄练习生")
            else:
                add_tag("适龄练习生")

        keyword_rules = [
            ("舞", "舞蹈基础"),
            ("舞社", "舞蹈基础"),
            ("扒舞", "舞蹈基础"),
            ("声乐", "声乐基础"),
            ("音色", "声乐基础"),
            ("唱", "声乐基础"),
            ("rap", "RAP基础"),
            ("节奏", "RAP基础"),
            ("镜头", "镜头优势"),
            ("门面", "视觉优势"),
            ("外貌", "视觉优势"),
            ("模特", "视觉优势"),
            ("综艺", "综艺潜力"),
            ("采访", "综艺潜力"),
            ("校园", "校园演出经验"),
            ("线上选拔", "线上选拔入社"),
            ("家庭压力", "家庭压力"),
            ("经济压力", "家庭压力"),
            ("优渥", "优渥家庭"),
            ("富裕", "优渥家庭"),
            ("学业", "学业压力"),
            ("韩语", "语言压力"),
            ("内耗", "心理敏感"),
            ("敏感", "心理敏感"),
            ("体能", "体能短板"),
            ("运动员", "前运动员"),
            ("旧伤", "旧伤风险"),
            ("伤", "身体风险"),
        ]
        lower_joined = joined.lower()
        for key, tag in keyword_rules:
            if key.lower() in lower_joined:
                add_tag(tag)

        if not tags:
            tags = ["普通练习生", "待观察"]
        return tags[:12]

    def build_random_character_seed(self, fields: Dict[str, Any]) -> None:
        names = self.random_character_names(fields["国籍"].value)
        fields["艺名"].value = names["艺名"]
        fields["本名"].value = names["本名"]
        for key in ["国籍", "年龄", "身高", "外貌特征", "性格", "爱好", "特长", "弱项", "家庭状况", "练习生经历", "在团定位", "你希望观众记住你的什么", "你不希望剧情触碰的内容", "其他补充"]:
            if key in fields:
                fields[key].value = self.random_character_field_value(key, fields["国籍"].value)

    def validate_character_numeric_fields(self, character: Dict[str, Any]) -> list[str]:
        errors: list[str] = []
        raw_age = str(character.get("年龄") or "").strip()
        if raw_age:
            try:
                age = int(raw_age)
                if age < 10 or age > 30:
                    errors.append("年龄建议填写 10—30 之间的整数。")
            except Exception:
                errors.append("年龄必须是整数，例如 18。")

        raw_height = str(character.get("身高") or "").strip().replace("cm", "").replace("CM", "").replace("厘米", "")
        if raw_height:
            try:
                height = float(raw_height)
                if height < 130 or height > 190:
                    errors.append("身高建议填写 130—190 之间的数值，单位为 cm。")
                else:
                    character["身高"] = f"{int(height) if height.is_integer() else height}cm"
            except Exception:
                errors.append("身高必须是数值，例如 165，系统会自动补成 165cm。")
        return errors


    def character_select_dropdown(self, label: str, value: str, options: list[str], width: int = 320):
        return ft.Dropdown(
            label=label,
            value=value,
            width=width,
            options=[ft.dropdown.Option(x) for x in options],
            border_radius=18,
            border_color=ft.Colors.with_opacity(0.52, C["line"]),
            focused_border_color=C["dai"],
            bgcolor=ft.Colors.with_opacity(0.78, ft.Colors.WHITE),
            content_padding=ft.Padding(left=14, right=14, top=8, bottom=8),
            text_style=ft.TextStyle(font_family=FONT_CN, color=C["ink"], size=self.ui_size(13)),
            label_style=ft.TextStyle(font_family=FONT_CN, color=C["sub"], size=self.ui_size(11)),
        )

    def period_intro_button(self):
        return ft.Container(
            padding=ft.Padding(left=13, right=13, top=9, bottom=9),
            border_radius=20,
            bgcolor=ft.Colors.with_opacity(0.82, ft.Colors.WHITE),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.50, C["line"])),
            ink=True,
            on_click=lambda e: self.show_period_intro_dialog(),
            content=ft.Row([
                icon_image("period", 18, 0.92),
                ft.Text("生理周期系统介绍", size=self.ui_size(12), color=C["dai"], weight=ft.FontWeight.W_700, font_family=FONT_CN),
            ], spacing=7, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )

    def show_period_intro_dialog(self) -> None:
        intro_sections = [
            ("系统作用", "生理周期系统会让角色的身体状态、训练效率、睡眠、体重管理压力、情绪波动、伤病风险和关系事件产生联动。它不是单纯扣数值，而是把练习生的身体负担写进日常。"),
            ("游戏影响", "经前期可能出现睡眠下降、情绪敏感、体重管理压力上升；生理期前段会影响体力、肌肉恢复、训练效率和伤病风险。高强度训练、舞台服装、外出行程、是否向经纪人或队友说明，都会影响后续事件。"),
            ("关闭", "不计算周期，不触发相关事件。适合完全不想让身体系统进入剧情的玩家。"),
            ("简化", "保留核心影响：体力、睡眠、训练效率、伤病风险、少量状态提醒。适合想要沉浸感，但不希望系统过细的玩家。"),
            ("极致", "在简化基础上加入更细的沉浸事件：用品准备、服装焦虑、是否求助、是否向管理层说明、长期压力导致周期不规律、队友照顾和边界变化等。"),
            ("建议", "建议开启。它能让角色不再只是数值面板，而是一个有身体、有边界、有日常负担的人，沉浸感会更强。"),
        ]

        section_controls = []
        for title, body in intro_sections:
            section_controls.append(
                ft.Container(
                    padding=ft.Padding(left=18, right=18, top=14, bottom=14),
                    border_radius=22,
                    bgcolor=ft.Colors.with_opacity(0.68, ft.Colors.WHITE),
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.48, C["line"])),
                    content=ft.Column([
                        ft.Text(title, size=self.ui_size(15), weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN),
                        ft.Text(body, size=self.ui_size(13), color=C["sub"], font_family=FONT_CN, selectable=True),
                    ], spacing=5),
                )
            )

        try:
            vw = int(self.page.width or 1500)
            vh = int(self.page.height or 900)
        except Exception:
            vw, vh = 1500, 900

        # 跟随窗口大小：宽高按当前窗口比例计算，并设置上下限。
        dialog_w = max(720, min(1180, int(vw * 0.82)))
        dialog_h = max(520, min(760, int(vh * 0.82)))

        close_button = ft.Container(
            padding=ft.Padding(left=16, right=16, top=9, bottom=9),
            border_radius=20,
            bgcolor=ft.Colors.with_opacity(0.86, C["jade"]),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.55, C["line"])),
            ink=True,
            on_click=lambda e: self.close_dialog(),
            content=ft.Text("知道了", size=self.ui_size(12), color=C["ink"], font_family=FONT_CN, weight=ft.FontWeight.W_700),
        )

        dialog = ft.AlertDialog(
            modal=True,
            content_padding=0,
            title_padding=0,
            actions_padding=0,
            content=ft.Container(
                width=dialog_w,
                height=dialog_h,
                border_radius=34,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                content=ft.Stack([
                    ft.Container(
                        left=0,
                        top=0,
                        right=0,
                        bottom=0,
                        image=ft.DecorationImage(
                            src=asset("backgrounds/period_help_dorm_bg.png"),
                            fit="cover",
                            opacity=0.94,
                        ),
                    ),
                    ft.Container(
                        left=0,
                        top=0,
                        right=0,
                        bottom=0,
                        bgcolor=ft.Colors.with_opacity(0.28, ft.Colors.WHITE),
                    ),
                    ft.Container(
                        left=30,
                        top=28,
                        right=30,
                        bottom=28,
                        padding=22,
                        border_radius=30,
                        bgcolor=ft.Colors.with_opacity(0.76, ft.Colors.WHITE),
                        border=ft.Border.all(1, ft.Colors.with_opacity(0.66, ft.Colors.WHITE)),
                        shadow=ft.BoxShadow(
                            blur_radius=30,
                            color=ft.Colors.with_opacity(0.12, C["dai"]),
                            offset=ft.Offset(0, 10),
                        ),
                        content=ft.Column([
                            ft.Row([
                                ft.Container(icon_image("period", 28, 0.94), width=46, height=46, border_radius=23, bgcolor=ft.Colors.with_opacity(0.34, C["lotus"]), alignment=ft.Alignment.CENTER),
                                ft.Column([
                                    ft.Text("生理周期系统介绍", size=self.ui_size(24), weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN),
                                    ft.Text("身体状态、训练效率、关系事件和沉浸日常的联动说明", size=self.ui_size(12), color=C["sub"], font_family=FONT_CN),
                                ], spacing=1, expand=True),
                                close_button,
                            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            ft.Divider(height=18, color=ft.Colors.with_opacity(0.35, C["line"])),
                            ft.Column(section_controls, spacing=12, scroll=ft.ScrollMode.AUTO, expand=True),
                        ], spacing=10, expand=True),
                    ),
                ]),
            ),
        )
        try:
            self.page.dialog = dialog
            dialog.open = True
        except Exception:
            pass
        try:
            if dialog not in self.page.overlay:
                self.page.overlay.append(dialog)
            dialog.open = True
        except Exception:
            pass
        self.page.update()


    def close_dialog(self) -> None:
        try:
            if self.page.dialog:
                self.page.dialog.open = False
        except Exception:
            pass
        try:
            for item in self.page.overlay:
                if isinstance(item, ft.AlertDialog):
                    item.open = False
        except Exception:
            pass
        self.page.update()

    def parse_json_object_from_text(self, raw: str) -> Dict[str, Any]:
        text = str(raw or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text).strip()
            text = re.sub(r"```$", "", text).strip()
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else {}
        except Exception:
            pass
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            data = json.loads(text[start:end + 1])
            return data if isinstance(data, dict) else {}
        return {}

    def normalize_ai_character_match(self, payload: Dict[str, Any], basic: Dict[str, Any]) -> Dict[str, Any]:
        allowed_fields = [
            "外貌风格", "性格", "爱好", "特长", "弱项", "家庭状况", "练习生经历",
            "在团定位", "你希望观众记住你的什么", "其他补充",
        ]
        result: Dict[str, Any] = {}
        for key in allowed_fields:
            value = payload.get(key, "")
            if isinstance(value, (list, tuple)):
                value = "、".join(str(x) for x in value if str(x).strip())
            result[key] = str(value or "").strip()[:380]

        tags = payload.get("出身来源标签", [])
        if isinstance(tags, str):
            tags = [x.strip() for x in re.split(r"[,，、/\\n]", tags) if x.strip()]
        elif isinstance(tags, list):
            tags = [str(x).strip() for x in tags if str(x).strip()]
        else:
            tags = []
        if not tags:
            temp = dict(basic)
            temp.update(result)
            tags = self.infer_source_tags(temp)
        result["出身来源标签"] = tags[:8]

        # This field is shown only in UI/status and saved into character data.
        notes = payload.get("基础数值倾向", [])
        if isinstance(notes, str):
            notes = [x.strip() for x in re.split(r"[,，、/\\n]", notes) if x.strip()]
        elif isinstance(notes, list):
            notes = [str(x).strip() for x in notes if str(x).strip()]
        else:
            notes = []
        result["基础数值倾向"] = notes[:8]
        return result

    def fallback_ai_character_match(self, basic: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback used when model call fails; still keeps MBTI/tag/stat logic working."""
        identity = str(basic.get("身份") or "")
        nationality = str(basic.get("国籍") or "")
        age = str(basic.get("年龄") or "")
        height = str(basic.get("身高") or "")
        mbti = str(basic.get("MBTI") or "INFP").upper()
        art_name = str(basic.get("艺名") or basic.get("本名") or "她")
        overseas = nationality and "韩国" not in nationality
        profile = self.mbti_profile(mbti)
        tendency = "；".join(profile.get("narrative_tendency", []))
        base = {
            "外貌风格": f"{art_name}适合清透梦幻系视觉，镜头里偏干净、轻盈；身高{height or '未知'}，适合根据舞台概念强化线条感。",
            "性格": f"MBTI为{mbti}。{tendency} 她不是人格测试标签本身，而是在练习室压力下逐渐显露这些反应倾向。",
            "爱好": "听 demo、整理练习笔记、看舞台直拍、拍天空和练习室角落。",
            "特长": "舞蹈基础和镜头学习能力较好，能快速记住动作重点。",
            "弱项": "体能储备和语言表达仍需训练，连续高压时容易内耗。",
            "家庭状况": "家庭支持存在但不稳定，家人既期待她成功，也担心这条路太不确定。",
            "练习生经历": f"{identity}入社，基础不均衡，但可塑性强。",
            "在团定位": "主舞候补 / 清冷视觉线 / 成长型全能练习生",
            "你希望观众记住你的什么": "希望观众记住她不是天生闪耀，而是在每一次训练里慢慢把自己磨亮。",
            "其他补充": "路线偏成长流，重视练习室、宿舍、考核、友情、竞争和公司压力。",
            "出身来源标签": ["海外练习生" if overseas else "普通练习生", "适龄练习生", "舞蹈基础", "镜头优势", "体能短板", *profile.get("stat_tags", [])],
            "基础数值倾向": ["舞蹈实力略高", "舞台感染力略高", "体力偏低", "精神压力略高", f"MBTI:{mbti}影响叙事反应和关系节奏"],
        }
        if age:
            try:
                age_i = int(re.search(r"\d+", age).group())
                if age_i < 16:
                    base["出身来源标签"].append("低龄入社")
                elif age_i >= 20:
                    base["出身来源标签"].append("大龄练习生")
            except Exception:
                pass
        # 去重
        seen = []
        for t in base["出身来源标签"]:
            if t and t not in seen:
                seen.append(t)
        base["出身来源标签"] = seen[:10]
        return base

    def generate_character_match_with_llm(self, basic: Dict[str, Any]) -> Dict[str, Any]:
        system = (
            "你是KPOP女团练习生叙事模拟器的角色设定生成器。"
            "你要根据玩家已经填写的基础信息，尤其是MBTI，自动匹配角色的外貌风格、性格、家庭背景、练习生经历、定位、优势短板和出身来源标签。"
            "MBTI在这里是叙事控制变量，不是真实心理诊断；它只能影响反应倾向、关系节奏和压力表达，不能把角色写成刻板模板。"
            "要求：1. 必须严格输出JSON对象；2. 不要Markdown；3. 不要解释；4. 内容要现实，符合KPOP练习生生态；"
            "5. 不要写露骨性内容；6. 身份来源由玩家选择，不能改写；7. 身份标签/出身来源标签必须依据身份来源、国籍、年龄、MBTI和基础信息推断，标签会影响初始数值。"
        )
        user = {
            "基础信息": basic,
            "MBTI叙事倾向": self.mbti_profile(basic.get("MBTI")),
            "必须输出字段": [
                "外貌风格", "性格", "爱好", "特长", "弱项", "家庭状况", "练习生经历",
                "在团定位", "你希望观众记住你的什么", "其他补充",
                "出身来源标签", "基础数值倾向",
            ],
            "标签候选": [
                "素人发掘", "普通练习生", "适应期新人", "海外练习生", "本土练习生",
                "低龄入社", "适龄练习生", "大龄练习生",
                "舞蹈基础", "声乐基础", "RAP基础", "表演基础", "创作兴趣",
                "镜头优势", "视觉优势", "综艺潜力", "语言压力", "家庭压力", "文化适应压力",
                "体能短板", "心理敏感", "校园演出经验", "线上选拔入社", "选秀淘汰者",
                "童星/模特", "优渥家庭", "顶流亲属", "前运动员", "再出道",
                "旧伤风险", "既有流量", "黑粉争议风险", "关系户争议风险", "公众审视压力",
            ],
            "数值影响说明": "出身来源标签会影响初始职业属性、身体状态、心理压力、粉丝与市场倾向。",
        }
        provider = get_llm_provider(self.config)
        raw = provider.generate(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
            model=self.config.model_for_tier("flash"),
        )
        payload = self.parse_json_object_from_text(raw)
        if not payload:
            raise LLMError("角色匹配模型没有返回可解析JSON。")
        return self.normalize_ai_character_match(payload, basic)


    def generated_result_field_card(self, title: str, field: ft.TextField, icon_name: str = "stage", width: int = 430, lines: int = 4):
        field.width = width - 34
        field.multiline = True
        field.min_lines = lines
        field.max_lines = lines
        field.border_radius = 16
        field.bgcolor = ft.Colors.with_opacity(0.72, ft.Colors.WHITE)
        field.border_color = ft.Colors.with_opacity(0.44, C["line"])
        field.focused_border_color = C["dai"]
        field.content_padding = ft.Padding(left=12, right=12, top=10, bottom=10)
        field.text_style = ft.TextStyle(font_family=FONT_CN, color=C["ink"], size=self.ui_size(12))
        field.label = ""
        return ft.Container(
            width=width,
            padding=14,
            border_radius=24,
            bgcolor=ft.Colors.with_opacity(0.58, ft.Colors.WHITE),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.52, C["line"])),
            content=ft.Column([
                ft.Row([
                    ft.Container(icon_image(icon_name, 17, 0.88), width=26, height=26, border_radius=13, bgcolor=ft.Colors.with_opacity(0.26, C["lotus"]), alignment=ft.Alignment.CENTER),
                    ft.Text(title, size=self.ui_size(13), weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN),
                ], spacing=7, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                field,
            ], spacing=8),
        )

    def generated_result_row(self, cards: list):
        return ft.Row(cards, spacing=14, wrap=True, alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.START)

    def show_character_create(self) -> None:
        self.clear()
        self.page.padding = 0
        self.page.bgcolor = ft.Colors.WHITE

        # 不再使用 Flet 原生 Dropdown：原生下拉菜单由系统控件绘制，弹层无法稳定美化。
        # 这里改成自绘选择器：点击输入框弹出玻璃风格选项面板。
        select_options: Dict[str, list[str]] = {
            "identity": [
                "素人学生被星探发现",
                "普通学生自投简历",
                "舞蹈学院学生",
                "海外练习生",
                "童星转型",
                "选秀遗珠",
                "地下舞者",
                "网红转练习生",
                "富裕家庭练习生",
                "顶流亲属",
                "前运动员转型",
                "平面模特转型",
                "声乐特招生",
                "RAP地下社群",
                "小公司再出道",
            ],
            "company_size": ["大型公司", "中型公司", "小型公司"],
            "timeline": ["练习生阶段", "出道准备期", "已出道新人"],
            "nationality": ["中国", "韩国", "日本", "泰国", "美国华裔", "加拿大华裔", "澳大利亚华裔", "新加坡", "越南", "菲律宾", "马来西亚"],
            "mbti": ["INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP", "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP"],
            "period": ["关闭", "简化", "极致"],
        }
        select_values: Dict[str, str] = {
            "identity": "素人学生被星探发现",
            "company_size": "中型公司",
            "timeline": "练习生阶段",
            "nationality": "中国",
            "mbti": "INFP",
            "period": "简化",
        }
        select_labels: Dict[str, str] = {
            "identity": "身份来源",
            "company_size": "公司规模",
            "timeline": "时间线",
            "nationality": "国籍",
            "mbti": "MBTI",
            "period": "生理周期系统",
        }
        select_displays: Dict[str, ft.Text] = {}

        def close_selector_dialog():
            try:
                if self.page.dialog:
                    self.page.dialog.open = False
            except Exception:
                pass
            try:
                for item in self.page.overlay:
                    if isinstance(item, ft.AlertDialog):
                        item.open = False
            except Exception:
                pass
            self.page.update()

        def open_selector_dialog(key: str):
            def choose(option: str):
                def handler(e=None):
                    select_values[key] = option
                    if key in select_displays:
                        select_displays[key].value = option
                    close_selector_dialog()
                    mark_basic_changed()
                return handler

            option_controls = []
            for option in select_options[key]:
                active = option == select_values[key]
                option_controls.append(
                    ft.Container(
                        padding=ft.Padding(left=16, right=16, top=12, bottom=12),
                        border_radius=18,
                        bgcolor=ft.Colors.with_opacity(0.72 if active else 0.52, C["jade"] if active else ft.Colors.WHITE),
                        border=ft.Border.all(1, ft.Colors.with_opacity(0.48, C["jade"] if active else C["line"])),
                        ink=True,
                        on_click=choose(option),
                        content=ft.Row([
                            ft.Text(option, size=self.ui_size(13), color=C["ink"], weight=ft.FontWeight.W_700 if active else ft.FontWeight.W_500, font_family=FONT_CN, expand=True),
                            ft.Text("✓" if active else "", size=self.ui_size(13), color=C["dai"], font_family=FONT_CN),
                        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    )
                )

            dialog = ft.AlertDialog(
                modal=True,
                content_padding=0,
                title_padding=0,
                actions_padding=0,
                content=ft.Container(
                    width=420,
                    height=620,
                    padding=20,
                    border_radius=30,
                    bgcolor=ft.Colors.with_opacity(0.88, ft.Colors.WHITE),
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.68, ft.Colors.WHITE)),
                    shadow=ft.BoxShadow(blur_radius=30, color=ft.Colors.with_opacity(0.14, C["dai"]), offset=ft.Offset(0, 10)),
                    content=ft.Column([
                        ft.Row([
                            ft.Container(icon_image("new_character", 22, 0.92), width=34, height=34, border_radius=17, bgcolor=ft.Colors.with_opacity(0.28, C["lotus"]), alignment=ft.Alignment.CENTER),
                            ft.Column([
                                ft.Text(select_labels[key], size=self.ui_size(17), color=C["ink"], weight=ft.FontWeight.W_700, font_family=FONT_CN),
                                ft.Text("选择一个选项，系统会自动刷新基础档案状态。", size=self.ui_size(11), color=C["sub"], font_family=FONT_CN),
                            ], spacing=0, expand=True),
                            ft.Container(
                                padding=ft.Padding(left=10, right=10, top=7, bottom=7),
                                border_radius=16,
                                bgcolor=ft.Colors.with_opacity(0.70, ft.Colors.WHITE),
                                border=ft.Border.all(1, ft.Colors.with_opacity(0.42, C["line"])),
                                ink=True,
                                on_click=lambda e: close_selector_dialog(),
                                content=ft.Text("关闭", size=self.ui_size(11), color=C["dai"], font_family=FONT_CN, weight=ft.FontWeight.W_700),
                            ),
                        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Divider(height=16, color=ft.Colors.with_opacity(0.34, C["line"])),
                        ft.Column(option_controls, spacing=8, scroll=ft.ScrollMode.AUTO, expand=True),
                    ], spacing=8, expand=True),
                ),
            )
            try:
                self.page.dialog = dialog
                dialog.open = True
            except Exception:
                pass
            try:
                if dialog not in self.page.overlay:
                    self.page.overlay.append(dialog)
                dialog.open = True
            except Exception:
                pass
            self.page.update()

        def make_selector(key: str, width: int):
            display = ft.Text(select_values[key], size=self.ui_size(13), color=C["ink"], font_family=FONT_CN, weight=ft.FontWeight.W_600, max_lines=1)
            select_displays[key] = display
            return ft.Container(
                width=width,
                height=54,
                padding=ft.Padding(left=14, right=13, top=7, bottom=6),
                border_radius=18,
                bgcolor=ft.Colors.with_opacity(0.78, ft.Colors.WHITE),
                border=ft.Border.all(1, ft.Colors.with_opacity(0.52, C["line"])),
                ink=True,
                on_click=lambda e: open_selector_dialog(key),
                content=ft.Column([
                    ft.Text(select_labels[key], size=self.ui_size(10), color=C["sub"], font_family=FONT_CN),
                    ft.Row([
                        display,
                        ft.Container(expand=True),
                        ft.Text("⌄", size=self.ui_size(14), color=C["dai"], font_family=FONT_CN),
                    ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ], spacing=0),
            )

        identity = make_selector("identity", 330)
        company_size = make_selector("company_size", 220)
        timeline = make_selector("timeline", 300)
        nationality = make_selector("nationality", 260)
        mbti = make_selector("mbti", 220)
        period_mode = make_selector("period", 220)

        manual_field_names = ["艺名", "本名", "年龄", "身高"]
        ai_field_names = [
            "外貌风格", "性格", "爱好", "特长", "弱项", "家庭状况", "练习生经历",
            "在团定位", "你希望观众记住你的什么", "其他补充",
        ]

        fields: Dict[str, ft.TextField] = {}
        for name in manual_field_names + ai_field_names:
            label = "身高（cm）" if name == "身高" else name
            multiline = name in {"外貌风格", "性格", "家庭状况", "练习生经历", "你希望观众记住你的什么", "其他补充"}
            fields[name] = ft.TextField(
                label=label,
                width=330,
                multiline=multiline,
                min_lines=1,
                max_lines=3 if multiline else 1,
                **self.character_form_field_style(),
            )

        boundary_field = ft.TextField(
            label="",
            width=640,
            multiline=True,
            min_lines=4,
            max_lines=4,
            hint_text="这里由玩家自己填写，例如：不写极端暴力、强制亲密、未成年露骨恋爱、不可逆重大身体伤害等。",
            **self.character_form_field_style(),
        )
        boundary_field.disabled = True

        source_tags_cache: Dict[str, Any] = {"tags": [], "notes": []}
        generation_state: Dict[str, Any] = {"ready": False, "generating": False}
        status = ft.Text("", color=C["dai"], size=self.ui_size(12), font_family=FONT_CN, selectable=True)

        result_hint = ft.Text(
            "先填写基础档案，点击“确认基础档案并生成角色”。系统会在后台做重名校验，然后自动调用模型生成外貌风格、性格背景、标签和基础数值倾向。",
            size=self.ui_size(12),
            color=C["sub"],
            font_family=FONT_CN,
            selectable=True,
        )
        result_progress = ft.ProgressRing(width=28, height=28, stroke_width=3, visible=False)

        def set_ai_fields_disabled(disabled: bool):
            for key in ai_field_names:
                fields[key].disabled = disabled

        set_ai_fields_disabled(True)

        def clear_ai_cache():
            source_tags_cache["tags"] = []
            source_tags_cache["notes"] = []
            generation_state["ready"] = False
            for key in ai_field_names:
                fields[key].value = ""
                fields[key].disabled = True
            boundary_field.value = ""
            boundary_field.disabled = True
            hide_generated_result_containers()
            result_hint.value = "基础档案已变化。请重新点击“确认基础档案并生成角色”。"
            result_hint.color = C["sub"]

        def collect_basic() -> Dict[str, Any]:
            data: Dict[str, Any] = {
                "身份": select_values["identity"],
                "公司规模": select_values["company_size"],
                "时间线": select_values["timeline"],
                "国籍": select_values["nationality"],
                "MBTI": select_values["mbti"],
                "MBTI人格倾向": self.mbti_profile(select_values["mbti"]),
                "生理周期系统": select_values["period"],
            }
            for k in manual_field_names:
                data[k] = fields[k].value or ""
            return data

        def collect_full_character() -> Dict[str, Any]:
            data = collect_basic()
            for k in ai_field_names:
                data[k] = fields[k].value or ""
            data["你不希望剧情触碰的内容"] = boundary_field.value or ""

            deterministic_tags = self.infer_source_tags(data)
            merged_tags = []
            for tag in deterministic_tags + list(source_tags_cache.get("tags") or []):
                tag = str(tag).strip()
                if tag and tag not in merged_tags:
                    merged_tags.append(tag)
            data["出身来源标签"] = merged_tags[:12]

            if source_tags_cache["notes"]:
                data["基础数值倾向"] = list(source_tags_cache["notes"])
            return data

        def mark_basic_changed(e=None):
            clear_ai_cache()
            status.color = C["dai"]
            status.value = "基础档案已更新，需要重新生成AI匹配结果。"
            self.page.update()

        def randomize_names(e=None):
            names = self.random_character_names(select_values["nationality"])
            fields["艺名"].value = names["艺名"]
            fields["本名"].value = names["本名"]
            mark_basic_changed()

        def randomize_mbti(e=None):
            import random
            select_values["mbti"] = random.choice(select_options["mbti"])
            select_displays["mbti"].value = select_values["mbti"]
            mark_basic_changed()

        def randomize_manual_field(key: str):
            def handler(e=None):
                if key in {"艺名", "本名"}:
                    randomize_names(e)
                else:
                    fields[key].value = self.random_character_field_value(key, select_values["nationality"])
                    mark_basic_changed()
            return handler

        def randomize_basic(e=None):
            import random
            select_values["nationality"] = self.random_character_field_value("国籍", select_values["nationality"])
            select_displays["nationality"].value = select_values["nationality"]
            names = self.random_character_names(select_values["nationality"])
            fields["艺名"].value = names["艺名"]
            fields["本名"].value = names["本名"]
            fields["年龄"].value = self.random_character_field_value("年龄", select_values["nationality"])
            fields["身高"].value = self.random_character_field_value("身高", select_values["nationality"])
            select_values["mbti"] = random.choice(select_options["mbti"])
            select_displays["mbti"].value = select_values["mbti"]
            clear_ai_cache()
            status.color = C["jade"]
            status.value = "已随机生成基础档案。点击“确认基础档案并生成角色”后，系统会自动生成AI匹配结果。"
            self.page.update()

        def apply_ai_match(match: Dict[str, Any]):
            for key in ai_field_names:
                if key in fields:
                    fields[key].disabled = False
                    fields[key].value = str(match.get(key) or "")
            boundary_field.disabled = False
            show_generated_result_containers()
            ai_tags = list(match.get("出身来源标签") or [])
            base_tags = self.infer_source_tags(collect_basic())
            merged_tags = []
            for tag in base_tags + ai_tags:
                tag = str(tag).strip()
                if tag and tag not in merged_tags:
                    merged_tags.append(tag)
            source_tags_cache["tags"] = merged_tags[:12]
            source_tags_cache["notes"] = list(match.get("基础数值倾向") or [])
            generation_state["ready"] = True
            generation_state["generating"] = False
            result_progress.visible = False
            tags = "、".join(source_tags_cache["tags"]) or "待创建时自动推断"
            notes = "、".join(source_tags_cache["notes"]) or "由标签进入初始分配器"
            result_hint.color = C["jade"]
            result_hint.value = f"AI生成完成。觉得不合理可以直接微调下面的文本框；剧情边界需要玩家自己填写，AI不会替你决定不能触碰什么。\n自动标签：{tags}\n基础数值倾向：{notes}"
            status.color = C["jade"]
            status.value = "角色设定已生成，可以微调后创建角色。"
            self.page.update()

        def confirm_basic_and_generate(e=None):
            if generation_state.get("generating"):
                return

            basic = collect_basic()
            field_errors = self.validate_character_numeric_fields(dict(basic))
            duplicate_errors = self.validate_character_name_unique(basic)
            if field_errors or duplicate_errors:
                status.color = ft.Colors.RED
                status.value = "基础档案未通过校验：\n" + "\n".join(f"• {x}" for x in field_errors + duplicate_errors)
                result_hint.color = ft.Colors.RED
                result_hint.value = "请先修正基础档案。重名、年龄、身高校验会在后台自动完成，不需要单独点击校验按钮。"
                self.page.update()
                return

            generation_state["generating"] = True
            generation_state["ready"] = False
            result_progress.visible = True
            set_ai_fields_disabled(True)
            hide_generated_result_containers()
            result_hint.color = C["dai"]
            result_hint.value = "正在生成角色中……系统正在根据基础档案、MBTI、国籍、年龄和身高匹配外貌风格、性格背景、标签与基础数值倾向。"
            status.color = C["dai"]
            status.value = "生成角色中，请稍等。"
            self.page.update()

            def worker():
                try:
                    match = self.generate_character_match_with_llm(basic)
                except Exception as exc:
                    logger.exception("AI character matching failed")
                    match = self.fallback_ai_character_match(basic)
                    match["其他补充"] = (match.get("其他补充", "") + f"\n模型匹配失败，已使用本地规则兜底：{exc}")[:380]
                apply_ai_match(match)

            threading.Thread(target=worker, daemon=True).start()

        def create(e):
            if generation_state.get("generating"):
                status.color = C["dai"]
                status.value = "正在生成角色中，请等待生成完成。"
                self.page.update()
                return
            if not generation_state.get("ready"):
                status.color = ft.Colors.RED
                status.value = "请先点击“确认基础档案并生成角色”。AI生成完成后，创建角色按钮才会开放。"
                self.page.update()
                return

            raw_character = collect_full_character()
            raw_character["艺名"] = str(raw_character.get("艺名") or "").strip()
            raw_character["本名"] = str(raw_character.get("本名") or "").strip()
            raw_character["国籍"] = str(raw_character.get("国籍") or "").strip()

            field_errors = self.validate_character_numeric_fields(raw_character)
            duplicate_errors = self.validate_character_name_unique(raw_character)
            if not raw_character.get("出身来源标签"):
                raw_character["出身来源标签"] = self.infer_source_tags(raw_character)

            if field_errors or duplicate_errors:
                status.color = ft.Colors.RED
                status.value = "角色创建信息有误：\n" + "\n".join(f"• {x}" for x in field_errors + duplicate_errors)
                self.page.update()
                return

            try:
                normalized = validate_character_input(raw_character)
            except CharacterValidationError as exc:
                status.color = ft.Colors.RED
                status.value = "角色创建信息有误：\n" + "\n".join(f"• {e}" for e in exc.errors)
                self.page.update()
                return

            if str(raw_character.get("身高") or "").strip():
                normalized.data["身高"] = raw_character["身高"]

            normalized.data["avatar"] = self.random_avatar_path()
            normalized.data["出身来源标签"] = raw_character.get("出身来源标签", [])
            normalized.data["基础数值倾向"] = raw_character.get("基础数值倾向", [])
            normalized.data["MBTI"] = raw_character.get("MBTI")
            normalized.data["MBTI人格倾向"] = raw_character.get("MBTI人格倾向")

            from core.initial_allocator import allocate_initial_state
            state = GameState()
            allocate_initial_state(state, normalized.data)
            self.save_id = self.storage.create_save(state)
            self.state = state
            self.show_game(initial=True)

        def manual_field_row(name: str):
            return ft.Row([
                fields[name],
                self.dice_button(randomize_manual_field(name), f"随机生成{name}"),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        def generated_card(name: str, icon_name: str = "stage", width: int = 430, lines: int = 4):
            return self.generated_result_field_card(name, fields[name], icon_name=icon_name, width=width, lines=lines)

        boundary_container = self.generated_result_field_card(
            "剧情边界（你不希望触碰的内容）",
            boundary_field,
            icon_name="safety",
            width=640,
            lines=4,
        )
        boundary_container.visible = False

        generated_result_containers: list = []

        def hide_generated_result_containers():
            for item in generated_result_containers:
                try:
                    item.visible = False
                except Exception:
                    pass
            boundary_container.visible = False
            try:
                create_button_row.visible = False
            except Exception:
                pass

        def show_generated_result_containers():
            for item in generated_result_containers:
                try:
                    item.visible = True
                except Exception:
                    pass
            boundary_container.visible = True
            try:
                create_button_row.visible = True
            except Exception:
                pass

        def input_type_chip(text: str, color: str):
            return ft.Container(
                padding=ft.Padding(left=10, right=10, top=5, bottom=5),
                border_radius=16,
                bgcolor=ft.Colors.with_opacity(0.30, color),
                content=ft.Text(text, size=self.ui_size(10), color=C["ink"], font_family=FONT_CN, weight=ft.FontWeight.W_600),
            )

        def section_card(title: str, subtitle: str, icon_name: str, controls: list, expand: bool = True):
            return ft.Container(
                expand=expand,
                padding=20,
                border_radius=28,
                bgcolor=ft.Colors.with_opacity(0.82, ft.Colors.WHITE),
                border=ft.Border.all(1, ft.Colors.with_opacity(0.70, ft.Colors.WHITE)),
                shadow=ft.BoxShadow(blur_radius=26, color=ft.Colors.with_opacity(0.10, C["dai"]), offset=ft.Offset(0, 9)),
                content=ft.Column([
                    ft.Row([
                        ft.Container(icon_image(icon_name, 24, 0.92), width=38, height=38, border_radius=19, bgcolor=ft.Colors.with_opacity(0.34, C["lotus"]), alignment=ft.Alignment.CENTER),
                        ft.Column([
                            ft.Text(title, size=self.ui_size(17), weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN),
                            ft.Text(subtitle, size=self.ui_size(11), color=C["sub"], font_family=FONT_CN),
                        ], spacing=1, expand=True),
                    ], spacing=10),
                    *controls,
                ], spacing=12),
            )

        action_bar = ft.Container(
            width=360,
            padding=ft.Padding(left=16, right=16, top=16, bottom=16),
            border_radius=26,
            bgcolor=ft.Colors.with_opacity(0.58, ft.Colors.WHITE),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.44, C["line"])),
            shadow=ft.BoxShadow(
                blur_radius=18,
                spread_radius=0,
                color=ft.Colors.with_opacity(0.08, C["dai"]),
                offset=ft.Offset(0, 6),
            ),
            content=ft.Column([
                ft.Text(
                    "基础档案确认",
                    size=self.ui_size(13),
                    color=C["ink"],
                    weight=ft.FontWeight.W_700,
                    font_family=FONT_CN,
                ),
                ft.Text(
                    "系统会自动校验重名、年龄和身高；通过后生成AI设定。",
                    size=self.ui_size(11),
                    color=C["sub"],
                    font_family=FONT_CN,
                ),
                ft.Row([
                    ft.Container(
                        expand=True,
                        padding=ft.Padding(left=14, right=14, top=10, bottom=10),
                        border_radius=20,
                        bgcolor=ft.Colors.with_opacity(0.84, C["lotus"]),
                        ink=True,
                        on_click=randomize_basic,
                        content=ft.Row([icon_image("dice", 18), ft.Text("随机", size=self.ui_size(12), color=C["ink"], weight=ft.FontWeight.W_700, font_family=FONT_CN)], spacing=7, alignment=ft.MainAxisAlignment.CENTER),
                    ),
                    ft.Container(
                        expand=True,
                        padding=ft.Padding(left=14, right=14, top=10, bottom=10),
                        border_radius=20,
                        bgcolor=ft.Colors.with_opacity(0.88, C["jade"]),
                        ink=True,
                        on_click=confirm_basic_and_generate,
                        content=ft.Row([icon_image("api", 18), ft.Text("确认生成", size=self.ui_size(12), color=C["ink"], weight=ft.FontWeight.W_700, font_family=FONT_CN)], spacing=7, alignment=ft.MainAxisAlignment.CENTER),
                    ),
                ], spacing=10),
            ], spacing=9),
        )

        basic_card = section_card(
            "基础档案",
            "先输入基础档案和 MBTI，再让模型自动生成性格背景与数值标签。",
            "new_character",
            [
                ft.Row([
                    input_type_chip("选项：身份 / 公司规模 / 时间线 / 国籍 / MBTI / 生理周期", C["jade"]),
                    input_type_chip("手动：艺名 / 本名 / 年龄 / 身高", C["lotus"]),
                    input_type_chip("自动：重名校验 / AI生成 / 标签 / 数值倾向", C["apricot"]),
                ], spacing=8, wrap=True),
                ft.Text("先确定选项和手动字段。点击确认后，系统会自动校验重名、年龄和身高；校验通过后才会进入AI生成。", size=self.ui_size(11), color=C["sub"], font_family=FONT_CN),
                ft.Row([identity, company_size, timeline, nationality, mbti, self.dice_button(randomize_mbti, "随机MBTI"), period_mode, self.period_intro_button()], spacing=10, wrap=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([
                    ft.Column([
                        ft.Row([manual_field_row("艺名"), manual_field_row("本名")], spacing=14, wrap=True),
                        ft.Row([manual_field_row("年龄"), manual_field_row("身高")], spacing=14, wrap=True),
                    ], spacing=10, expand=True),
                    action_bar,
                ], spacing=18, vertical_alignment=ft.CrossAxisAlignment.START),
            ],
            expand=False,
        )

        result_row_1 = self.generated_result_row([
            generated_card("外貌风格", "new_character", 430, 4),
            generated_card("性格", "diary", 430, 4),
            generated_card("在团定位", "stage", 430, 4),
        ])
        result_row_2 = self.generated_result_row([
            generated_card("特长", "stage", 430, 3),
            generated_card("弱项", "health", 430, 3),
            generated_card("爱好", "schedule", 430, 3),
        ])
        result_row_3 = self.generated_result_row([
            generated_card("家庭状况", "family", 640, 4),
            generated_card("练习生经历", "contract", 640, 4),
        ])
        result_row_4 = self.generated_result_row([
            generated_card("你希望观众记住你的什么", "fans", 640, 4),
            boundary_container,
        ])
        result_row_5 = self.generated_result_row([
            generated_card("其他补充", "diary", 1296, 4),
        ])
        generated_result_containers.extend([result_row_1, result_row_2, result_row_3, result_row_4, result_row_5])
        hide_generated_result_containers()

        create_button_row = ft.Row([
            ft.Container(
                padding=ft.Padding(left=18, right=18, top=10, bottom=10),
                border_radius=22,
                bgcolor=ft.Colors.with_opacity(0.86, C["jade"]),
                ink=True,
                on_click=create,
                content=ft.Text("创建角色", size=self.ui_size(13), color=C["ink"], font_family=FONT_CN, weight=ft.FontWeight.W_700),
            ),
            ft.Container(
                padding=ft.Padding(left=18, right=18, top=10, bottom=10),
                border_radius=22,
                bgcolor=ft.Colors.with_opacity(0.78, ft.Colors.WHITE),
                border=ft.Border.all(1, ft.Colors.with_opacity(0.52, C["line"])),
                ink=True,
                on_click=lambda e: self.show_home(),
                content=ft.Text("返回首页", size=self.ui_size(13), color=C["dai"], font_family=FONT_CN, weight=ft.FontWeight.W_700),
            ),
        ], spacing=10)
        create_button_row.visible = False

        ai_card = section_card(
            "AI生成结果",
            "AI生成项会显示在这里；剧情边界由玩家自己填写。觉得不合理可以微调后再创建角色。",
            "stage",
            [
                ft.Container(
                    padding=ft.Padding(left=14, right=14, top=12, bottom=12),
                    border_radius=20,
                    bgcolor=ft.Colors.with_opacity(0.54, ft.Colors.WHITE),
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.42, C["line"])),
                    content=ft.Row([result_progress, result_hint], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ),
                result_row_1,
                result_row_2,
                result_row_3,
                result_row_4,
                result_row_5,
                status,
                create_button_row,
            ],
            expand=False,
        )

        header = ft.Container(
            padding=ft.Padding(left=30, right=30, top=18, bottom=12),
            content=ft.Row([
                ft.Container(icon_image("new_character", 30, 0.95), width=46, height=46, border_radius=18, bgcolor=ft.Colors.with_opacity(0.45, C["lotus"]), alignment=ft.Alignment.CENTER),
                ft.Column([
                    ft.Text("角色创建", size=self.ui_size(26), weight=ft.FontWeight.W_700, color=C["ink"], font_family=FONT_CN),
                    ft.Text("基础数据确认后自动校验并生成AI设定；生成结果可以微调。", size=self.ui_size(12), color=C["sub"], font_family=FONT_CN),
                ], spacing=1),
                ft.Container(expand=True),
                ft.Container(
                    padding=ft.Padding(left=14, right=14, top=8, bottom=8),
                    border_radius=20,
                    bgcolor=ft.Colors.with_opacity(0.78, ft.Colors.WHITE),
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.58, C["line"])),
                    ink=True,
                    on_click=lambda e: self.show_home(),
                    content=ft.Row([icon_image("app_logo", 18), ft.Text("返回首页", size=self.ui_size(12), color=C["dai"], font_family=FONT_CN, weight=ft.FontWeight.W_700)], spacing=7),
                ),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )

        content = ft.Column([
            header,
            ft.Container(
                expand=True,
                padding=ft.Padding(left=28, right=28, top=10, bottom=28),
                content=ft.Column([
                    basic_card,
                    ai_card,
                ], spacing=18, expand=True, scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            ),
        ], expand=True)

        self.page.add(ft.Stack([self.character_create_bg(), content], expand=True))
        self.page.update()


