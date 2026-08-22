from __future__ import annotations

import random
import re
import secrets
from typing import Any, Dict, List, Optional, Tuple

from core.models import (
    CompanySize,
    GameState,
)
from core.company_curriculum import TRAINING_WEIGHTS_BY_STYLE
from core.company_profile import derive_company_profile
from core.menstrual_cycle import apply_daily_menstrual_physiology, initialize_menstrual_cycle
from core.npc_initialization import initialize_npc_roster


# 正式 Skill 的固定生成顺序：决定本地 PRNG 的随机数消耗顺序，
# 保证同一 rng_seed 下初始化结果稳定、可重复。
TALENT_SKILL_ORDER = (
    "dance",
    "vocal",
    "rap",
    "stage",
    "camera",
    "language",
    "acting",
    "creation",
)

# 创建表单中的背景修正键 → 正式技能名（仅用于一次性背景修正映射）。
_BOOST_TO_SKILL = {
    "舞蹈天赋": "dance",
    "声乐天赋": "vocal",
    "RAP天赋": "rap",
    "镜头天赋": "camera",
    "语言天赋": "language",
    "演技天赋": "acting",
    "创作天赋": "creation",
}


def generate_talents(rng_seed: int, character: Dict[str, object]) -> Dict[str, int]:
    """生成新角色的一次性初始 Talent（与 8 个正式 Skill 一一对应）。

    第一层：基础值由本地 random.Random(rng_seed) 按固定技能顺序
    （TALENT_SKILL_ORDER）各生成一个 35–75 的独立随机数；
    第二层：身份 / 特长 / 弱项等背景对初始 Talent 做一次性修正。

    Talent 只在这里生成一次并写入 SkillState.talent，之后直接读取，
    运行时不重新推导，也不根据角色资料决定任何随机 seed。
    """
    rng = random.Random(rng_seed)
    talents: Dict[str, int] = {skill: rng.randint(35, 75) for skill in TALENT_SKILL_ORDER}

    identity = str(character.get("身份", ""))
    speciality = str(character.get("特长", ""))
    weakness = str(character.get("弱项", ""))

    def boost(key: str, amount: int) -> None:
        skill = _BOOST_TO_SKILL[key]
        talents[skill] = max(0, min(100, talents[skill] + amount))

    if "舞" in speciality:
        boost("舞蹈天赋", 12)
    if "声乐" in speciality or "唱" in speciality:
        boost("声乐天赋", 10)
    if "rap" in speciality.lower() or "说唱" in speciality:
        boost("RAP天赋", 10)
    if "镜头" in speciality or "门面" in speciality:
        boost("镜头天赋", 8)
    if "演技" in speciality or "表演" in speciality:
        boost("演技天赋", 8)
    if "作词" in speciality or "作曲" in speciality or "创作" in speciality:
        boost("创作天赋", 10)

    if "舞" in weakness:
        boost("舞蹈天赋", -8)
    if "声乐" in weakness or "唱" in weakness:
        boost("声乐天赋", -8)
    if "韩语" in weakness or "语言" in weakness:
        boost("语言天赋", -6)

    if "运动员" in identity:
        boost("舞蹈天赋", 5)
    if "海外" in identity:
        boost("语言天赋", 10)
    if "童星" in identity or "模特" in identity:
        boost("镜头天赋", 12)
        boost("演技天赋", 6)
    if "选秀" in identity:
        boost("镜头天赋", 8)
    if "网红" in identity:
        boost("镜头天赋", 8)

    return talents


def clamp(v: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(v)))


def mbti_letters(character: Dict[str, Any]) -> Optional[Tuple[str, str, str, str, str]]:
    """合法 MBTI 才返回四字母分解；未提供/非法格式返回 None（绝不伪造 INFP）。"""
    code = str(character.get("MBTI") or "").upper().strip()
    if not re.match(r"^[IE][NS][TF][JP]$", code):
        return None
    return code, code[0], code[1], code[2], code[3]


