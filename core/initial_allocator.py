from __future__ import annotations

from typing import Any, Dict, List, Tuple
import re

from core.models import GameState
from core.talents import generate_talents


CAREER_KEYS = ["舞蹈实力", "声乐实力", "RAP能力", "舞台感染力", "综艺感", "语言能力", "演技潜力", "创作能力", "制作人能力"]


def clamp(v: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(v)))


def add(d: Dict[str, int], key: str, delta: int, log: List[str], reason: str, cap: int | None = None) -> None:
    old = d.get(key, 0)
    new = old + delta
    if cap is not None:
        new = min(new, cap)
    d[key] = clamp(new)
    if delta != 0:
        log.append(f"{key}: {old} → {d[key]}（{reason}）")


def mbti_letters(character: Dict[str, Any]) -> tuple[str, str, str, str, str]:
    code = str(character.get("MBTI") or "").upper().strip()
    if not re.match(r"^[IE][NS][TF][JP]$", code):
        code = "INFP"
    return code, code[0], code[1], code[2], code[3]


def normalize_company_size(character: Dict[str, Any]) -> str:
    raw = str(character.get("公司规模") or character.get("公司类型") or "").strip()
    identity = str(character.get("身份") or character.get("身份来源") or "")
    tags = " ".join(map(str, character.get("出身来源标签", []) or []))
    text = f"{raw} {identity} {tags}"
    if any(k in text for k in ["大型", "大公司", "头部", "四大", "TOP", "top"]):
        return "大型公司"
    if any(k in text for k in ["小型", "小公司", "独立", "小厂"]):
        return "小型公司"
    return "中型公司"


def apply_company_size_profile(state: GameState, character: Dict[str, Any], log: List[str]) -> None:
    size = normalize_company_size(character)
    profile = {
        "大型公司": {
            "公司路线": "高资源高竞争",
            "资源池": 78,
            "出道窗口压力": 70,
            "公司满意度": 54,
            "公司信任度": 48,
            "主推指数": 38,
            "资源倾斜度": 42,
            "危机关注度": 18,
            "合约稳定度": 78,
            "个人议价权": 6,
            "续约倾向": 54,
        },
        "中型公司": {
            "公司路线": "均衡培养",
            "资源池": 52,
            "出道窗口压力": 48,
            "公司满意度": 50,
            "公司信任度": 45,
            "主推指数": 35,
            "资源倾斜度": 30,
            "危机关注度": 10,
            "合约稳定度": 70,
            "个人议价权": 10,
            "续约倾向": 50,
        },
        "小型公司": {
            "公司路线": "低资源高自主",
            "资源池": 28,
            "出道窗口压力": 34,
            "公司满意度": 46,
            "公司信任度": 42,
            "主推指数": 28,
            "资源倾斜度": 18,
            "危机关注度": 7,
            "合约稳定度": 55,
            "个人议价权": 18,
            "续约倾向": 42,
        },
    }[size]
    state.company["公司规模"] = size
    for key, value in profile.items():
        state.company[key] = value
    if size == "大型公司":
        state.team["队内竞争度"] = min(100, int(state.team.get("队内竞争度", 35)) + 8)
        state.market["话题度"] = min(100, int(state.market.get("话题度", 15)) + 6)
        log.append("大型公司：资源池更高、曝光和出道窗口更强，但队内竞争与危机关注同步上升。")
    elif size == "小型公司":
        state.market["销量潜力"] = max(0, int(state.market.get("销量潜力", 25)) - 5)
        state.risks["公关危机风险"] = min(100, int(state.risks.get("公关危机风险", 5)) + 3)
        log.append("小型公司：资源池更低、合约稳定度较弱，但个人议价权和自主空间更高。")
    else:
        log.append("中型公司：资源、竞争和风险保持均衡，公司规模会持续影响资源与出道节奏。")


