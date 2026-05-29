from __future__ import annotations

from typing import Dict, List, Tuple
from core.models import GameState, SystemEvent, RouteInfo
from core.rules import _add

CRISIS_WORDS = ["回应", "澄清", "声明", "道歉", "公关", "舆论", "热搜", "黑粉", "造谣", "霸凌", "不和", "恋爱曝光", "曝光", "私生", "追车", "泄露", "住址", "伤病", "发烧", "崩溃", "退团", "解约", "雪藏", "争议"]
MAINLINE_WORDS = ["出道", "回归", "一位", "大赏", "颁奖", "续约", "合同", "谈判", "维权", "暂停活动", "solo", "Solo", "单飞", "演员", "转型", "解散", "世巡", "演唱会", "主打歌"]
FOCUS_WORDS = ["考核", "会议", "镜头", "part", "center", "分量", "资源", "概念", "风格", "制作", "demo", "团综", "直播", "签售", "综艺", "队友", "谈心", "品牌", "代言", "杂志", "商业", "直拍", "榜单", "销量", "音源"]

def classify_turn(action: str, state: GameState) -> RouteInfo:
    if any(word in action for word in CRISIS_WORDS):
        return RouteInfo(model_tier="pro", turn_kind="crisis", reason="危机/公关/安全/严重关系事件，自动使用 Pro。")
    if any(word in action for word in MAINLINE_WORDS):
        if state.is_trainee_stage():
            return RouteInfo(model_tier="flash", turn_kind="focus", reason="练习生阶段的正式爱豆行动已被阶段门控降级，使用 Flash。")
        return RouteInfo(model_tier="pro", turn_kind="mainline", reason="主线职业节点，自动使用 Pro。")
    if any(word in action for word in FOCUS_WORDS):
        return RouteInfo(model_tier="flash", turn_kind="focus", reason="重点剧情回合，使用 Flash。")
    if state.active_crises:
        return RouteInfo(model_tier="pro", turn_kind="crisis", reason="存在未关闭危机窗口，自动使用 Pro。")
    return RouteInfo(model_tier="flash", turn_kind="ordinary", reason="普通养成/日常推进回合，使用 Flash。")

def ev(code: str, title: str, severity: str, system: str, desc: str, diff: Dict[str, int] | None = None, flags: List[str] | None = None, tags: List[str] | None = None) -> SystemEvent:
    return SystemEvent(code=code, title=title, severity=severity, source_system=system, description=desc, suggested_diff=diff or {}, new_flags=flags or [title], tags=tags or [system])

def evaluate_health_system(state: GameState, action: str) -> List[SystemEvent]:
    events: List[SystemEvent] = []
    if state.body.get("体力", 100) < 35:
        events.append(ev("health_low_stamina", "体力透支预警", "warning", "health", "你的体力已经低于安全线。本回合训练收益会下降，疲劳、低血糖或注意力波动事件概率上升。", {"心理状态.精神压力": 2, "身体状态.免疫状态": -3, "风险.伤病爆发风险": 3}))
    if state.body.get("伤病风险", 0) > 75 or state.body.get("肌肉疲劳", 0) > 80:
        events.append(ev("health_injury_warning", "伤病风险临界", "crisis" if state.body.get("伤病风险", 0) > 85 else "warning", "health", "高强度训练正在把小疼痛推向真正的伤病。继续硬撑会影响后续舞台。", {"心理状态.精神压力": 2, "公司与合约.危机关注度": 2}))
    if state.body.get("嗓音状态", 100) < 45:
        events.append(ev("health_voice_warning", "嗓音状态预警", "warning", "health", "你的嗓子开始发紧。录音、安可和声乐课都会受到影响。", {"职业属性.声乐实力": -1, "心理状态.精神压力": 1}))
    if state.mind.get("精神压力", 0) > 75:
        events.append(ev("mind_high_pressure", "精神压力过载", "warning", "mind", "精神压力已经接近过载。误会、失眠和情绪失控概率上升。", {"心理状态.心情": -3, "心理状态.职业倦怠": 3}))
    return events

def evaluate_resource_system(state: GameState, action: str) -> List[SystemEvent]:
    events: List[SystemEvent] = []
    if state.is_trainee_stage():
        if any(w in action for w in ["月末考核展示", "评估录像", "展示段落", "考核曲"]):
            events.append(ev("trainee_resource_request", "练习生展示机会请求", "info", "trainee_resource", "你触碰的是练习生阶段的展示机会，而不是正式爱豆资源。老师和经纪人会把它理解为考核积极性。", {"团队关系.队内竞争度": 1, "公司与合约.公司信任度": 1}))
        return events

    if any(w in action for w in ["镜头", "part", "center", "分量", "资源", "主推"]):
        events.append(ev("resource_negotiation", "资源分配被拉到台面上", "info", "resource", "你开始触碰镜头、part、center 或个人资源的问题。它会同时影响公司判断、唯粉情绪和队友竞争。", {"团队关系.队内竞争度": 3, "粉丝与舆论.唯粉攻击性": 2, "公司与合约.危机关注度": 1}))
    return events

