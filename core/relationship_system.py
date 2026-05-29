from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Tuple
from core.models import GameState, SystemEvent


REL_KEYS = [
    "friendship",
    "trust",
    "dependence",
    "intimacy_comfort",
    "rivalry",
    "boundary_clarity",
    "care_memory",
    "shared_secret",
    "player_crush",
    "player_misread_probability",
    "player_expectation",
    "fear_of_ruining_friendship",
    "npc_romantic_interest_hidden",
    "npc_boundary_hidden",
    "ambiguity",
    "business_cp_level",
    "cp_fandom_pressure",
    "relationship_risk",
]


def clamp(v: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(v)))


def _stable_int(seed: str, low: int, high: int) -> int:
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    val = int(h[:8], 16)
    return low + (val % (high - low + 1))


def _add(diff: Dict[str, int], key: str, val: int) -> None:
    diff[key] = diff.get(key, 0) + val


def _event(code: str, title: str, desc: str, severity: str = "info", diff: Dict[str, int] | None = None, flags: List[str] | None = None) -> SystemEvent:
    return SystemEvent(
        code=code,
        title=title,
        severity=severity,
        description=desc,
        source_system="relationship",
        suggested_diff=diff or {},
        new_flags=flags or [title],
        tags=["relationship"],
    )


def _merge_event_diff(diff: Dict[str, int], event: SystemEvent) -> None:
    for key, value in event.suggested_diff.items():
        diff[key] = diff.get(key, 0) + value


def default_relationship(name: str, role: str = "同期练习生", age: int | None = None) -> Dict[str, Any]:
    seed = f"{name}|{role}|{age}"
    npc_romantic = _stable_int(seed + "|romance", 5, 55)
    npc_boundary = _stable_int(seed + "|boundary", 35, 85)
    orientation_visibility = "未知"
    return {
        "name": name,
        "role": role,
        "age": age,
        "is_minor": bool(age is not None and age < 18),
        "public_relation_state": "陌生",
        "private_relation_state": "普通同期",
        "friendship": 20,
        "trust": 20,
        "dependence": 5,
        "intimacy_comfort": 10,
        "rivalry": 25,
        "boundary_clarity": 55,
        "care_memory": 0,
        "shared_secret": 0,
        "player_crush": 0,
        "player_misread_probability": 10,
        "player_expectation": 0,
        "fear_of_ruining_friendship": 15,
        "npc_romantic_interest_hidden": npc_romantic,
        "npc_boundary_hidden": npc_boundary,
        "npc_orientation_visibility": orientation_visibility,
        "ambiguity": 0,
        "business_cp_level": 0,
        "cp_fandom_pressure": 0,
        "relationship_risk": 0,
        "cp_eligible": False,
        "relationship_category": relationship_category_for_role(role),
        "professional_role_category": staff_role_category(role),
        "role_viewpoint": role_viewpoint(role),
        "professional_boundary_pressure": 0,
        "last_signals": [],
        "observed_clues": [],
        "confirmed_state": "未确认",
    }

def _npc_name_from_record(record: Any) -> str:
    if isinstance(record, dict):
        return str(record.get("name") or record.get("姓名") or record.get("艺名") or record.get("本名") or "").strip()
    return ""


def _npc_role_from_record(record: Any) -> str:
    if isinstance(record, dict):
        return str(record.get("role") or record.get("身份") or record.get("关系") or "剧情人物").strip()
    return "剧情人物"


def _is_generic_npc_name(name: str) -> bool:
    text = str(name or "").strip()
    if not text:
        return True
    return text in {"NPC", "npc", "人物", "人物1", "人物2", "人物3", "角色", "对方", "某人", "旁人"} or text.startswith("人物")


def infer_role_from_text(name: str, text: str = "") -> str:
    haystack = f"{name} {text}"
    if any(k in haystack for k in ["经纪", "室长", "manager", "Manager"]):
        return "经纪人"
    if any(k in haystack for k in ["老师", "导师", "训练师", "vocal", "dance", "rap"]):
        return "老师"
    if any(k in haystack for k in ["PD", "制作", "主管", "代表", "A&R"]):
        return "制作/管理人员"
    if any(k in haystack for k in ["造型", "化妆", "妆发", "服装", "助理", "工作人员", "staff", "Staff"]):
        return "工作人员"
    if any(k in haystack for k in ["队友", "同期", "练习生", "成员", "同团"]):
        return "同龄练习生"
    if any(k in haystack for k in ["粉丝", "站姐", "粉头"]):
        return "粉丝"
    return "剧情人物"