def parse_profile_tags(character: Dict[str, Any]) -> List[str]:
    tags: List[str] = []
    identity = str(character.get("身份", ""))
    source_tags = character.get("出身来源标签", []) or []
    speciality = str(character.get("特长", ""))
    weakness = str(character.get("弱项", ""))
    exp = str(character.get("练习生经历", ""))
    family = str(character.get("家庭状况", ""))
    mbti_code, mbti_e, mbti_p, mbti_j, mbti_l = mbti_letters(character)
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

    # AI/规则匹配标签直接进入 profile_tags，供初始数值分配使用。
    for t in source_tags:
        text = str(t).strip()
        if text:
            tags.append(text)

    # 去重保持顺序
    out = []
    for t in tags:
        if t not in out:
            out.append(t)
    return out


def allocate_initial_state(state: GameState, character: Dict[str, Any]) -> None:
    """Apply initial stats for a new character.

    Career stats are intentionally low for trainee-stage games.
    Talents may be high; current abilities are not.
    """
    log: List[str] = []
    profile_tags = parse_profile_tags(character)
    timeline = str(character.get("时间线", "练习生阶段"))
    identity = str(character.get("身份", ""))

    state.profile_tags = profile_tags
    state.initial_allocation_log = log

    apply_company_size_profile(state, character, log)

    state.talents = generate_talents(character)

    # Low career defaults.
    if "练习生" in timeline:
        state.career = {
            "舞蹈实力": 5,
            "声乐实力": 5,
            "RAP能力": 3,
            "舞台感染力": 4,
            "综艺感": 3,
            "语言能力": 5,
            "演技潜力": 2,
            "创作能力": 2,
            "制作人能力": 0,
        }
        log.append("练习生阶段：职业属性采用低值开局，多数为 2—5。")
        career_cap = 15
    elif "出道前" in timeline:
        state.career = {
            "舞蹈实力": 24,
            "声乐实力": 24,
            "RAP能力": 18,
            "舞台感染力": 22,
            "综艺感": 16,
            "语言能力": 22,
            "演技潜力": 10,
            "创作能力": 8,
            "制作人能力": 0,
        }
        log.append("出道前一天：职业属性进入预备出道水平。")
        career_cap = 45
    elif "回归" in timeline:
        state.career = {
            "舞蹈实力": 45,
            "声乐实力": 42,
            "RAP能力": 30,
            "舞台感染力": 45,
            "综艺感": 32,
            "语言能力": 35,
            "演技潜力": 18,
            "创作能力": 15,
            "制作人能力": 0,
        }
        log.append("回归瓶颈期：职业属性按已出道成员初始化。")
        career_cap = 70
    else:
        state.career = {
            "舞蹈实力": 55,
            "声乐实力": 50,
            "RAP能力": 35,
            "舞台感染力": 55,
            "综艺感": 40,
            "语言能力": 45,
            "演技潜力": 25,
            "创作能力": 20,
            "制作人能力": 5,
        }
        log.append("续约前一年：职业属性按成熟爱豆初始化。")
        career_cap = 80

    # MBTI-based small initial biases. MBTI is a game control variable, not a diagnosis.
    mbti_code, mbti_e, mbti_p, mbti_j, mbti_l = mbti_letters(character)
    state.character["MBTI"] = mbti_code
    state.character.setdefault("MBTI说明", "MBTI只影响叙事倾向和小幅初始数值，不决定角色命运。")
    log.append(f"MBTI {mbti_code}：作为叙事控制变量进入初始分配。")

    if mbti_e == "E":
        add(state.career, "综艺感", 3, log, "E型更主动表达和接梗", min(career_cap, 13 if "练习生" in timeline else career_cap))
        state.team["团队默契度"] += 2
        state.risks["公关危机风险"] += 1
        log.append("E型：团队默契度更高，镜头暴露和公关风险轻微上升。")
    else:
        add(state.career, "创作能力", 2, log, "I型更容易沉淀内心素材", min(career_cap, 10 if "练习生" in timeline else career_cap))
        state.mind["孤独感"] += 4
        state.inner_life["日记倾向"] += 6
        log.append("I型：内心戏和日记倾向更强，孤独感轻微上升。")

    if mbti_p == "N":
        add(state.career, "创作能力", 3, log, "N型更重视概念理解和表达", min(career_cap, 12 if "练习生" in timeline else career_cap))
        add(state.career, "舞台感染力", 2, log, "N型更容易理解舞台叙事", min(career_cap, 13 if "练习生" in timeline else career_cap))
        state.mind["精神压力"] += 2
        log.append("N型：概念消化和舞台表达更强，但更容易想太多。")
    else:
        add(state.career, "舞蹈实力", 2, log, "S型更重视动作复现和细节执行", min(career_cap, 13 if "练习生" in timeline else career_cap))
        state.company["公司信任度"] += 2
        log.append("S型：训练执行稳定，公司信任轻微上升。")

    if mbti_j == "F":
        state.team["队内信任度"] += 3
        state.mind["精神压力"] += 3
        state.inner_life["秘密重量"] = min(100, int(state.inner_life.get("秘密重量", 10)) + 3)
        log.append("F型：共情和团队黏性更高，秘密重量和内耗压力更容易累积。")
    else:
        state.mind["边界感"] = min(100, int(state.mind.get("边界感", 40)) + 4)
        state.team["队内竞争度"] += 1
        log.append("T型：边界感更高，冲突表达更直接。")

    if mbti_l == "J":
        state.company["公司信任度"] += 3
        state.mind["精神压力"] += 2
        state.schedule_profile["discipline_score"] = min(100, int(state.schedule_profile.get("discipline_score", 50)) + 4)
        log.append("J型：计划性和纪律性更强，公司信任上升，责任压力略高。")
    else:
        add(state.career, "舞台感染力", 2, log, "P型更依赖现场反应和即兴", min(career_cap, 13 if "练习生" in timeline else career_cap))
        state.risks["行程泄露风险"] += 1
        state.schedule_profile["discipline_score"] = max(0, state.schedule_profile.get("discipline_score", 50) - 2)
        log.append("P型：现场反应更灵活，纪律波动和行程风险轻微上升。")

    # Tag-based low boosts.
    if "舞蹈基础" in profile_tags:
        add(state.career, "舞蹈实力", 5, log, "特长/经历包含舞蹈基础", min(career_cap, 15 if "练习生" in timeline else career_cap))
        add(state.career, "舞台感染力", 2, log, "舞蹈基础带来舞台感", min(career_cap, 12 if "练习生" in timeline else career_cap))
    if "声乐基础" in profile_tags:
        add(state.career, "声乐实力", 5, log, "特长/经历包含声乐基础", min(career_cap, 15 if "练习生" in timeline else career_cap))
    if "RAP基础" in profile_tags:
        add(state.career, "RAP能力", 5, log, "特长/经历包含 RAP", min(career_cap, 15 if "练习生" in timeline else career_cap))
    if "表演基础" in profile_tags:
        add(state.career, "演技潜力", 5, log, "特长包含表演/演技", min(career_cap, 12 if "练习生" in timeline else career_cap))
    if "创作兴趣" in profile_tags:
        add(state.career, "创作能力", 4, log, "有创作兴趣或基础", min(career_cap, 12 if "练习生" in timeline else career_cap))

    if "镜头优势" in profile_tags or "视觉优势" in profile_tags:
        add(state.career, "舞台感染力", 3, log, "外貌/镜头风格匹配带来镜头表现优势", min(career_cap, 14 if "练习生" in timeline else career_cap))
        state.market["话题度"] += 4
        log.append("镜头/视觉优势：舞台感染力和初始话题度小幅上升。")

    if "综艺潜力" in profile_tags:
        add(state.career, "综艺感", 5, log, "性格与反应方式具备综艺潜力", min(career_cap, 15 if "练习生" in timeline else career_cap))

    if "体能短板" in profile_tags:
        state.body["体力"] = max(0, state.body.get("体力", 70) - 8)
        state.body["肌肉疲劳"] = min(100, state.body.get("肌肉疲劳", 10) + 6)
        log.append("体能短板：初始体力下降，肌肉疲劳偏高。")

    if "语言压力" in profile_tags:
        add(state.career, "语言能力", -2, log, "语言压力影响初期表达与采访稳定性", career_cap)
        state.mind["精神压力"] += 4
        log.append("语言压力：语言能力轻微受限，精神压力上升。")

    if "家庭压力" in profile_tags:
        state.mind["精神压力"] += 6
        state.mind["孤独感"] += 3
        log.append("家庭压力：精神压力与孤独感上升。")

    if "心理敏感" in profile_tags:
        state.mind["精神压力"] += 4
        state.mind["自我认同"] = max(0, state.mind.get("自我认同", 50) - 3)
        log.append("心理敏感：精神压力上升，自我认同略低。")

    if "前运动员" in profile_tags:
        add(state.career, "舞蹈实力", 3, log, "前运动员的身体控制迁移到舞蹈学习", min(career_cap, 14 if "练习生" in timeline else career_cap))
        add(state.career, "舞台感染力", 2, log, "竞技经历带来舞台承压经验", min(career_cap, 12 if "练习生" in timeline else career_cap))
        state.body["体力"] = 86
        state.body["旧伤负担"] = 18
        state.body["伤病风险"] = 20
        log.append("前运动员：体力较高，但旧伤负担和伤病风险同步上升。")

    if "选秀淘汰者" in profile_tags:
        add(state.career, "舞台感染力", 5, log, "选秀经历带来镜头与舞台经验", 20 if "练习生" in timeline else career_cap)
        add(state.career, "综艺感", 3, log, "选秀经历带来镜头表达经验", 18 if "练习生" in timeline else career_cap)
        state.fans["个人粉丝数"] += 3000
        state.fans["黑粉活跃度"] += 5
        state.mind["精神压力"] += 8
        log.append("选秀淘汰者：自带少量粉丝、黑粉与失败记忆压力。")

    if "再出道" in profile_tags:
        add(state.career, "舞台感染力", 6, log, "再出道经历带来真实舞台经验", 20 if "练习生" in timeline else career_cap)
        state.mind["职业倦怠"] += 12
        state.mind["精神压力"] += 6
        log.append("再出道：舞台经验更强，但职业倦怠和压力更高。")

    if "海外练习生" in profile_tags:
        add(state.career, "语言能力", 4, log, "海外背景带来外语/跨文化优势", min(career_cap, 14 if "练习生" in timeline else career_cap))
        state.mind["孤独感"] += 10
        log.append("海外练习生：语言/海外潜力增加，同时孤独感上升。")

    if "顶流亲属" in profile_tags:
        state.market["话题度"] += 15
        state.fans["黑粉活跃度"] += 8
        state.mind["精神压力"] += 8
        log.append("顶流亲属：初始话题高，但比较压力和黑粉更高。")

    if "优渥家庭" in profile_tags:
        add(state.career, "声乐实力", 2, log, "优渥家庭可能带来早期课程资源", min(career_cap, 12 if "练习生" in timeline else career_cap))
        add(state.career, "语言能力", 2, log, "优渥教育资源带来语言基础", min(career_cap, 12 if "练习生" in timeline else career_cap))
        state.fans["黑粉活跃度"] += 3
        log.append("优渥家庭：课程资源略高，但关系户争议风险存在。")


    if "素人发掘" in profile_tags or "适应期新人" in profile_tags:
        state.company["公司信任度"] += 1
        state.mind["精神压力"] += 2
        log.append("素人/适应期新人：可塑性较高，但初入体系的压力略高。")

    if "校园演出经验" in profile_tags:
        add(state.career, "舞台感染力", 2, log, "校园演出带来基础舞台适应", min(career_cap, 12 if "练习生" in timeline else career_cap))

    if "舞台经验" in profile_tags:
        add(state.career, "舞台感染力", 4, log, "既有舞台经验提升舞台稳定性", min(career_cap, 16 if "练习生" in timeline else career_cap))

    if "训练适应快" in profile_tags:
        state.schedule_profile["discipline_score"] = min(100, int(state.schedule_profile.get("discipline_score", 50)) + 3)
        add(state.career, "舞蹈实力", 1, log, "训练适应较快", min(career_cap, 12 if "练习生" in timeline else career_cap))
        log.append("训练适应快：纪律分和基础训练吸收略高。")

    if "既有流量" in profile_tags:
        state.market["话题度"] += 10
        state.fans["个人粉丝数"] += 1200
        log.append("既有流量：初始话题度和个人粉丝数上升。")

    if "黑粉争议风险" in profile_tags:
        state.fans["黑粉活跃度"] += 7
        state.risks["公关危机风险"] += 3
        log.append("黑粉争议风险：黑粉活跃和公关风险上升。")

    if "关系户争议风险" in profile_tags:
        state.fans["黑粉活跃度"] += 5
        state.mind["精神压力"] += 4
        log.append("关系户争议风险：外部质疑带来黑粉和心理压力。")

    if "公众审视压力" in profile_tags:
        state.market["话题度"] += 6
        state.mind["精神压力"] += 5
        log.append("公众审视压力：话题度上升，同时精神压力上升。")

    if "文化适应压力" in profile_tags:
        state.mind["孤独感"] += 4
        state.social_context["cultural_adaptation"] = max(0, int(state.social_context.get("cultural_adaptation", 55)) - 5)
        log.append("文化适应压力：孤独感上升，文化适应度下降。")

    if "纪律适应风险" in profile_tags:
        state.schedule_profile["discipline_score"] = max(0, state.schedule_profile.get("discipline_score", 50) - 4)
        state.company["公司信任度"] = max(0, state.company.get("公司信任度", 45) - 2)
        log.append("纪律适应风险：纪律分和公司信任略降。")

    if "体能优势" in profile_tags:
        state.body["体力"] = min(100, int(state.body.get("体力", 70)) + 8)
        log.append("体能优势：初始体力上升。")

    if "旧伤风险" in profile_tags:
        state.body["旧伤负担"] = min(100, int(state.body.get("旧伤负担", 0)) + 10)
        state.body["伤病风险"] = min(100, int(state.body.get("伤病风险", 10)) + 5)
        log.append("旧伤风险：旧伤负担和伤病风险上升。")

    if "职业倦怠风险" in profile_tags:
        state.mind["职业倦怠"] += 8
        log.append("职业倦怠风险：开局职业倦怠更高。")


    # Weakness penalties.
    if "舞蹈短板" in profile_tags:
        add(state.career, "舞蹈实力", -2, log, "弱项包含舞蹈", career_cap)
    if "声乐短板" in profile_tags:
        add(state.career, "声乐实力", -2, log, "弱项包含声乐", career_cap)
    if "语言短板" in profile_tags:
        add(state.career, "语言能力", -2, log, "弱项包含语言", career_cap)

    # Always force producer ability low at start.
    if "练习生" in timeline:
        state.career["制作人能力"] = 0
    elif "出道前" in timeline or "回归" in timeline:
        state.career["制作人能力"] = min(state.career.get("制作人能力", 0), 5)

    # Career caps for trainee.
    if "练习生" in timeline:
        for key in CAREER_KEYS:
            cap = 15
            if "选秀淘汰者" in profile_tags or "再出道" in profile_tags:
                cap = 20 if key in {"舞台感染力", "舞蹈实力", "声乐实力", "综艺感"} else 15
            if key == "制作人能力":
                cap = 0
            state.career[key] = clamp(state.career[key], 0, cap)

        # Market/fandom mostly near zero unless special background.
        state.market["品牌价值"] = min(state.market.get("品牌价值", 0), 5)
        state.market["韩国本土影响力"] = min(state.market.get("韩国本土影响力", 0), 5)
        state.fans["团体粉丝数"] = 0

    log.append("制作人能力开局不因兴趣上升，必须通过创作能力与真实项目逐步解锁。")