def evaluate_fandom_pr_system(state: GameState, action: str) -> List[SystemEvent]:
    events: List[SystemEvent] = []
    if any(w in action for w in ["回应", "澄清", "道歉", "声明", "不回应", "公关"]):
        events.append(ev("pr_response_window", "进入回应窗口", "warning", "public_relations", "你已经进入舆论回应窗口。回应方式会影响粉丝信任、公司满意度、黑粉活跃度和长期 public image。", {"公司与合约.危机关注度": 2}))
        events.append(ev("crisis_pr_response_window", "公关危机回应窗口", "warning", "public_relations", "这不是普通沟通，而是危机生命周期的一部分。沉默、回应或错误回应都会改变长期后果。", {"风险.公关危机风险": 1}, tags=["public_relations", "crisis"]))
    if not state.is_trainee_stage() and state.fans.get("黑粉活跃度", 0) > 70:
        events.append(ev("fandom_anti_high", "黑粉高活跃", "warning", "fandom", "黑粉活跃度已经很高。旧片段、表情截图和舞台失误都容易被剪辑传播。", {"风险.公关危机风险": 4, "心理状态.精神压力": 2}))
    return events

def evaluate_team_lens_system(state: GameState, action: str) -> List[SystemEvent]:
    events: List[SystemEvent] = []
    if state.team.get("营业疲劳", 0) > 70 and state.team.get("真实关系温度", 100) < 40:
        events.append(ev("lens_harmony_crack", "镜头前和谐裂缝", "crisis", "team_lens", "真实关系温度低，但镜头前和谐长期维持，营业疲劳已经很高。下一次直播、团综或采访可能被剪成不和证据。", {"风险.队内不和曝光风险": 6, "风险.公关危机风险": 4, "心理状态.精神压力": 3}))
    return events

def evaluate_love_safety_system(state: GameState, action: str) -> List[SystemEvent]:
    events: List[SystemEvent] = []
    if not state.is_trainee_stage() and state.risks.get("恋爱风险", 0) > 60:
        events.append(ev("love_risk_visible", "恋爱风险可见化", "warning", "love", "恋爱风险已经进入可被经纪人、站姐或队友察觉的区间。", {"风险.公关危机风险": 3, "公司与合约.危机关注度": 3}))
    if state.risks.get("私生风险", 0) > 70 or state.risks.get("行程泄露风险", 0) > 70:
        events.append(ev("sasaeng_security_warning", "私生安全风险", "crisis", "safety", "私生或行程泄露风险过高。宿舍、酒店、机场或私人行程可能出现安全事件。", {"心理状态.精神压力": 4, "风险.公关危机风险": 3, "公司与合约.危机关注度": 5}))
    return events

def evaluate_comeback_system(state: GameState, action: str) -> List[SystemEvent]:
    events: List[SystemEvent] = []
    if state.is_trainee_stage():
        if any(w in action for w in ["作词作曲训练", "练习用 demo", "出道组概念课", "写demo", "demo", "作词", "作曲", "创作"]):
            events.append(ev("trainee_creation_training", "练习生创作训练", "info", "creation", "你现在能做的是训练创作基本功，而不是决定正式回归。", {"职业属性.创作能力": 1, "心理状态.自我认同": 1}))
        return events

    if any(w in action for w in ["风格", "概念", "回归", "demo", "制作", "主打"]):
        level = int(state.comeback.get("制作参与等级", 0))
        if level <= 0 and any(w in action for w in ["坚持", "争取", "自己想法", "我的想法"]):
            events.append(ev("comeback_low_authority", "制作参与权不足", "warning", "comeback", "你开始争取回归表达权，但当前制作参与等级还低。强硬争取可能提高自我认同，也可能让公司觉得你不好管理。", {"心理状态.自我认同": 2, "公司与合约.公司满意度": -2}))
        else:
            events.append(ev("comeback_style_discussion", "回归风格讨论", "info", "comeback", "你触及了回归风格或概念方向。这会影响音源潜力、舞台传播、公司满意度和队内分量。", {"心理状态.自我认同": 1}))
    return events

def evaluate_delay_consequences(state: GameState, action: str) -> List[SystemEvent]:
    events: List[SystemEvent] = []
    if "镜头前和谐裂缝" in state.flags and state.risks.get("队内不和曝光风险", 0) > 45:
        events.append(ev("delayed_team_pr_risk", "延迟后果：不和剪辑风险", "warning", "delayed_consequence", "之前长期没有处理的队内裂缝正在回流。下一次公开内容中，微小表情也可能被剪辑放大。", {"风险.公关危机风险": 3, "粉丝与舆论.黑粉活跃度": 2}))
    if "伤病风险临界" in state.flags and state.body.get("体力", 100) < 45:
        events.append(ev("delayed_injury_debt", "延迟后果：伤病债", "warning", "delayed_consequence", "之前没有完全处理的伤病风险还在。疲劳状态下继续训练会让它回到剧情中心。", {"身体状态.伤病风险": 3, "风险.伤病爆发风险": 4}))
    return events

def evaluate_all_systems(state: GameState, action: str) -> Tuple[List[SystemEvent], Dict[str, int]]:
    events: List[SystemEvent] = []
    for fn in [evaluate_health_system, evaluate_resource_system, evaluate_fandom_pr_system, evaluate_team_lens_system, evaluate_love_safety_system, evaluate_comeback_system, evaluate_delay_consequences]:
        events.extend(fn(state, action))
    unique = {}
    for evnt in events:
        unique[evnt.code] = evnt
    events = list(unique.values())
    system_diff: Dict[str, int] = {}
    for evnt in events:
        for key, value in evnt.suggested_diff.items():
            _add(system_diff, key, value)
    return events, system_diff