def normalize_company_size(character: Dict[str, Any]) -> CompanySize:
    raw = str(character.get("公司规模") or character.get("公司类型") or "").strip()
    identity = str(character.get("身份") or character.get("身份来源") or "")
    tags = " ".join(map(str, character.get("出身来源标签", []) or []))
    text = f"{raw} {identity} {tags}"
    if any(k in text for k in ["大型", "大公司", "头部", "四大", "TOP", "top"]):
        return CompanySize.LARGE
    if any(k in text for k in ["小型", "小公司", "独立", "小厂"]):
        return CompanySize.SMALL
    return CompanySize.MEDIUM


def parse_profile_tags(character: Dict[str, Any]) -> List[str]:
    tags: List[str] = []
    identity = str(character.get("身份", ""))
    source_tags = character.get("出身来源标签", []) or []
    speciality = str(character.get("特长", ""))
    weakness = str(character.get("弱项", ""))
    exp = str(character.get("练习生经历", ""))
    family = str(character.get("家庭状况", ""))
    mbti_letters_result = mbti_letters(character)
    if mbti_letters_result is not None:
        mbti_code, mbti_e, mbti_p, mbti_j, mbti_l = mbti_letters_result
        tags.extend([f"MBTI:{mbti_code}", f"MBTI-{mbti_e}", f"MBTI-{mbti_p}", f"MBTI-{mbti_j}", f"MBTI-{mbti_l}"])

    if "运动员" in identity or any("运动员" in str(t) for t in source_tags):
        tags.append("前运动员")
    if "海外" in identity or any("海外" in str(t) for t in source_tags):
        tags.append("海外练习生")
    if "顶流" in identity or "妹妹" in identity or "亲属" in identity:
        tags.append("顶流亲属")
    if "选秀" in identity or any("选秀" in str(t) for t in source_tags):
        tags.append("选秀淘汰者")
    if "再出道" in identity or "小公司" in identity:
        tags.append("再出道")
    if "富二代" in identity or "优渥" in identity:
        tags.append("优渥家庭")
    if "网红" in ",".join(map(str, source_tags)):
        tags.append("网红出身")
    if "童星" in ",".join(map(str, source_tags)) or "儿童模特" in ",".join(map(str, source_tags)):
        tags.append("童星/模特")
    if "舞" in speciality or "舞" in exp:
        tags.append("舞蹈基础")
    if "声乐" in speciality or "唱" in speciality or "声乐" in exp:
        tags.append("声乐基础")
    if "rap" in speciality.lower() or "说唱" in speciality:
        tags.append("RAP基础")
    if "演技" in speciality or "表演" in speciality:
        tags.append("表演基础")
    if "作词" in speciality or "作曲" in speciality or "创作" in speciality:
        tags.append("创作兴趣")
    if "韩语" in weakness or "语言" in weakness:
        tags.append("语言短板")
    if "声乐" in weakness or "唱" in weakness:
        tags.append("声乐短板")
    if "舞" in weakness:
        tags.append("舞蹈短板")
    if family:
        tags.append("家庭背景已设定")

    for t in source_tags:
        text = str(t).strip()
        if text:
            tags.append(text)

    out = []
    for t in tags:
        if t not in out:
            out.append(t)
    return out


def _parse_int(value: Any) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    m = re.search(r"\d+", text)
    if not m:
        return None
    try:
        return int(m.group())
    except Exception:
        return None


