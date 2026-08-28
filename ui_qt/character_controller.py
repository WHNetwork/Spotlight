from __future__ import annotations

import json
import random
import re
from typing import Any, Dict, List, Optional

from loguru import logger
from PySide6.QtCore import QObject, Property, QRunnable, QThreadPool, Qt, Signal, Slot

from core.character_validator import CharacterValidationError, validate_character_input
from core.company_curriculum import build_day_with_courses
from core.config import AppConfig
from core.day_schedule import build_base_day
from core.initial_allocator import allocate_initial_state
from core.llm import LLMError, get_llm_provider
from core.models import EducationStatus, GameState
from core.storage import SaveStorage

_IDENTITY_OPTIONS = [
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
]

_COMPANY_SIZE_OPTIONS = ["大型公司", "中型公司", "小型公司"]

_NATIONALITY_OPTIONS = [
    "中国", "韩国", "日本", "泰国", "美国华裔", "加拿大华裔",
    "澳大利亚华裔", "新加坡", "越南", "菲律宾", "马来西亚",
]

_MBTI_OPTIONS = [
    "INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP",
    "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP",
]

# 正式 AI 生成字段（与旧 Flet 角色创建系统一致，键名/含义不变）。
_AI_FIELDS = [
    "外貌风格", "性格", "爱好", "特长", "弱项", "家庭状况", "练习生经历",
    "在团定位", "你希望观众记住你的什么", "其他补充",
]

_EDU_MAP = {
    "ENROLLED": EducationStatus.ENROLLED,
    "NOT_ENROLLED": EducationStatus.NOT_ENROLLED,
}


# ---------------------------------------------------------------------------
# 纯逻辑 helper（从旧 Flet ui/sections/character.py 原样迁移，算法不改动，
# 只是脱离 Flet 视图层，供 Qt 前端复用）。
# ---------------------------------------------------------------------------

def _normalize_name_key(name: Any) -> str:
    return re.sub(r"\s+", "", str(name or "").strip()).lower()


def _save_name(character: Dict[str, Any]) -> str:
    art = str(character.get("艺名") or "").strip()
    real = str(character.get("本名") or "").strip()
    return art or real or "星光练习室存档"


def _existing_name_keys(storage: SaveStorage) -> set:
    keys: set = set()
    try:
        saves = storage.list_saves()
    except Exception:
        logger.exception("list_saves failed for duplicate check")
        saves = []
    for item in saves:
        for raw in [item.get("name"), item.get("save_name")]:
            key = _normalize_name_key(raw)
            if key:
                keys.add(key)
        sid = item.get("id")
        if sid is None:
            continue
        try:
            state = storage.load_save(int(sid))
            p = state.player
            for raw in [state.save_name, p.stage_name, p.name]:
                key = _normalize_name_key(raw)
                if key:
                    keys.add(key)
        except Exception:
            continue
    return keys


def _random_character_names(nationality: str | None, storage: SaveStorage) -> Dict[str, str]:
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

    existing = _existing_name_keys(storage)

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
            _normalize_name_key(real) not in existing
            and _normalize_name_key(art) not in existing
            and _normalize_name_key(real) != _normalize_name_key(art)
        ):
            return {"艺名": art, "本名": real}
    stamp = random.randint(100, 999)
    return {"艺名": f"Stella{stamp}", "本名": f"Trainee {stamp}"}