def known_relationship_names(state: GameState) -> List[str]:
    names: List[str] = []
    for name in (getattr(state, "relationships", {}) or {}).keys():
        if name and name not in names:
            names.append(str(name))
    for collection_name in ("teammates", "important_npcs"):
        for record in getattr(state, collection_name, []) or []:
            name = _npc_name_from_record(record)
            if name and not _is_generic_npc_name(name) and name not in names:
                names.append(name)
    return names


def _infer_named_target_from_action(action: str) -> str | None:
    stop_names = {
        "公司", "老师", "经纪人", "制作人", "工作人员", "队友", "同期", "粉丝",
        "宿舍", "练习室", "考核", "热水", "资源", "镜头", "舞台", "我",
        "他的", "她的", "我的", "你的",
    }
    patterns = [
        r"(?:对|和|跟|与)?([\u4e00-\u9fff]{1,2}PD)(?:的|在|陪|帮|和我|跟我|与我|对我|给我|把|被|产生)",
        r"([\u4e00-\u9fff]{2,4})(?:在|陪|帮|和我|跟我|与我|对我|给我|把|被)",
        r"(?:和|跟|与)([\u4e00-\u9fff]{2,4})(?:的|一起|比较|谈心|练习)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, action):
            name = match.group(1).strip()
            name = name.lstrip("我对和跟与")
            if name and name not in stop_names and not _is_generic_npc_name(name):
                return name
    return None


def register_known_npc(state: GameState, name: str, role: str = "剧情人物", age: int | None = None) -> bool:
    name = str(name or "").strip()
    if _is_generic_npc_name(name):
        return False
    try:
        age = int(age) if age is not None and str(age).strip() else None
    except Exception:
        age = None
    if not hasattr(state, "important_npcs") or state.important_npcs is None:
        state.important_npcs = []
    if not any(_npc_name_from_record(record) == name for record in state.important_npcs):
        record = {"name": name, "role": role or "剧情人物"}
        if age is not None:
            record["age"] = age
        state.important_npcs.append(record)
    if not hasattr(state, "relationships") or state.relationships is None:
        state.relationships = {}
    if name not in state.relationships:
        state.relationships[name] = default_relationship(name, role or "剧情人物", age)
        return True
    return False


def register_response_npcs(state: GameState, response: Any, action: str = "") -> List[str]:
    registered: List[str] = []
    for reaction in getattr(response, "npc_reactions", []) or []:
        name = str(getattr(reaction, "name", "") or "").strip()
        reaction_text = str(getattr(reaction, "reaction", "") or "")
        if _is_generic_npc_name(name):
            continue
        role = str(getattr(reaction, "role", "") or "").strip() or infer_role_from_text(name, f"{action} {reaction_text}")
        age = getattr(reaction, "age", None)
        register_known_npc(state, name, role, age)
        if name not in registered:
            registered.append(name)
    ensure_default_relationships(state)
    return registered


def ensure_default_relationships(state: GameState) -> None:
    if not hasattr(state, "relationships") or state.relationships is None:
        state.relationships = {}

    def sync(rel: Dict[str, Any]) -> None:
        rel["professional_role_category"] = staff_role_category(str(rel.get("role", "")))
        rel["relationship_category"] = relationship_category_for_role(str(rel.get("role", "")))
        rel["role_viewpoint"] = role_viewpoint(str(rel.get("role", "")))
        rel["cp_eligible"] = is_cp_eligible(rel, state)
        rel.setdefault("professional_boundary_pressure", 0)
        if not rel["cp_eligible"]:
            rel["business_cp_level"] = 0
            rel["cp_fandom_pressure"] = 0

    if state.relationships:
        for rel in state.relationships.values():
            sync(rel)
    for collection_name in ("teammates", "important_npcs"):
        for record in getattr(state, collection_name, []) or []:
            name = _npc_name_from_record(record)
            if not name or _is_generic_npc_name(name) or name in state.relationships:
                continue
            role = _npc_role_from_record(record)
            age = record.get("age") if isinstance(record, dict) else None
            rel = default_relationship(name, role, age)
            sync(rel)
            state.relationships[name] = rel

def find_relationship_target(state: GameState, action: str) -> str | None:
    ensure_default_relationships(state)
    inferred = _infer_named_target_from_action(action)
    if inferred and inferred in action:
        if inferred not in state.relationships:
            register_known_npc(state, inferred, infer_role_from_text(inferred, action))
        return inferred
    for name in sorted(known_relationship_names(state), key=len, reverse=True):
        if name and name in action:
            return name
    return None

def classify_relationship_signals(action: str) -> List[str]:
    signals: List[str] = []
    friendship_words = ["陪", "帮", "照顾", "热水", "借", "谈心", "一起练", "安慰", "守着", "分享", "信任"]
    romance_words = ["心动", "喜欢", "在意", "暗恋", "想靠近", "吃醋", "特别", "眼神", "牵手", "想确认关系"]
    boundary_words = ["拒绝", "边界", "保持距离", "只是朋友", "不想越界", "转移话题", "回避", "不方便"]
    business_words = ["营业", "CP", "镜头前", "粉丝想看", "公司安排", "互动", "对视", "牵手营业"]
    risk_words = ["被拍", "站姐", "私生", "曝光", "恋爱风险", "热搜", "粉丝误会", "截图"]
    rivalry_words = ["竞争", "资源", "center", "part", "考核", "被夸", "比较", "嫉妒"]

    if any(w in action for w in friendship_words):
        signals.append("friendship")
    if any(w in action for w in romance_words):
        signals.append("romance")
    if any(w in action for w in boundary_words):
        signals.append("boundary")
    if any(w in action for w in business_words):
        signals.append("business_cp")
    if any(w in action for w in risk_words):
        signals.append("risk")
    if any(w in action for w in rivalry_words):
        signals.append("rivalry")

    return signals



def staff_role_category(role: str) -> str:
    role = str(role or "")
    if any(k in role for k in ["经纪人", "室长", "manager", "Manager"]):
        return "manager"
    if any(k in role for k in ["老师", "导师", "舞蹈老师", "声乐老师", "rap老师", "训练老师"]):
        return "teacher"
    if any(k in role for k in ["PD", "制作人", "主管", "社长", "代表", "A&R", "导演"]):
        return "production"
    if any(k in role for k in ["造型", "化妆", "妆发", "服装", "stylist", "Stylist", "助理"]):
        return "styling"
    if any(k in role for k in ["保镖", "安保", "司机"]):
        return "security"
    if any(k in role for k in ["工作人员", "staff", "Staff"]):
        return "staff"
    if any(k in role for k in ["粉丝", "站姐", "粉头"]):
        return "fan"
    return "non_staff"


def role_viewpoint(role: str) -> str:
    cat = staff_role_category(role)
    mapping = {
        "manager": "管理责任：优先考虑行程、安全、公司风险和合约责任。",
        "teacher": "评价权：优先考虑训练成果、考核表现和课堂秩序。",
        "production": "资源权：掌握概念、part、镜头、选曲或项目机会。",
        "styling": "后台照顾：接触妆发服装、身体边界、舞台准备和临场照顾。",
        "security": "安全职责：优先考虑出入路线、宿舍安全和风险隔离。",
        "staff": "职业协作：在工作流程内提供协助，但仍有职业边界。",
        "fan": "外部凝视：存在明显身份不对等和舆论风险。",
        "non_staff": "普通同龄关系：以同辈互动和个人关系为主。",
    }
    return mapping.get(cat, mapping["non_staff"])


def is_power_imbalanced(rel: Dict[str, Any]) -> bool:
    cat = staff_role_category(str(rel.get("role", "")))
    return cat in {"manager", "teacher", "production", "security", "fan"}


def is_professional_relationship(rel: Dict[str, Any]) -> bool:
    cat = staff_role_category(str(rel.get("role", "")))
    return cat in {"manager", "teacher", "production", "styling", "security", "staff", "fan"}


def is_peer_entertainment_role(rel: Dict[str, Any]) -> bool:
    role = str(rel.get("role", ""))
    if is_professional_relationship(rel):
        return False
    peer_keywords = ["同期练习生", "同龄练习生", "练习生", "队友", "同团成员", "爱豆", "idol", "Idol"]
    return any(k in role for k in peer_keywords)


def cp_age_gap_limit(state: GameState) -> int:
    """Stage-specific CP age-gap rule.

    Trainee stage: <= 3 years.
    Idol/debuted stage: <= 5 years.
    """
    stage_text = f"{state.current_stage} {state.current_mainline} {state.current_schedule}"
    idol_keywords = ["出道", "爱豆", "回归", "打歌", "巡演", "续约", "solo", "Solo", "团体活动"]
    trainee_keywords = ["练习生", "初入公司", "报到", "月末考核"]
    if any(k in stage_text for k in idol_keywords) and not any(k in stage_text for k in trainee_keywords):
        return 5
    return 3


def is_debuted_or_idol_stage(state: GameState) -> bool:
    stage_text = f"{state.current_stage} {state.current_mainline} {state.current_schedule}"
    idol_keywords = ["出道", "爱豆", "回归", "打歌", "巡演", "续约", "solo", "Solo", "团体活动"]
    trainee_keywords = ["练习生", "初入公司", "报到", "月末考核"]
    return any(k in stage_text for k in idol_keywords) and not any(k in stage_text for k in trainee_keywords)


def is_near_age(rel: Dict[str, Any], state: GameState, max_gap: int | None = None) -> bool:
    if max_gap is None:
        max_gap = cp_age_gap_limit(state)

    player_age = state.age_context.get("age")
    npc_age = rel.get("age")
    if player_age is None or npc_age is None:
        return False
    try:
        player_age = int(player_age)
        npc_age = int(npc_age)
    except Exception:
        return False

    # 未成年与成年人不能进入 CP / 恋爱确认 / 成人化亲密。
    if (player_age < 18) != (npc_age < 18):
        return False

    if abs(player_age - npc_age) > max_gap:
        return False

    return True


def is_cp_eligible(rel: Dict[str, Any], state: GameState) -> bool:
    """Only near-age peer trainees/idols can enter the CP/business-relationship system.

    Trainee stage: age gap <= 3.
    Debuted idol stage: age gap <= 5.
    Staff/professional/fan relationships are never CP-eligible.
    """
    if not is_peer_entertainment_role(rel):
        return False

    # 同期练习生如果没有年龄字段，默认视作与玩家同龄。
    if rel.get("age") is None and state.is_trainee_stage():
        return True

    return is_near_age(rel, state, max_gap=cp_age_gap_limit(state))


def is_same_age_staff_crush_allowed(rel: Dict[str, Any], state: GameState) -> bool:
    """A player can like a near-age low-power staff member, but it is a boundary-risk path.

    Staff crush tolerance is stricter than idol CP tolerance: adults only and age gap <= 2.
    This does not apply to managers, teachers, PDs/supervisors, fans, security.
    """
    if state.age_context.get("is_minor", False):
        return False
    cat = staff_role_category(str(rel.get("role", "")))
    if cat not in {"styling", "staff"}:
        return False
    return is_near_age(rel, state, max_gap=2)


def professional_romance_policy(rel: Dict[str, Any], state: GameState) -> str:
    if not is_professional_relationship(rel):
        return "peer_or_other"
    cat = staff_role_category(str(rel.get("role", "")))
    if cat in {"manager", "teacher", "production", "security", "fan"}:
        return "blocked_high_power"
    if is_same_age_staff_crush_allowed(rel, state):
        return "same_age_staff_high_risk"
    return "professional_boundary"


def public_relationship_label(rel: Dict[str, Any], state: GameState) -> str:
    if is_professional_relationship(rel):
        cat = staff_role_category(str(rel.get("role", "")))
        label_map = {
            "manager": "职务关系·经纪",
            "teacher": "职务关系·老师",
            "production": "职务关系·制作",
            "styling": "职务关系·后台",
            "security": "职务关系·安保",
            "staff": "职务关系·工作人员",
            "fan": "外部关系·粉丝",
        }
        return label_map.get(cat, "职务关系")
    if not is_peer_entertainment_role(rel):
        return "普通关系"
    return str(rel.get("public_relation_state", rel.get("private_relation_state", "普通同期")))


def relationship_ui_summary(name: str, rel: Dict[str, Any], state: GameState) -> str:
    base = (
        f"{name}({rel.get('role', '未知')}): {public_relationship_label(rel, state)} / "
        f"友{rel.get('friendship')} 信{rel.get('trust')} 心动{rel.get('player_crush')} 模糊{rel.get('ambiguity')}"
    )
    if is_cp_eligible(rel, state):
        base += f" CP{rel.get('business_cp_level')}"
    else:
        if professional_romance_policy(rel, state) == "same_age_staff_high_risk":
            base += " 边界:同龄工作人员高风险"
        elif is_professional_relationship(rel):
            base += " 边界:职务"
        elif is_peer_entertainment_role(rel):
            base += f" 边界:年龄差>{cp_age_gap_limit(state)}"
        else:
            base += " 边界:不适用"
    return base


def relationship_category_for_role(role: str) -> str:
    cat = staff_role_category(role)
    if cat == "non_staff":
        return "peer"
    if cat in {"manager", "teacher", "production", "styling", "security", "staff"}:
        return f"professional_{cat}"
    if cat == "fan":
        return "fan"
    return "other"

def update_private_state(rel: Dict[str, Any], state: GameState) -> None:
    friendship = int(rel.get("friendship", 0))
    trust = int(rel.get("trust", 0))
    intimacy = int(rel.get("intimacy_comfort", 0))
    crush = int(rel.get("player_crush", 0))
    npc_romance = int(rel.get("npc_romantic_interest_hidden", 0))
    boundary = int(rel.get("boundary_clarity", 50))
    ambiguity = int(rel.get("ambiguity", 0))
    business = int(rel.get("business_cp_level", 0))

    if friendship < 25 and trust < 25:
        rel["private_relation_state"] = "普通同期"
    if friendship >= 35 and trust >= 35:
        rel["private_relation_state"] = "朋友"
    if friendship >= 60 and trust >= 55 and intimacy >= 45:
        rel["private_relation_state"] = "亲密朋友"

    if crush >= 35 and npc_romance < 35:
        rel["private_relation_state"] = "单方面心动"
    if crush >= 35 and friendship >= 55 and npc_romance < 35 and boundary >= 55:
        rel["private_relation_state"] = "友情被误读"
    if crush >= 45 and npc_romance >= 40 and boundary < 60 and ambiguity >= 35:
        rel["private_relation_state"] = "暧昧未确认"
    if crush >= 60 and npc_romance >= 55 and ambiguity >= 50:
        rel["private_relation_state"] = "互相心动但未确认"

    # 权力差异或未成年时，不允许推进为普通恋爱线。
    if is_power_imbalanced(rel) or state.age_context.get("is_minor", False):
        if rel["private_relation_state"] in {"暧昧未确认", "互相心动但未确认"}:
            rel["private_relation_state"] = "边界风险"
            rel["relationship_risk"] = clamp(int(rel.get("relationship_risk", 0)) + 10)

    if business >= 30 and bool(rel.get("cp_eligible", False)):
        rel["public_relation_state"] = "营业CP"
    elif is_power_imbalanced(rel):
        rel["public_relation_state"] = "职务关系"
    elif rel.get("private_relation_state") in {"亲密朋友", "暧昧未确认", "互相心动但未确认"}:
        rel["public_relation_state"] = "关系被关注"
    else:
        rel["public_relation_state"] = rel.get("private_relation_state", "普通同期")


def evaluate_relationship_system(state: GameState, action: str, fallback_target: str | None = None) -> Tuple[List[SystemEvent], Dict[str, int]]:
    ensure_default_relationships(state)

    events: List[SystemEvent] = []
    diff: Dict[str, int] = {}
    target_name = find_relationship_target(state, action) or fallback_target
    signals = classify_relationship_signals(action)
    if not signals or not target_name:
        return events, diff
    rel = state.relationships.setdefault(target_name, default_relationship(target_name))
    rel["professional_role_category"] = staff_role_category(str(rel.get("role", "")))
    rel["relationship_category"] = relationship_category_for_role(str(rel.get("role", "")))
    rel["role_viewpoint"] = role_viewpoint(str(rel.get("role", "")))
    rel["cp_eligible"] = is_cp_eligible(rel, state)
    rel.setdefault("professional_boundary_pressure", 0)
    if not rel["cp_eligible"]:
        rel["business_cp_level"] = 0
        rel["cp_fandom_pressure"] = 0
    signals = classify_relationship_signals(action)

    # 如果完全没有关系相关信号，仍不触发。
    if not signals:
        return events, diff

    rel.setdefault("last_signals", [])
    rel.setdefault("observed_clues", [])

    if "friendship" in signals:
        rel["friendship"] = clamp(int(rel.get("friendship", 0)) + 4)
        rel["trust"] = clamp(int(rel.get("trust", 0)) + 3)
        rel["intimacy_comfort"] = clamp(int(rel.get("intimacy_comfort", 0)) + 2)
        rel["care_memory"] = clamp(int(rel.get("care_memory", 0)) + 1)
        _add(diff, "团队关系.真实关系温度", 2)
        _add(diff, "心理状态.孤独感", -2)
        events.append(_event(
            "rel_friendship_signal",
            f"关系信号：友情照顾（{target_name}）",
            "这次互动首先被记录为友情和照顾记忆。亲密不自动等于恋爱。",
            "info",
            diff.copy(),
            [f"友情信号：{target_name}"],
        ))
        rel["last_signals"].append("友情信号")
        rel["observed_clues"].append("她/对方在这次互动中表现出照顾或支持。")

    if "romance" in signals:
        policy = professional_romance_policy(rel, state)

        if policy == "blocked_high_power":
            rel["player_crush"] = clamp(int(rel.get("player_crush", 0)) + 4)
            rel["professional_boundary_pressure"] = clamp(int(rel.get("professional_boundary_pressure", 0)) + 12)
            rel["relationship_risk"] = clamp(int(rel.get("relationship_risk", 0)) + 12)
            rel["boundary_clarity"] = clamp(int(rel.get("boundary_clarity", 50)) + 6)
            if hasattr(state, "inner_life"):
                state.inner_life["秘密重量"] = clamp(int(state.inner_life.get("秘密重量", 0)) + 4)
            events.append(_event(
                "rel_high_power_crush_boundary",
                f"职业边界：高权力差心动（{target_name}）",
                f"{target_name} 的角色视角是：{rel.get('role_viewpoint')} 这类关系不能按普通恋爱线推进。继续执意推进会增加公司风险、心理压力和职业边界风险。",
                "crisis",
                {"风险.公关危机风险": 4, "心理状态.精神压力": 4, "公司与合约.危机关注度": 4},
                [f"高权力差心动边界：{target_name}"],
            ))
            rel["last_signals"].append("高权力差边界")
            rel["observed_clues"].append("这段心动被系统归入职业边界和风险，而不是普通暧昧。")

        elif policy == "same_age_staff_high_risk":
            rel["player_crush"] = clamp(int(rel.get("player_crush", 0)) + 8)
            rel["player_expectation"] = clamp(int(rel.get("player_expectation", 0)) + 4)
            rel["player_misread_probability"] = clamp(int(rel.get("player_misread_probability", 0)) + 6)
            rel["ambiguity"] = clamp(int(rel.get("ambiguity", 0)) + 5)
            rel["professional_boundary_pressure"] = clamp(int(rel.get("professional_boundary_pressure", 0)) + 8)
            rel["relationship_risk"] = clamp(int(rel.get("relationship_risk", 0)) + 8)
            if hasattr(state, "inner_life"):
                state.inner_life["心动值"] = clamp(int(state.inner_life.get("心动值", 0)) + 5)
                state.inner_life["秘密重量"] = clamp(int(state.inner_life.get("秘密重量", 0)) + 3)
            events.append(_event(
                "rel_same_age_staff_crush_risk",
                f"职业边界：同龄工作人员心动（{target_name}）",
                f"你可以对同龄工作人员产生喜欢或在意，但对方仍处在工作身份里。{target_name} 的角色视角是：{rel.get('role_viewpoint')} 继续推进会带来职业边界、公司审视和舆论代价。",
                "warning",
                {"风险.恋爱风险": 3, "风险.公关危机风险": 2, "心理状态.精神压力": 2, "公司与合约.危机关注度": 2},
                [f"同龄工作人员心动风险：{target_name}"],
            ))
            rel["last_signals"].append("同龄工作人员心动")
            rel["observed_clues"].append("你对同龄工作人员产生在意，但这段关系被职业边界包围。")

        elif policy == "professional_boundary":
            rel["player_crush"] = clamp(int(rel.get("player_crush", 0)) + 5)
            rel["professional_boundary_pressure"] = clamp(int(rel.get("professional_boundary_pressure", 0)) + 8)
            rel["relationship_risk"] = clamp(int(rel.get("relationship_risk", 0)) + 8)
            events.append(_event(
                "rel_staff_crush_boundary",
                f"职业边界：工作人员心动（{target_name}）",
                f"{target_name} 是工作人员关系。即使年龄不构成绝对障碍，这也不是同龄练习生关系，不能进入 CP 或普通恋爱线。",
                "warning",
                {"风险.恋爱风险": 2, "心理状态.精神压力": 2},
                [f"工作人员心动边界：{target_name}"],
            ))
            rel["last_signals"].append("工作人员边界")

        else:
            rel["player_crush"] = clamp(int(rel.get("player_crush", 0)) + 8)
            rel["player_expectation"] = clamp(int(rel.get("player_expectation", 0)) + 5)
            rel["player_misread_probability"] = clamp(int(rel.get("player_misread_probability", 0)) + 4)
            rel["fear_of_ruining_friendship"] = clamp(int(rel.get("fear_of_ruining_friendship", 0)) + 2)
            rel["ambiguity"] = clamp(int(rel.get("ambiguity", 0)) + 4)
            if hasattr(state, "inner_life"):
                state.inner_life["心动值"] = clamp(int(state.inner_life.get("心动值", 0)) + 5)
                state.inner_life["秘密重量"] = clamp(int(state.inner_life.get("秘密重量", 0)) + 2)
            events.append(_event(
                "rel_romance_signal_player_side",
                f"关系信号：玩家心动（{target_name}）",
                "系统只记录玩家一侧的心动或在意。NPC 是否有浪漫兴趣仍然未知，不能直接写成恋爱成立。",
                "info",
                {"风险.恋爱风险": 1, "心理状态.精神压力": 1},
                [f"玩家心动线索：{target_name}"],
            ))
            rel["last_signals"].append("玩家心动")
            rel["observed_clues"].append("你开始在意对方的反应，但这还不是对方的回应。")

    if "boundary" in signals:
        rel["boundary_clarity"] = clamp(int(rel.get("boundary_clarity", 50)) + 8)
        rel["ambiguity"] = clamp(int(rel.get("ambiguity", 0)) - 8)
        rel["player_expectation"] = clamp(int(rel.get("player_expectation", 0)) - 5)
        events.append(_event(
            "rel_boundary_signal",
            f"关系信号：边界明确（{target_name}）",
            "对方或你自己把关系边界放清楚。它可能会带来失落，但能保护关系不被误读强行吞掉。",
            "info",
            {"心理状态.精神压力": 1, "风险.恋爱风险": -1},
            [f"边界信号：{target_name}"],
        ))
        rel["last_signals"].append("边界信号")
        rel["observed_clues"].append("关系边界变得更明确。")

    if "business_cp" in signals:
        if is_cp_eligible(rel, state):
            rel["business_cp_level"] = clamp(int(rel.get("business_cp_level", 0)) + 8)
            rel["cp_fandom_pressure"] = clamp(int(rel.get("cp_fandom_pressure", 0)) + 6)
            rel["relationship_risk"] = clamp(int(rel.get("relationship_risk", 0)) + 3)
            _add(diff, "粉丝与舆论.CP粉规模", 2)
            _add(diff, "粉丝与舆论.CP粉幻想强度", 4)
            _add(diff, "团队关系.营业疲劳", 2)
            events.append(_event(
                "rel_business_cp_signal",
                f"关系信号：营业 CP（{target_name}）",
                "镜头前亲密优先被记录为营业 CP 和外界解读，不直接等于真实浪漫关系。",
                "warning",
                diff.copy(),
                [f"营业CP信号：{target_name}"],
            ))
            rel["last_signals"].append("营业CP信号")
            rel["observed_clues"].append("粉丝或公司可能把这段互动当成 CP 素材。")
        else:
            rel["business_cp_level"] = 0
            rel["cp_fandom_pressure"] = 0
            rel["relationship_risk"] = clamp(int(rel.get("relationship_risk", 0)) + 6)
            _add(diff, "风险.公关危机风险", 2)
            events.append(_event(
                "rel_cp_ineligible_boundary",
                f"关系边界：不进入营业关系系统（{target_name}）",
                "营业关系只适用于同龄或近龄练习生、队友、同龄爱豆。经纪人、老师、工作人员、粉丝等职务或权力不对等关系只能按职业边界、公关误读或安全风险处理。",
                "warning",
                diff.copy(),
                [f"非营业关系对象：{target_name}"],
            ))
            rel["last_signals"].append("职业边界信号")
            rel["observed_clues"].append("这段关系被系统归入职务/边界关系，不进入营业关系计算。")

    if "risk" in signals:
        rel["relationship_risk"] = clamp(int(rel.get("relationship_risk", 0)) + 8)
        _add(diff, "风险.恋爱风险", 4)
        _add(diff, "风险.公关危机风险", 2)
        events.append(_event(
            "rel_public_risk_signal",
            f"关系信号：外界误读风险（{target_name}）",
            "这段关系被外界捕捉或误读的风险上升。关系越不清晰，风险越难处理。",
            "warning",
            diff.copy(),
            [f"关系外界误读风险：{target_name}"],
        ))
        rel["last_signals"].append("风险信号")

    if "rivalry" in signals:
        rel["rivalry"] = clamp(int(rel.get("rivalry", 0)) + 6)
        rel["friendship"] = clamp(int(rel.get("friendship", 0)) - 1)
        _add(diff, "团队关系.队内竞争度", 2)
        events.append(_event(
            "rel_rivalry_signal",
            f"关系信号：竞争（{target_name}）",
            "竞争不等于讨厌。它会影响关系温度，也可能推动彼此成长。",
            "info",
            diff.copy(),
            [f"竞争信号：{target_name}"],
        ))
        rel["last_signals"].append("竞争信号")

    # Minor hardening. High-power professional hardening has already been handled in the romance branch.
    if "romance" in signals and state.age_context.get("is_minor", False):
        rel["relationship_risk"] = clamp(int(rel.get("relationship_risk", 0)) + 15)
        rel["boundary_clarity"] = clamp(int(rel.get("boundary_clarity", 0)) + 10)
        events.append(_event(
            "rel_minor_boundary_ethics_warning",
            f"未成年关系边界警告（{target_name}）",
            "当前角色未成年，不能按正式恋爱线推进。系统将其归入边界和安全风险。",
            "crisis",
            {"风险.公关危机风险": 4, "心理状态.精神压力": 2},
            [f"未成年伦理边界风险：{target_name}"],
        ))

    # Ambiguity drift: only when friendship and player crush both high.
    if int(rel.get("friendship", 0)) >= 50 and int(rel.get("player_crush", 0)) >= 35:
        rel["ambiguity"] = clamp(int(rel.get("ambiguity", 0)) + 3)
        rel["fear_of_ruining_friendship"] = clamp(int(rel.get("fear_of_ruining_friendship", 0)) + 2)

    update_private_state(rel, state)

    # Keep signal list short.
    rel["last_signals"] = rel["last_signals"][-8:]
    rel["observed_clues"] = rel["observed_clues"][-8:]

    for _ev in events:
        _merge_event_diff(diff, _ev)

    return events, diff


def relationship_debug_summary(state: GameState) -> List[str]:
    ensure_default_relationships(state)
    return [relationship_ui_summary(name, rel, state) for name, rel in state.relationships.items()]