def apply_company_profile(state: GameState, character: Dict[str, Any], log: List[str]) -> None:
    """由创建输入确定公司规模，其余画像由存档 rng_seed 确定性生成。

    只有 resource_level 受 size 的范围约束（区间故意重叠）；
    training_style / management_style / training_intensity 与规模完全无关。
    training_weights 由 training_style 的官方基础模板确定（同一风格固定权重）。
    """
    size = normalize_company_size(character)
    profile = derive_company_profile(size, state.meta.rng_seed)
    state.company.name = str(character.get("公司") or "").strip()
    state.company.size = size
    state.company.training_style = profile.training_style
    state.company.management_style = profile.management_style
    state.company.training_intensity = profile.training_intensity
    state.company.resource_level = profile.resource_level
    state.company.training_weights = TRAINING_WEIGHTS_BY_STYLE[profile.training_style].model_copy(deep=True)
    log.append(
        f"公司画像：规模 {size.value}，培养风格 {profile.training_style.value}，"
        f"管理风格 {profile.management_style.value}，训练强度 {profile.training_intensity}，"
        f"资源水平 {profile.resource_level}。课程权重按培养风格基础模板确定。"
    )


def apply_skill_initial(state: GameState, character: Dict[str, Any], tags: List[str], log: List[str]) -> None:
    talents = generate_talents(state.meta.rng_seed, character)

    for key, skill in [
        ("dance", state.skills.dance), ("vocal", state.skills.vocal),
        ("rap", state.skills.rap), ("stage", state.skills.stage),
        ("camera", state.skills.camera), ("language", state.skills.language),
        ("acting", state.skills.acting), ("creation", state.skills.creation),
    ]:
        skill.talent = talents[key]
        if key in {"acting", "creation"}:
            skill.unlocked = False
            skill.value = None
            skill.form = None
            skill.exploration_progress = 0
            log.append(f"{key}.talent = {skill.talent}（隐藏天赋，已生成，未解锁）")
        else:
            skill.unlocked = True
            skill.exploration_progress = 100

    values: Dict[str, int] = {"dance": 5, "vocal": 5, "rap": 3, "stage": 4, "camera": 3, "language": 5}
    cap = 15

    def add_value(key: str, delta: int, reason: str) -> None:
        values[key] = clamp(values[key] + delta, 0, cap)
        if delta != 0:
            log.append(f"skills.{key}.value：{values[key]}（{reason}）")

    if "舞蹈基础" in tags:
        add_value("dance", 5, "特长/经历包含舞蹈基础")
        add_value("stage", 2, "舞蹈基础带来舞台感")
    if "声乐基础" in tags:
        add_value("vocal", 5, "特长/经历包含声乐基础")
    if "RAP基础" in tags:
        add_value("rap", 5, "特长/经历包含 RAP")
    if "镜头优势" in tags or "视觉优势" in tags:
        add_value("camera", 3, "外貌/镜头风格匹配带来镜头表现优势")
        add_value("stage", 2, "镜头感支撑舞台表现")
    if "综艺潜力" in tags:
        add_value("camera", 5, "性格与反应方式具备综艺潜力")
    if "校园演出经验" in tags:
        add_value("stage", 2, "校园演出带来基础舞台适应")
    if "舞台经验" in tags:
        add_value("stage", 4, "既有舞台经验提升舞台稳定性")
    if "选秀淘汰者" in tags:
        add_value("stage", 5, "选秀经历带来镜头与舞台经验")
        add_value("camera", 3, "选秀经历带来镜头表达经验")
    if "再出道" in tags:
        add_value("stage", 6, "再出道经历带来真实舞台经验")
    if "海外练习生" in tags:
        add_value("language", 4, "海外背景带来外语/跨文化优势")
    if "前运动员" in tags:
        add_value("dance", 3, "前运动员的身体控制迁移到舞蹈学习")
        add_value("stage", 2, "竞技经历带来舞台承压经验")
    if "训练适应快" in tags:
        add_value("dance", 1, "训练适应较快")
    if "优渥家庭" in tags:
        add_value("vocal", 2, "优渥家庭可能带来早期课程资源")
        add_value("language", 2, "优渥教育资源带来语言基础")

    if "语言短板" in tags:
        add_value("language", -2, "弱项包含语言")
    if "舞蹈短板" in tags:
        add_value("dance", -2, "弱项包含舞蹈")
    if "声乐短板" in tags:
        add_value("vocal", -2, "弱项包含声乐")

    for key, skill in [
        ("dance", state.skills.dance), ("vocal", state.skills.vocal),
        ("rap", state.skills.rap), ("stage", state.skills.stage),
        ("camera", state.skills.camera), ("language", state.skills.language),
    ]:
        skill.value = clamp(values[key], 0, cap)
        skill.form = float(skill.value)
        skill.xp = 0.0
        skill.last_practiced_date = None
        log.append(f"skills.{key}：value={skill.value}，form={skill.form}，unlocked=True")