_RANDOM_FIELD_POOL: Dict[str, List[str]] = {
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


def _random_field_value(field_name: str, nationality: str | None = None) -> str:
    if field_name == "国籍":
        return random.choice(["中国", "韩国", "日本", "泰国", "越南", "菲律宾", "马来西亚", "新加坡", "美国华裔", "加拿大华裔", "澳大利亚华裔"])
    if field_name == "年龄":
        return random.choice(["15", "16", "17", "18", "19", "20", "21"])
    return random.choice(_RANDOM_FIELD_POOL.get(field_name, [""]))


def _mbti_profile(mbti: str | None) -> Dict[str, Any]:
    code = str(mbti or "").upper().strip()
    if code not in _MBTI_OPTIONS:
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


def _infer_source_tags(character: Dict[str, Any]) -> List[str]:
    tags: List[str] = []

    def add_tag(tag: str) -> None:
        tag = str(tag or "").strip()
        if tag and tag not in tags:
            tags.append(tag)

    joined = " ".join(str(v) for v in character.values() if v is not None)
    identity_source = str(character.get("身份") or character.get("身份来源") or "").strip()

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

    profile = _mbti_profile(character.get("MBTI"))
    for tag in profile.get("stat_tags", []):
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
        ("舞", "舞蹈基础"), ("舞社", "舞蹈基础"), ("扒舞", "舞蹈基础"),
        ("声乐", "声乐基础"), ("音色", "声乐基础"), ("唱", "声乐基础"),
        ("rap", "RAP基础"), ("节奏", "RAP基础"),
        ("镜头", "镜头优势"), ("门面", "视觉优势"), ("外貌", "视觉优势"), ("模特", "视觉优势"),
        ("综艺", "综艺潜力"), ("采访", "综艺潜力"),
        ("校园", "校园演出经验"), ("线上选拔", "线上选拔入社"),
        ("家庭压力", "家庭压力"), ("经济压力", "家庭压力"), ("优渥", "优渥家庭"), ("富裕", "优渥家庭"),
        ("学业", "学业压力"), ("韩语", "语言压力"),
        ("内耗", "心理敏感"), ("敏感", "心理敏感"),
        ("体能", "体能短板"), ("运动员", "前运动员"), ("旧伤", "旧伤风险"), ("伤", "身体风险"),
    ]
    lower_joined = joined.lower()
    for key, tag in keyword_rules:
        if key.lower() in lower_joined:
            add_tag(tag)

    if not tags:
        tags = ["普通练习生", "待观察"]
    return tags[:12]