def apply_condition_initial(state: GameState, tags: List[str], log: List[str]) -> None:
    c = state.condition
    c.energy = 80
    c.muscle_fatigue = 20
    c.injury_risk = 15
    c.voice_condition = 80
    c.sleep_condition = 70
    c.stress = 35
    c.mood = 70
    c.confidence = 55

    def mod(key: str, delta: int, reason: str) -> None:
        setattr(c, key, clamp(getattr(c, key) + delta))
        if delta != 0:
            log.append(f"condition.{key}：{getattr(c, key)}（{reason}）")

    if "体能短板" in tags:
        mod("energy", -8, "体能短板")
        mod("muscle_fatigue", 6, "体能短板")
    if "体能优势" in tags:
        mod("energy", 8, "体能优势")
    if "前运动员" in tags:
        c.energy = 86
        mod("injury_risk", 5, "前运动员旧伤负担")
        mod("muscle_fatigue", 5, "前运动员训练负荷")
    if "旧伤风险" in tags:
        mod("injury_risk", 5, "旧伤风险")
    if "语言压力" in tags:
        mod("stress", 4, "语言压力影响初期表达")
    if "家庭压力" in tags:
        mod("stress", 6, "家庭压力")
    if "心理敏感" in tags:
        mod("stress", 4, "心理敏感")
        mod("confidence", -3, "心理敏感")
    if "选秀淘汰者" in tags:
        mod("stress", 8, "失败记忆带来额外压力")
    if "再出道" in tags:
        mod("stress", 6, "再出道压力")
    if "海外练习生" in tags:
        mod("stress", 5, "海外适应压力")
        mod("mood", -8, "海外孤独感")
    if "顶流亲属" in tags:
        mod("stress", 8, "比较压力较高")
    if "关系户争议风险" in tags:
        mod("stress", 4, "外部质疑带来心理压力")
    if "公众审视压力" in tags:
        mod("stress", 5, "公众审视压力")
    if "文化适应压力" in tags:
        mod("mood", -5, "文化适应压力")
    if "职业倦怠风险" in tags:
        mod("stress", 6, "职业倦怠风险")
        mod("mood", -4, "职业倦怠风险")
    if "素人发掘" in tags or "适应期新人" in tags:
        mod("stress", 2, "初入体系的压力略高")


def apply_trainee_initial(state: GameState, log: List[str]) -> None:
    """练习生身份初始化为真正意义上的入社第一天。

    没有公司内部资历；正式月评结果在第一次月评前保持 None（真正 Unknown）。
    过去经历只决定角色自身水平，不决定公司已经怎么看她。
    """
    t = state.trainee
    t.status = "active"
    t.training_level = 1
    t.latest_evaluation_score = None
    t.latest_evaluation_date = None
    log.append("trainee：入社第一天。latest_evaluation_score / date 为 None（尚无正式月评结果）。")