def _validate_numeric_fields(character: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
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


def _validate_name_unique(character: Dict[str, Any], storage: SaveStorage) -> List[str]:
    existing = _existing_name_keys(storage)
    errors: List[str] = []
    art = str(character.get("艺名") or "").strip()
    real = str(character.get("本名") or "").strip()
    save_name = _save_name(character)
    for label, value in [("艺名", art), ("本名", real), ("存档名", save_name)]:
        key = _normalize_name_key(value)
        if key and key in existing:
            errors.append(f"{label}“{value}”已经存在。请换一个名字，避免角色档案串档。")
    if art and real and _normalize_name_key(art) == _normalize_name_key(real):
        errors.append("艺名和本名不能完全一样。")
    return errors


def _parse_json_object(raw: str) -> Dict[str, Any]:
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


def _normalize_ai_match(payload: Dict[str, Any], basic: Dict[str, Any]) -> Dict[str, Any]:
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
        tags = _infer_source_tags(temp)
    result["出身来源标签"] = tags[:8]
    return result


def _fallback_ai_match(basic: Dict[str, Any]) -> Dict[str, Any]:
    identity = str(basic.get("身份") or "")
    nationality = str(basic.get("国籍") or "")
    age = str(basic.get("年龄") or "")
    height = str(basic.get("身高") or "")
    mbti = str(basic.get("MBTI") or "INFP").upper()
    art_name = str(basic.get("艺名") or basic.get("本名") or "她")
    overseas = nationality and "韩国" not in nationality
    profile = _mbti_profile(mbti)
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
    seen = []
    for t in base["出身来源标签"]:
        if t and t not in seen:
            seen.append(t)
    base["出身来源标签"] = seen[:10]
    return base


def _generate_ai_match(config: AppConfig, basic: Dict[str, Any]) -> Dict[str, Any]:
    system = (
        "你是KPOP女团练习生叙事模拟器的角色设定生成器。"
        "你要根据玩家已经填写的基础信息，尤其是MBTI，自动匹配角色的外貌风格、性格、家庭背景、练习生经历、定位、优势短板和出身来源标签。"
        "MBTI在这里是叙事控制变量，不是真实心理诊断；它只能影响反应倾向、关系节奏和压力表达，不能把角色写成刻板模板。"
        "要求：1. 必须严格输出JSON对象；2. 不要Markdown；3. 不要解释；4. 内容要现实，符合KPOP练习生生态；"
        "5. 不要写露骨性内容；6. 身份来源由玩家选择，不能改写；7. 身份标签/出身来源标签必须依据身份来源、国籍、年龄、MBTI和基础信息推断，标签会影响初始数值。"
    )
    user = {
        "基础信息": basic,
        "MBTI叙事倾向": _mbti_profile(basic.get("MBTI")),
        "必须输出字段": [
            "外貌风格", "性格", "爱好", "特长", "弱项", "家庭状况", "练习生经历",
            "在团定位", "你希望观众记住你的什么", "其他补充",
            "出身来源标签",
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
    provider = get_llm_provider(config)
    raw = provider.generate(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        model=config.model_for_tier("flash"),
    )
    payload = _parse_json_object(raw)
    if not payload:
        raise LLMError("角色匹配模型没有返回可解析JSON。")
    return _normalize_ai_match(payload, basic)


def _random_avatar_path(character: Dict[str, Any]) -> str:
    seed_text = str(character.get("艺名") or character.get("本名") or "starlight")
    idx = (sum(ord(ch) for ch in seed_text) % 36) + 1
    return f"avatars/avatar_{idx:03d}.png"


class _GenerateMatchTask(QRunnable):
    """AI 角色设定生成，在 QThreadPool worker 中执行（避免冻结 Qt UI）。

    LLM 失败时使用旧正式 fallback 规则兜底，与旧 Flet 行为一致。
    """

    def __init__(self, config: AppConfig, basic: Dict[str, Any], done_signal) -> None:
        super().__init__()
        self._config = config
        self._basic = basic
        self._done = done_signal

    def run(self) -> None:
        try:
            match = _generate_ai_match(self._config, self._basic)
            self._done.emit(True, match, "")
        except Exception as exc:  # noqa: BLE001
            logger.exception("AI character matching failed")
            match = _fallback_ai_match(self._basic)
            note = match.get("其他补充", "")
            extra = f"\n模型匹配失败，已使用本地规则兜底：{exc}"
            match["其他补充"] = (note + extra)[:380]
            self._done.emit(True, match, "")


_OPENING_SYSTEM_PROMPT = (
    "你是《星光练习室》的温柔叙事者。请为一位刚刚选择成为偶像练习生的人写一段开场白。"
    "要求：温柔、优美、克制；大意是：既然选择了这条路，就认真努力地走到出道那天；"
    "生活很美好，值得坚持。不要使用夸张口号，不要堆砌感叹号，不超过 140 字，直接输出正文，不要任何前后缀。"
)

_OPENING_FALLBACK_TEXT = (
    "练习室的灯亮着，镜子里的你还带着一点点不确定。选择这条路本身，就已经是勇敢的第一步。"
    "星光不会辜负认真练习的人——把每一天都过得值得，出道那天会来得刚好。"
)


class _OpeningMessageTask(QRunnable):
    """开场白生成，在 QThreadPool worker 中执行（不冻结 Qt UI）。失败用本地文案兜底。"""

    def __init__(self, config: AppConfig, done_signal) -> None:
        super().__init__()
        self._config = config
        self._done = done_signal

    def run(self) -> None:
        try:
            provider = get_llm_provider(self._config)
            raw = provider.generate(
                [
                    {"role": "system", "content": _OPENING_SYSTEM_PROMPT},
                    {"role": "user", "content": "请开始。"},
                ],
                model=self._config.model_for_tier("flash"),
                json_mode=False,
            )
            text = str(raw or "").strip()
            if not text:
                raise LLMError("开场白为空。")
            self._done.emit(True, text[:400], "")
        except Exception as exc:  # noqa: BLE001
            logger.exception("opening message generation failed")
            self._done.emit(False, _OPENING_FALLBACK_TEXT, str(exc))


class CharacterController(QObject):
    """轻量桥接：角色创建页 → 旧正式角色创建逻辑 + 正式 GameState/存档初始化。

    - 暴露正式选项列表（国籍/MBTI/身份/公司规模）。
    - 随机基础资料：复用旧随机算法，不改 mechanics。
    - AI 设定生成：QThreadPool worker 中调用旧正式 LLM 流程（失败用 fallback）。
    - 创建存档：正式 validate → allocate_initial_state → 设置 education_status
      → 正式 build_base_day + build_day_with_courses 生成第一天 8 Slot → create_save。
    """

    characterCreated = Signal(int)          # save_id
    matchDone = Signal(bool, object, str)   # ok, match(dict), error
    generatingChanged = Signal()
    aiResultChanged = Signal()              # AI result saved -> QML sync
    openingMessageDone = Signal(bool, str, str)  # ok, text, error

    def __init__(self, config: Optional[AppConfig] = None, parent=None) -> None:
        super().__init__(parent)
        self._storage = SaveStorage()
        self._config = config or AppConfig()
        self._generating = False
        self._ai_ready = False
        self._ai_result: Dict[str, Any] = {}
        self._opening_pending = False
        self.matchDone.connect(self._on_match_done, Qt.QueuedConnection)
        self.openingMessageDone.connect(self._on_opening_done, Qt.QueuedConnection)

    # ---- option lists -----------------------------------------------------
    @Property("QVariantList", constant=True)
    def identityOptions(self) -> list:  # noqa: N802
        return _IDENTITY_OPTIONS

    @Property("QVariantList", constant=True)
    def companySizeOptions(self) -> list:  # noqa: N802
        return _COMPANY_SIZE_OPTIONS

    @Property("QVariantList", constant=True)
    def nationalityOptions(self) -> list:  # noqa: N802
        return _NATIONALITY_OPTIONS

    @Property("QVariantList", constant=True)
    def mbtiOptions(self) -> list:  # noqa: N802
        return _MBTI_OPTIONS

    @Property(bool, notify=generatingChanged)
    def generating(self) -> bool:  # noqa: N802
        return self._generating

    # ---- AI result (stable English bridge keys; source is the official
    #      Chinese JSON schema, never invented) -----------------------------
    def _ai_text(self, key: str) -> str:
        return str(self._ai_result.get(key, "") or "").strip()

    @Property(bool, notify=aiResultChanged)
    def aiReady(self) -> bool:  # noqa: N802
        return self._ai_ready

    @Property(str, notify=aiResultChanged)
    def aiPersonality(self) -> str:  # noqa: N802
        return self._ai_text("性格")

    @Property(str, notify=aiResultChanged)
    def aiAppearanceStyle(self) -> str:  # noqa: N802
        return self._ai_text("外貌风格")

    @Property(str, notify=aiResultChanged)
    def aiHobbies(self) -> str:  # noqa: N802
        return self._ai_text("爱好")

    @Property(str, notify=aiResultChanged)
    def aiStrengths(self) -> str:  # noqa: N802
        return self._ai_text("特长")

    @Property(str, notify=aiResultChanged)
    def aiWeaknesses(self) -> str:  # noqa: N802
        return self._ai_text("弱项")

    @Property(str, notify=aiResultChanged)
    def aiFamily(self) -> str:  # noqa: N802
        return self._ai_text("家庭状况")

    @Property(str, notify=aiResultChanged)
    def aiBackground(self) -> str:  # noqa: N802
        return self._ai_text("练习生经历")

    @Property(str, notify=aiResultChanged)
    def aiPosition(self) -> str:  # noqa: N802
        return self._ai_text("在团定位")

    @Property(str, notify=aiResultChanged)
    def aiWish(self) -> str:  # noqa: N802
        return self._ai_text("你希望观众记住你的什么")

    @Property(str, notify=aiResultChanged)
    def aiExtra(self) -> str:  # noqa: N802
        return self._ai_text("其他补充")

    @Property("QVariantList", notify=aiResultChanged)
    def aiTags(self) -> list:  # noqa: N802
        tags = self._ai_result.get("出身来源标签", [])
        return [str(t) for t in tags if str(t).strip()] if isinstance(tags, list) else []

    # ---- randomize --------------------------------------------------------
    @Slot(dict, result="QVariantMap")
    def randomizeBasic(self, values: dict) -> dict:  # noqa: N802
        """按旧正式逻辑随机生成基础资料（国籍→姓名→年龄/身高→MBTI）。"""
        nationality = str(values.get("国籍", "") or "").strip() or "中国"
        new_nationality = _random_field_value("国籍", nationality)
        names = _random_character_names(new_nationality, self._storage)
        return {
            "国籍": new_nationality,
            "艺名": names["艺名"],
            "本名": names["本名"],
            "年龄": _random_field_value("年龄", new_nationality),
            "身高": _random_field_value("身高", new_nationality),
            "MBTI": random.choice(_MBTI_OPTIONS),
        }

    # ---- AI match generation ----------------------------------------------
    def _basic_errors(self, basic: Dict[str, Any]) -> List[str]:
        errors = _validate_numeric_fields(dict(basic))
        errors += _validate_name_unique(basic, self._storage)
        if not str(basic.get("身份") or "").strip():
            errors.append("必须选择身份来源。")
        if not str(basic.get("国籍") or "").strip():
            errors.append("必须选择国籍。")
        if not str(basic.get("艺名") or "").strip() and not str(basic.get("本名") or "").strip():
            errors.append("艺名和本名至少填写一个。")
        return errors

    @Slot(dict)
    def generateCharacterMatch(self, basic: dict) -> None:  # noqa: N802
        """确认基础档案：先做正式校验（不通过则不发 AI 请求），通过后 worker 生成。"""
        if self._generating:
            return
        errors = self._basic_errors(basic)
        if errors:
            self.matchDone.emit(False, {}, "\n".join(errors))
            return
        self._generating = True
        self.generatingChanged.emit()
        task = _GenerateMatchTask(self._config, basic, self.matchDone)
        QThreadPool.globalInstance().start(task)

    @Slot(bool, object, str)
    def _on_match_done(self, ok: bool, match: object, error: str) -> None:  # noqa: N802
        self._generating = False
        self.generatingChanged.emit()
        if ok and isinstance(match, dict):
            self._ai_result = match
            self._ai_ready = True
            self.aiResultChanged.emit()

    # ---- opening message -------------------------------------------------
    @Slot()
    def requestOpeningMessage(self) -> None:  # noqa: N802
        """异步请求创建角色前的开场白（失败自动回退本地文案）。"""
        if self._opening_pending:
            return
        self._opening_pending = True
        task = _OpeningMessageTask(self._config, self.openingMessageDone)
        QThreadPool.globalInstance().start(task)

    @Slot(bool, str, str)
    def _on_opening_done(self, ok: bool, text: str, error: str) -> None:  # noqa: N802
        self._opening_pending = False

    # ---- create save ------------------------------------------------------
    def _build_full_character(self, values: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "身份": str(values.get("identity", "") or "").strip(),
            "公司规模": str(values.get("companySize", "") or "").strip(),
            "时间线": "练习生阶段",  # 项目正式固定范围，不在 UI 暴露
            "国籍": str(values.get("nationality", "") or "").strip(),
            "MBTI": str(values.get("mbti", "") or "").strip(),
            "MBTI人格倾向": _mbti_profile(values.get("mbti", "")),
            "艺名": str(values.get("stageName", "") or "").strip(),
            "本名": str(values.get("realName", "") or "").strip(),
            "年龄": str(values.get("age", "") or "").strip(),
            "身高": str(values.get("height", "") or "").strip(),
            "外貌风格": str(values.get("appearance", "") or "").strip(),
            "性格": str(values.get("personality", "") or "").strip(),
            "爱好": str(values.get("interests", "") or "").strip(),
            "特长": str(values.get("strengths", "") or "").strip(),
            "弱项": str(values.get("weaknesses", "") or "").strip(),
            "家庭状况": str(values.get("family", "") or "").strip(),
            "练习生经历": str(values.get("background", "") or "").strip(),
            "在团定位": str(values.get("position", "") or "").strip(),
            "你希望观众记住你的什么": str(values.get("wish", "") or "").strip(),
            "其他补充": str(values.get("extra", "") or "").strip(),
            "你不希望剧情触碰的内容": str(values.get("boundary", "") or "").strip(),
            "出身来源标签": list(values.get("sourceTags", []) or []),
        }

    @Slot(dict, result=str)
    def createCharacter(self, values: dict) -> str:  # noqa: N802
        """正式创建：校验 → allocate_initial_state → education_status →
        第一天 8 Slot（正式 build_base_day + build_day_with_courses）→ create_save。
        """
        try:
            raw = self._build_full_character(values)
            errors = _validate_numeric_fields(dict(raw))
            errors += _validate_name_unique(raw, self._storage)
            if errors:
                return "创建失败：" + "；".join(errors)

            normalized = validate_character_input(raw)
            data = normalized.data
            data["avatar"] = _random_avatar_path(raw)
            data["出身来源标签"] = raw.get("出身来源标签", [])
            data["MBTI"] = raw.get("MBTI")
            data["MBTI人格倾向"] = raw.get("MBTI人格倾向")

            edu_raw = str(values.get("educationStatus", "") or "").upper()
            edu = _EDU_MAP.get(edu_raw, EducationStatus.ENROLLED)

            state = GameState()
            allocate_initial_state(state, data)
            state.player.education_status = edu

            # 正式第一天：与 day_settlement 使用同一套机制（基础日程 + 公司课程）。
            day = build_base_day(state.time, edu)
            day = build_day_with_courses(
                day, state.company, edu, state.meta.rng_seed, state.time.current_date
            )
            state.day = day

            save_id = self._storage.create_save(state)
            logger.info(f"character created: save_id={save_id}, edu={edu.value}")
            self.characterCreated.emit(int(save_id))
            return "角色创建成功。"
        except CharacterValidationError as exc:
            return "创建失败：" + "；".join(exc.errors)
        except Exception as exc:  # noqa: BLE001
            logger.exception("createCharacter failed")
            return f"创建失败：{exc}"