def apply_player_initial(state: GameState, character: Dict[str, Any], tags: List[str], log: List[str]) -> None:
    p = state.player
    p.name = str(character.get("本名") or "").strip()
    p.stage_name = str(character.get("艺名") or "").strip()
    p.nationality = str(character.get("国籍") or "").strip()
    p.birthday = None
    p.starting_age = _parse_int(character.get("年龄"))
    p.height_cm = _parse_int(character.get("身高"))
    p.identity_source = str(character.get("身份") or "").strip()
    p.mbti = str(character.get("MBTI") or "").strip()
    p.mbti_profile = character.get("MBTI人格倾向") if isinstance(character.get("MBTI人格倾向"), dict) else {}
    p.appearance = str(character.get("外貌风格") or "").strip()
    p.personality = str(character.get("性格") or "").strip()
    p.interests = str(character.get("爱好") or "").strip()
    p.strengths = str(character.get("特长") or "").strip()
    p.weak_points = str(character.get("弱项") or "").strip()
    p.family_background = str(character.get("家庭状况") or "").strip()
    p.background = str(character.get("练习生经历") or "").strip()
    p.trainee_position = str(character.get("在团定位") or "").strip()
    p.player_wish = str(character.get("你希望观众记住你的什么") or "").strip()
    p.story_boundary = str(character.get("你不希望剧情触碰的内容") or "").strip()
    p.extra_notes = str(character.get("其他补充") or "").strip()
    p.avatar = str(character.get("avatar") or "").strip()
    p.source_tags = list(tags)

    if p.starting_age is not None:
        log.append(f"player.starting_age = {p.starting_age}（创建流程只提供年龄，不伪造具体生日）")


def allocate_initial_state(state: GameState, character: Dict[str, Any]) -> List[str]:
    """根据角色创建数据构造新的权威 GameState（failure-atomic）。

    只迁移：人物稳定事实、常规技能初始值、隐藏天赋、身体心理初始状态、
    公司基本事实、练习生入社第一天的身份、Company Local Roster（NPC 人物圈）。

    过去经历（身份 / 背景 / 标签）只在此处一次性结算初始数值，
    不会形成后续隐藏倍率或持续修正。MBTI 仅作为人格描述事实保存，
    不参与任何数值分配。所有角色都从入社第一天开始。

    本函数是“新建存档”的正式入口：只在这里随机生成一次世界根随机种子
    （MetaState.rng_seed），随后保存进存档；读档时直接恢复存档里的值，
    绝不根据角色资料、日期或 save_id 重新计算。

    原子性：所有初始化在 deep copy 上完成，全部成功后才一次性提交回输入
    state；任何异常时输入 state 保持完全不变。
    """
    working = state.model_copy(deep=True)

    log: List[str] = []
    timeline = str(character.get("时间线", "练习生阶段"))
    if timeline != "练习生阶段":
        log.append(f"时间线「{timeline}」暂按练习生阶段初始化；出道后内容将在后续版本重新设计。")

    tags = parse_profile_tags(character)
    working.meta.rng_seed = secrets.randbits(64)
    log.append(f"meta.rng_seed = {working.meta.rng_seed}（新建存档时随机生成一次，与角色资料无关）")

    apply_player_initial(working, character, tags, log)
    apply_company_profile(working, character, log)
    apply_skill_initial(working, character, tags, log)
    apply_condition_initial(working, tags, log)
    apply_trainee_initial(working, log)

    # Menstrual Cycle bootstrap + 第一可玩日生理影响（作用于 time.current_date，非 created_date）。
    initialize_menstrual_cycle(working)
    apply_daily_menstrual_physiology(
        working.menstrual_cycle, working.condition, working.time.current_date, working.meta.rng_seed
    )
    log.append("menstrual_cycle 已初始化并应用第一可玩日生理影响（每天仅应用一次）。")

    # Company Profile 完成后生成 Company Local Roster（一次性 world bootstrap）。
    initialize_npc_roster(working)
    working.day = type(working.day)()
    log.append(
        f"NPC Local Roster 已初始化：{len(working.npcs)} 人"
        f"（trainee/teacher/manager/staff 按 CompanySize={working.company.size.value} 确定，关系均为陌生人初始值）。"
    )

    # 提交：全部成功后先对 working_state 做一次完整 model revalidation
    #（防止 helper 经 assignment 写入非法值绕过 validator），再一次性写回输入 state。
    GameState.model_validate(working.model_dump())
    for field_name in GameState.model_fields:
        setattr(state, field_name, getattr(working, field_name))
    return log
