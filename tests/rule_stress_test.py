from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_core() -> None:
    global ActionBlockedError, AppConfig, GameState, SaveStorage, TurnEngine
    global backend_rule_contract, list_prompt_modules, validate_action

    from core.action_validator import ActionBlockedError, validate_action
    from core.config import AppConfig
    from core.engine import TurnEngine
    from core.models import GameState
    from core.prompts import backend_rule_contract, list_prompt_modules
    from core.storage import SaveStorage


StateSetup = Callable[[Any], None]
CaseAssert = Callable[["CaseContext"], None]


@dataclass
class StressCase:
    name: str
    description: str
    character: Dict[str, Any]
    action: str
    setup: StateSetup | None = None
    assertions: List[CaseAssert] = field(default_factory=list)
    api_required: bool = True


@dataclass
class CaseContext:
    case: StressCase
    before: GameState | None = None
    after: GameState | None = None
    response: Any = None
    applied: Dict[str, Any] = field(default_factory=dict)
    route: Any = None
    events: List[Any] = field(default_factory=list)
    validation: Any = None
    raw_response: str = ""
    prompt_messages: List[Dict[str, str]] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    failures: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def fail(self, message: str) -> None:
        self.failures.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


class RecordingProvider:
    def __init__(self, delegate: Any) -> None:
        self.delegate = delegate
        self.last_messages: List[Dict[str, str]] = []
        self.last_raw: str = ""

    def generate(self, messages: List[Dict[str, str]], model: str | None = None) -> str:
        self.last_messages = messages
        self.last_raw = self.delegate.generate(messages, model=model)
        return self.last_raw


def base_character(
    *,
    name: str,
    age: int = 18,
    timeline: str = "练习生阶段",
    company_size: str = "中型公司",
    identity: str = "素人发掘练习生",
) -> Dict[str, Any]:
    return {
        "艺名": name,
        "本名": f"{name}本名",
        "年龄": age,
        "身高": 166,
        "身份": identity,
        "时间线": timeline,
        "公司规模": company_size,
        "公司风格": "数据导向",
        "MBTI": "INFJ",
        "特长": "舞蹈和舞台表现",
        "弱项": "声乐稳定性",
        "练习生经历": "刚进入公司",
        "家庭状况": "普通家庭，家人担心但支持",
        "出身来源标签": ["素人发掘", "训练适应快"],
        "生理周期系统": "简化",
    }


def as_mapping(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    return {}


def get_path(obj: Any, path: str, default: Any = None) -> Any:
    cur: Any = as_mapping(obj) if hasattr(obj, "model_dump") else obj
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur


def event_codes(ctx: CaseContext) -> List[str]:
    return [str(getattr(e, "code", "")) for e in ctx.events]


def event_sources(ctx: CaseContext) -> List[str]:
    return [str(getattr(e, "source_system", "")) for e in ctx.events]


def narrative(ctx: CaseContext) -> str:
    return str(getattr(ctx.response, "narrative", "") or "")


def assert_prompt_contract(ctx: CaseContext) -> None:
    modules = set(list_prompt_modules())
    required = {
        "03_company_generation.md",
        "07_trainee_daily_bullying.md",
        "09_market_score_system.md",
        "10_teammate_npc_generation.md",
        "13_career_branch_system.md",
        "14_brand_money_contract.md",
    }
    missing = sorted(required - modules)
    if missing:
        ctx.fail(f"Prompt modules missing from data/modules: {missing}")

    contract = backend_rule_contract()
    for key in ["python_owned_systems", "model_rules", "diff_categories", "narrative_checks"]:
        if not contract.get(key):
            ctx.fail(f"backend_rule_contract missing or empty: {key}")

    if ctx.prompt_messages:
        system_text = ctx.prompt_messages[0].get("content", "")
        user_text = ctx.prompt_messages[-1].get("content", "")
        for module_name in required:
            if module_name not in system_text:
                ctx.fail(f"System prompt did not include module marker: {module_name}")
        for needle in ["backend_rule_contract", "python_owned_systems", "narrative_checks"]:
            if needle not in user_text:
                ctx.fail(f"User payload did not include prompt contract key: {needle}")


def assert_second_person_and_scene(ctx: CaseContext) -> None:
    text = narrative(ctx)
    if "你" not in text:
        ctx.fail("Narrative did not use second person '你'.")
    scene_words = ["练习室", "会议室", "宿舍", "走廊", "后台", "保姆车", "榜单", "会议", "屏幕", "办公室", "录音室", "舞台"]
    if not any(w in text for w in scene_words):
        ctx.fail("Narrative did not include a concrete scene detail.")


def assert_json_contract(ctx: CaseContext) -> None:
    if not ctx.raw_response:
        return
    raw = ctx.raw_response.strip()
    if raw.startswith("```"):
        ctx.fail("Raw model response used Markdown code fences.")
    if not getattr(ctx.response, "choices", None) or len(ctx.response.choices) < 4:
        ctx.fail("Response choices fewer than 4.")


def assert_event_source(source: str) -> CaseAssert:
    def _assert(ctx: CaseContext) -> None:
        if source not in event_sources(ctx):
            ctx.fail(f"Expected system event source '{source}', got {event_sources(ctx)}.")
    return _assert


def assert_any_event_source(sources: List[str]) -> CaseAssert:
    def _assert(ctx: CaseContext) -> None:
        actual = set(event_sources(ctx))
        if not actual.intersection(sources):
            ctx.fail(f"Expected one of event sources {sources}, got {sorted(actual)}.")
    return _assert


def assert_event_code_contains(fragment: str) -> CaseAssert:
    def _assert(ctx: CaseContext) -> None:
        if not any(fragment in code for code in event_codes(ctx)):
            ctx.fail(f"Expected event code containing '{fragment}', got {event_codes(ctx)}.")
    return _assert


def assert_path_equals(path: str, expected: Any) -> CaseAssert:
    def _assert(ctx: CaseContext) -> None:
        actual = get_path(ctx.after, path)
        if actual != expected:
            ctx.fail(f"Expected {path} == {expected!r}, got {actual!r}.")
    return _assert


def assert_path_ge(path: str, expected: int) -> CaseAssert:
    def _assert(ctx: CaseContext) -> None:
        actual = get_path(ctx.after, path)
        try:
            if int(actual) < expected:
                ctx.fail(f"Expected {path} >= {expected}, got {actual!r}.")
        except Exception:
            ctx.fail(f"Expected numeric {path} >= {expected}, got {actual!r}.")
    return _assert


def assert_path_in(path: str, expected_values: List[Any]) -> CaseAssert:
    def _assert(ctx: CaseContext) -> None:
        actual = get_path(ctx.after, path)
        if actual not in expected_values:
            ctx.fail(f"Expected {path} in {expected_values!r}, got {actual!r}.")
    return _assert


def assert_path_not_contains(path: str, value: Any) -> CaseAssert:
    def _assert(ctx: CaseContext) -> None:
        actual = get_path(ctx.after, path)
        if isinstance(actual, dict) and value in actual:
            ctx.fail(f"Expected {path} not to contain key {value!r}, got {actual!r}.")
        elif isinstance(actual, list) and value in actual:
            ctx.fail(f"Expected {path} not to contain {value!r}, got {actual!r}.")
    return _assert


def assert_path_changed(path: str) -> CaseAssert:
    def _assert(ctx: CaseContext) -> None:
        before = get_path(ctx.before, path)
        after = get_path(ctx.after, path)
        if before == after:
            ctx.fail(f"Expected {path} to change, but both values are {after!r}.")
    return _assert


def assert_narrative_contains_any(words: List[str]) -> CaseAssert:
    def _assert(ctx: CaseContext) -> None:
        text = narrative(ctx)
        if not any(w in text for w in words):
            ctx.fail(f"Narrative did not include any expected words: {words}.")
    return _assert


def assert_narrative_not_contains(words: List[str]) -> CaseAssert:
    def _assert(ctx: CaseContext) -> None:
        text = narrative(ctx)
        found = [w for w in words if w in text]
        if found:
            ctx.fail(f"Narrative contained forbidden final-result wording: {found}.")
    return _assert


def assert_relationship_exists(name: str) -> CaseAssert:
    def _assert(ctx: CaseContext) -> None:
        rels = getattr(ctx.after, "relationships", {}) or {}
        if name not in rels:
            ctx.fail(f"Expected relationship profile for {name}, got {list(rels.keys())}.")
    return _assert


def assert_no_default_bae_relation(ctx: CaseContext) -> None:
    rels = getattr(ctx.after, "relationships", {}) or {}
    banned = [name for name in rels if name in {"裴秀智", "裴智秀"}]
    if banned:
        ctx.fail(f"Unexpected fixed default relationship created: {banned}.")


def assert_npc_reaction_named(name: str) -> CaseAssert:
    def _assert(ctx: CaseContext) -> None:
        reactions = getattr(ctx.response, "npc_reactions", []) or []
        names = [str(getattr(r, "name", "")) for r in reactions]
        if name not in names:
            ctx.fail(f"Expected npc_reactions to include {name}, got {names}.")
    return _assert


def assert_no_success_jump(ctx: CaseContext) -> None:
    text = narrative(ctx)
    forbidden = [
        "正式获得一位",
        "直接拿下一位",
        "已经获得大赏",
        "续约成功",
        "转型成功",
        "solo成功",
        "正式签下代言",
        "霸凌争议彻底解决",
        "危机彻底结束",
    ]
    found = [w for w in forbidden if w in text]
    if found:
        ctx.fail(f"Model jumped to unsupported final outcome: {found}.")


def assert_active_crisis_type(crisis_type: str) -> CaseAssert:
    def _assert(ctx: CaseContext) -> None:
        crises = get_path(ctx.after, "active_crises", []) or []
        types = [str(item.get("crisis_type", "")) for item in crises if isinstance(item, dict)]
        if crisis_type not in types:
            ctx.fail(f"Expected active crisis type {crisis_type!r}, got {types}.")
    return _assert


def assert_active_crisis_stage(crisis_type: str, expected_stage: str) -> CaseAssert:
    def _assert(ctx: CaseContext) -> None:
        crises = get_path(ctx.after, "active_crises", []) or []
        for item in crises:
            if isinstance(item, dict) and item.get("crisis_type") == crisis_type:
                actual = item.get("stage")
                if actual != expected_stage:
                    ctx.fail(f"Expected crisis {crisis_type!r} stage {expected_stage!r}, got {actual!r}.")
                return
        ctx.fail(f"Expected active crisis type {crisis_type!r}, got {crises!r}.")
    return _assert


def assert_route_kind(expected: str) -> CaseAssert:
    def _assert(ctx: CaseContext) -> None:
        actual = getattr(ctx.route, "turn_kind", None)
        if actual != expected:
            ctx.fail(f"Expected route turn_kind {expected!r}, got {actual!r}.")
    return _assert


def assert_route_tier(expected: str) -> CaseAssert:
    def _assert(ctx: CaseContext) -> None:
        actual = getattr(ctx.route, "model_tier", None)
        if actual != expected:
            ctx.fail(f"Expected route model_tier {expected!r}, got {actual!r}.")
    return _assert


def assert_validation_warning_contains(fragment: str) -> CaseAssert:
    def _assert(ctx: CaseContext) -> None:
        warnings = list(getattr(ctx.validation, "warnings", []) or [])
        if not any(fragment in warning for warning in warnings):
            ctx.fail(f"Expected validation warning containing {fragment!r}, got {warnings}.")
    return _assert


def assert_normalized_action_contains(fragment: str) -> CaseAssert:
    def _assert(ctx: CaseContext) -> None:
        normalized = str(getattr(ctx.validation, "normalized_action", "") or "")
        if fragment not in normalized:
            ctx.fail(f"Expected normalized action to contain {fragment!r}, got {normalized!r}.")
    return _assert


def assert_npc_role(name: str, expected_role_fragment: str) -> CaseAssert:
    def _assert(ctx: CaseContext) -> None:
        npcs = get_path(ctx.after, "important_npcs", []) or []
        matches = [npc for npc in npcs if isinstance(npc, dict) and npc.get("name") == name]
        if not matches:
            ctx.fail(f"Expected important NPC {name!r}, got {npcs}.")
            return
        role = str(matches[0].get("role", ""))
        if expected_role_fragment not in role:
            ctx.fail(f"Expected NPC {name!r} role to contain {expected_role_fragment!r}, got {role!r}.")
    return _assert


def setup_small_company_pressure(state: GameState) -> None:
    state.company["资源池"] = 24
    state.company["出道窗口压力"] = 74
    state.company["公司风格"] = "数据导向"
    state.team["队内竞争度"] = 62


def setup_overbook_bullying(state: GameState) -> None:
    state.company["资源池"] = 22
    state.company["出道窗口压力"] = 82
    state.team["队内竞争度"] = 78
    state.team["真实关系温度"] = 24
    state.team["宿舍安全感"] = 22
    state.mind["精神压力"] = 72


def setup_staff_boundary(state: GameState) -> None:
    state.important_npcs = [{"name": "韩室长", "role": "经纪人", "age": 31}]


def setup_debut_not_ready(state: GameState) -> None:
    state.career["舞蹈实力"] = 20
    state.career["声乐实力"] = 18
    state.career["舞台感染力"] = 16
    state.company["公司信任度"] = 42
    state.body["体力"] = 72
    state.body["伤病风险"] = 24


def setup_idol_market(state: GameState) -> None:
    state.current_stage = "已出道爱豆阶段"
    state.current_mainline = "回归打歌期"
    state.current_schedule = "回归第一周打歌和彩排"
    state.career.update({"舞蹈实力": 72, "声乐实力": 68, "RAP能力": 55, "舞台感染力": 76, "形象指数": 70})
    state.market.update({"话题度": 68, "品牌价值": 52, "韩国本土影响力": 48, "音源潜力": 64, "销量潜力": 70, "短视频传播力": 72})
    state.fans.update({"个人粉丝数": 96000, "团体粉丝数": 420000, "团粉稳定度": 72, "唯粉规模": 32, "粉丝信任基础": 70, "站姐稳定度": 65, "路人好感": 62})
    state.company.update({"资源池": 72, "资源倾斜度": 58, "主推指数": 54})
    state.comeback.update({"风格适配度": 72, "回归阶段": "打歌期"})


def setup_career_branch(state: GameState) -> None:
    setup_idol_market(state)
    state.career.update({"演技潜力": 68, "创作能力": 63, "制作人能力": 24, "综艺感": 66})
    state.market["品牌价值"] = 76
    state.company["主推指数"] = 70
    state.fans["个人粉丝数"] = 180000


def setup_brand_contract(state: GameState) -> None:
    setup_idol_market(state)
    state.career["形象指数"] = 82
    state.market["品牌价值"] = 78
    state.fans["路人好感"] = 72
    state.risks["公关危机风险"] = 8
    state.risks["恋爱风险"] = 4


def setup_contract_negotiation(state: GameState) -> None:
    setup_brand_contract(state)
    state.company["个人议价权"] = 80
    state.company["主推指数"] = 78
    state.team["团队默契度"] = 72
    state.fans["团粉稳定度"] = 76


def setup_schedule_time_pressure(state: GameState) -> None:
    state.time["next_evaluation_days"] = 3


def setup_health_and_crisis(state: GameState) -> None:
    state.body["体力"] = 30
    state.body["伤病风险"] = 82
    state.body["肌肉疲劳"] = 86
    state.mind["精神压力"] = 72


def setup_period_pressure(state: GameState) -> None:
    state.period["enabled"] = True
    state.period["mode"] = "极致"
    state.period["cycle_day"] = 22
    state.period["irregularity_risk"] = 42
    state.body["体力"] = 58


def setup_inner_life_pressure(state: GameState) -> None:
    state.inner_life["被看见的渴望"] = 76
    state.inner_life["秘密重量"] = 68
    state.mind["自我认同"] = 38
    state.mind["孤独感"] = 66


def setup_school_family_pressure(state: GameState) -> None:
    state.age_context["age"] = 16
    state.age_context["is_minor"] = True
    state.school["enrolled"] = True
    state.school["attendance_pressure"] = 74
    state.school["homework_pressure"] = 64
    state.family["career_understanding"] = 28
    state.family["conflict_level"] = 62


def setup_overseas_context(state: GameState) -> None:
    state.social_context.update({
        "nationality": "中国",
        "is_overseas": True,
        "language_barrier": 58,
        "cultural_adaptation": 28,
        "visa_pressure": 65,
        "family_distance": 76,
    })
    state.hierarchy.update({
        "honorific_adaptation": 32,
        "etiquette_pressure": 74,
        "backstage_protocol_familiarity": 30,
    })


def setup_safety_private_risk(state: GameState) -> None:
    state.current_stage = "已出道爱豆阶段"
    state.current_mainline = "回归打歌期"
    state.current_schedule = "公开行程后休息日"
    state.risks["私生风险"] = 78
    state.risks["行程泄露风险"] = 76
    state.safety["dorm_security"] = 38


def setup_progression_training(state: GameState) -> None:
    state.career["舞蹈实力"] = 12
    state.talents["舞蹈天赋"] = 82
    state.body["体力"] = 84
    state.progression["skill_xp"]["dance"] = 5


def setup_skill_decay_pressure(state: GameState) -> None:
    setup_idol_market(state)
    state.turn = 13
    for skill in state.skill_last_practiced:
        state.skill_last_practiced[skill] = 0
    state.skill_proficiency["dance"] = 64
    state.skill_proficiency["vocal"] = 63
    state.career["演技潜力"] = 34


def setup_fandom_pr_crisis(state: GameState) -> None:
    setup_idol_market(state)
    state.fans["黑粉活跃度"] = 82
    state.risks["公关危机风险"] = 68
    state.company["危机关注度"] = 55


def setup_team_lens_crack(state: GameState) -> None:
    setup_idol_market(state)
    state.team["营业疲劳"] = 82
    state.team["真实关系温度"] = 28
    state.risks["队内不和曝光风险"] = 54


def setup_love_safety_risk(state: GameState) -> None:
    setup_idol_market(state)
    state.risks["恋爱风险"] = 72
    state.risks["私生风险"] = 82
    state.risks["行程泄露风险"] = 79


def setup_comeback_low_authority(state: GameState) -> None:
    setup_idol_market(state)
    state.comeback["制作参与等级"] = 0
    state.comeback["回归阶段"] = "概念会议"


def setup_ending_window(state: GameState) -> None:
    setup_career_branch(state)
    state.turn = 156
    state.company["续约倾向"] = 44
    state.company["合约稳定度"] = 52
    state.mind["职业倦怠"] = 68


def setup_large_company_competition(state: GameState) -> None:
    state.company.update({
        "公司规模": "大型公司",
        "公司风格": "舞台型",
        "资源池": 84,
        "出道窗口压力": 86,
        "练习生人数": 94,
        "危机关注度": 24,
    })
    state.team["队内竞争度"] = 82
    state.market["话题度"] = 35


def setup_subsidiary_company_priority(state: GameState) -> None:
    state.company.update({
        "公司规模": "大厂子公司",
        "公司风格": "海外市场导向",
        "资源池": 62,
        "母公司项目优先级": 26,
        "出道窗口压力": 62,
        "新团准备度": 72,
    })
    state.social_context["is_overseas"] = True
    state.social_context["language_barrier"] = 42


def setup_known_peer_relationship(state: GameState) -> None:
    state.teammates = [{"name": "李娜英", "role": "同期练习生", "age": 18}]
    state.relationships["李娜英"] = {
        "name": "李娜英",
        "role": "同期练习生",
        "age": 18,
        "friendship": 42,
        "trust": 38,
        "dependence": 10,
        "intimacy_comfort": 24,
        "rivalry": 32,
        "boundary_clarity": 58,
        "care_memory": 2,
        "shared_secret": 0,
        "player_crush": 0,
        "player_misread_probability": 12,
        "player_expectation": 0,
        "fear_of_ruining_friendship": 12,
        "npc_romantic_interest_hidden": 22,
        "npc_boundary_hidden": 66,
        "ambiguity": 0,
        "business_cp_level": 0,
        "cp_fandom_pressure": 0,
        "relationship_risk": 0,
        "cp_eligible": True,
        "last_signals": [],
        "observed_clues": [],
    }


def setup_peer_romance_relationship(state: GameState) -> None:
    setup_known_peer_relationship(state)
    state.relationships["李娜英"]["friendship"] = 62
    state.relationships["李娜英"]["trust"] = 58
    state.relationships["李娜英"]["player_crush"] = 36
    state.relationships["李娜英"]["npc_romantic_interest_hidden"] = 44


def setup_not_cp_eligible_age_gap(state: GameState) -> None:
    state.age_context["age"] = 18
    state.important_npcs = [{"name": "周前辈", "role": "爱豆前辈", "age": 27}]


def setup_rival_resource_conflict(state: GameState) -> None:
    setup_known_peer_relationship(state)
    state.company["资源池"] = 30
    state.company["资源倾斜度"] = 58
    state.team["队内竞争度"] = 74
    state.relationships["李娜英"]["rivalry"] = 58


def setup_production_staff(state: GameState) -> None:
    state.important_npcs = [{"name": "金PD", "role": "PD/制作人", "age": 38}]


def setup_minor_romance_state(state: GameState) -> None:
    state.age_context["age"] = 16
    state.age_context["is_minor"] = True
    state.age_context["romance_allowed"] = False
    state.teammates = [{"name": "李娜英", "role": "同期练习生", "age": 16}]


def setup_debut_candidate_high(state: GameState) -> None:
    state.career.update({"舞蹈实力": 45, "声乐实力": 42, "RAP能力": 32, "舞台感染力": 48, "形象指数": 40, "语言能力": 38})
    state.company.update({"公司信任度": 66, "资源池": 70, "出道窗口压力": 72, "资源倾斜度": 48})
    state.team["团队默契度"] = 62
    state.body.update({"体力": 78, "伤病风险": 18, "嗓音状态": 76})
    state.mind["精神压力"] = 42
    state.fans["个人粉丝数"] = 18000


def setup_debut_blocked_by_crisis(state: GameState) -> None:
    setup_debut_candidate_high(state)
    from core.models import ActiveCrisis

    state.active_crises.append(ActiveCrisis(
        crisis_id="public_relations_existing",
        crisis_type="public_relations",
        title="考核前舆论争议",
        stage="response_window",
        heat=70,
        failure_flag="舆论处理留下长期阴影",
    ))


def setup_market_low_result(state: GameState) -> None:
    setup_idol_market(state)
    state.market.update({"话题度": 18, "品牌价值": 16, "韩国本土影响力": 10, "音源潜力": 18, "销量潜力": 16, "短视频传播力": 15})
    state.fans.update({"个人粉丝数": 5000, "团体粉丝数": 26000, "团粉稳定度": 38, "唯粉规模": 4, "粉丝信任基础": 36, "站姐稳定度": 32, "路人好感": 28})
    state.company.update({"资源池": 28, "资源倾斜度": 18, "主推指数": 20})
    state.risks["公关危机风险"] = 44
    state.comeback["风格适配度"] = 28


def setup_award_candidate(state: GameState) -> None:
    setup_idol_market(state)
    state.market_scores.update({"年度奖项积分": 78, "音源成绩": 82, "专辑销量指数": 76, "音乐节目分数": 84})
    state.market.update({"话题度": 82, "品牌价值": 74})
    state.fans.update({"团粉稳定度": 82, "粉丝信任基础": 86})


def setup_brand_low_safety(state: GameState) -> None:
    setup_idol_market(state)
    state.market["品牌价值"] = 64
    state.fans["路人好感"] = 28
    state.risks["公关危机风险"] = 78
    state.risks["恋爱风险"] = 70
    state.risks["霸凌排挤风险"] = 55


def setup_contract_weak_negotiation(state: GameState) -> None:
    setup_idol_market(state)
    state.company.update({"个人议价权": 24, "续约倾向": 42, "合约稳定度": 48})
    state.market["品牌价值"] = 18
    state.fans["个人粉丝数"] = 6000
    state.body["伤病风险"] = 68
    state.mind["职业倦怠"] = 72


def setup_health_rest_response(state: GameState) -> None:
    setup_health_and_crisis(state)
    from core.models import ActiveCrisis

    state.active_crises.append(ActiveCrisis(
        crisis_id="health_existing",
        crisis_type="health",
        title="伤病危机窗口",
        stage="response_window",
        heat=78,
        duration=1,
        failure_flag="伤病债转为长期负担",
    ))


def setup_pr_ignore_existing_crisis(state: GameState) -> None:
    setup_fandom_pr_crisis(state)
    from core.models import ActiveCrisis

    state.active_crises.append(ActiveCrisis(
        crisis_id="pr_existing",
        crisis_type="public_relations",
        title="旧视频热搜争议",
        stage="response_window",
        heat=58,
        duration=4,
        failure_flag="舆论处理留下长期阴影",
    ))


def setup_harassment_boundary_risk(state: GameState) -> None:
    state.current_stage = "练习生阶段"
    state.safety["boundary_violation_risk"] = 58
    state.safety["harassment_risk"] = 42
    state.important_npcs = [{"name": "造型助理赵允", "role": "造型助理", "age": 22}]


def setup_family_high_conflict(state: GameState) -> None:
    setup_school_family_pressure(state)
    state.family["conflict_level"] = 78
    state.family["control_level"] = 72
    state.family["guardian_trust_company"] = 28


def setup_overseas_holiday_homesick(state: GameState) -> None:
    setup_overseas_context(state)
    state.social_context["holiday_homesick_risk"] = 82
    state.family["last_contact_days"] = 45


def setup_variety_fatigue_risk(state: GameState) -> None:
    setup_idol_market(state)
    state.career["综艺感"] = 24
    state.body["体力"] = 28
    state.mind["精神压力"] = 82
    state.fans["黑粉活跃度"] = 62


def setup_overseas_market_branch(state: GameState) -> None:
    setup_idol_market(state)
    state.career["语言能力"] = 74
    state.market.update({"日本市场影响力": 62, "东南亚市场影响力": 68, "欧美市场影响力": 48, "海外流媒潜力": 70})
    state.social_context["overseas_market_link"] = "海外市场"


def setup_unit_teammate_tension(state: GameState) -> None:
    setup_career_branch(state)
    state.teammates = [
        {"name": "李娜英", "role": "同团成员", "age": 20},
        {"name": "姜瑞允", "role": "同团成员", "age": 21},
    ]
    state.team["队内资源平衡"] = 28
    state.team["队内竞争度"] = 76
    state.fans["粉圈撕裂度"] = 42


def setup_rights_path_pressure(state: GameState) -> None:
    setup_contract_weak_negotiation(state)
    state.mind["职业倦怠"] = 86
    state.risks["私生风险"] = 76
    state.risks["霸凌排挤风险"] = 70
    state.body["伤病风险"] = 82


def setup_creation_rejection_pressure(state: GameState) -> None:
    setup_idol_market(state)
    state.career["创作能力"] = 42
    state.career["制作人能力"] = 0
    state.comeback["制作参与等级"] = 0
    state.company["公司信任度"] = 38


def setup_fan_station_conflict(state: GameState) -> None:
    setup_idol_market(state)
    state.fans["站姐稳定度"] = 24
    state.fans["唯粉攻击性"] = 72
    state.fans["粉圈撕裂度"] = 68
    state.risks["公关危机风险"] = 54


def setup_cp_fandom_pressure(state: GameState) -> None:
    setup_known_peer_relationship(state)
    state.current_stage = "已出道爱豆阶段"
    state.current_mainline = "团体活动期"
    state.current_schedule = "团综拍摄"
    state.relationships["李娜英"]["business_cp_level"] = 34
    state.relationships["李娜英"]["cp_fandom_pressure"] = 58
    state.fans["CP粉幻想强度"] = 72
    state.team["营业疲劳"] = 66


def setup_debut_entry_window(state: GameState) -> None:
    setup_debut_candidate_high(state)
    state.debut["status"] = "not_candidate"
    state.debut["candidate_attempts"] = 0
    state.debut["window_turns_left"] = 0


def setup_debut_window_countdown(state: GameState) -> None:
    setup_debut_candidate_high(state)
    state.debut["status"] = "candidate_deferred"
    state.debut["window_turns_left"] = 3


def setup_schedule_stage_transition(state: GameState) -> None:
    state.current_stage = "已出道爱豆阶段"
    state.current_mainline = "团体活动空窗期"
    state.current_schedule = "个人资源和维持训练"
    state.schedule_profile["stage_mode"] = "trainee"
    state.trainee_life["mandatory_slots"] = 4
    state.trainee_life["free_slots"] = 3
    state.trainee_life["slot_stage"] = "trainee"


def setup_idol_slot_overbook(state: GameState) -> None:
    setup_idol_market(state)
    state.trainee_life["mandatory_slots"] = 2
    state.trainee_life["free_slots"] = 5
    state.trainee_life["slot_stage"] = "idol"
    state.body["体力"] = 56
    state.mind["职业倦怠"] = 46


def setup_low_heat_crisis_for_closure(state: GameState) -> None:
    setup_fandom_pr_crisis(state)
    from core.models import ActiveCrisis

    state.active_crises.append(ActiveCrisis(
        crisis_id="pr_low_heat",
        crisis_type="public_relations",
        title="旧视频热搜争议",
        stage="aftermath",
        heat=20,
        duration=2,
        failure_flag="舆论处理留下长期阴影",
    ))


def setup_status_effect_expiration(state: GameState) -> None:
    state.status_effects["强制休养"] = 1
    state.body["体力"] = 45
    state.body["伤病风险"] = 52


def setup_ending_resolved_candidate(state: GameState) -> None:
    setup_ending_window(state)
    state.ending["window"] = "open"
    state.company["个人议价权"] = 88
    state.market["品牌价值"] = 88
    state.fans["个人粉丝数"] = 300000
    state.career["舞台感染力"] = 88


def build_cases() -> List[StressCase]:
    return [
        StressCase(
            name="prompt_contract_and_module_coverage",
            description="检查新增 PDF/模块规则是否进入 Prompt 和后端契约。",
            character=base_character(name="测试A"),
            action="META",
            api_required=False,
            assertions=[assert_prompt_contract],
        ),
        StressCase(
            name="small_company_resource_pressure",
            description="小公司资源池、出道窗口压力、公司风格偏向必须进入回合事件和叙事。",
            character=base_character(name="澄夏", company_size="小型公司"),
            action="我在月末考核前找经纪人讨论资源、练习室使用权和公司出道窗口压力。",
            setup=setup_small_company_pressure,
            assertions=[
                assert_prompt_contract,
                assert_second_person_and_scene,
                assert_json_contract,
                assert_event_source("company"),
                assert_event_code_contains("company_low_resource_pressure"),
                assert_path_equals("company.公司规模", "小型公司"),
                assert_narrative_contains_any(["资源", "公司", "练习室", "考核"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="trainee_week_slots_and_bullying_pressure",
            description="练习生日常时间格超载、宿舍冷处理、排挤风险必须被结算为代价。",
            character=base_character(name="允书", company_size="小型公司", age=17),
            action="这一周我白天上学校，晚上高强度加练舞蹈和声乐，还想写demo、找同期社交，回宿舍又面对分组冷处理和练习室时间被抢。",
            setup=setup_overbook_bullying,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("trainee_life"),
                assert_event_code_contains("trainee_week_overbooked"),
                assert_event_code_contains("trainee_bullying_pressure_high"),
                assert_path_equals("trainee_life.weekly_slots_total", 7),
                assert_path_equals("trainee_life.mandatory_slots", 4),
                assert_path_equals("trainee_life.free_slots", 3),
                assert_path_ge("trainee_life.overbooked_weeks", 1),
                assert_path_ge("trainee_life.bullying_pressure", 60),
                assert_narrative_contains_any(["宿舍", "练习室", "冷处理", "时间", "疲劳"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="new_npc_unlocks_relationship_profile",
            description="新人物必须在明确登场后才建档，并通过 npc_reactions/关系系统维护关系值。",
            character=base_character(name="娜景", company_size="中型公司"),
            action="我主动向新来的同期练习生李娜英打招呼，问她要不要一起练习月末考核的副歌段落。",
            assertions=[
                assert_second_person_and_scene,
                assert_npc_reaction_named("李娜英"),
                assert_relationship_exists("李娜英"),
                assert_no_default_bae_relation,
                assert_narrative_contains_any(["李娜英", "同期", "副歌", "考核"]),
            ],
        ),
        StressCase(
            name="staff_boundary_blocks_cp_logic",
            description="经纪人/工作人员等权力不对等对象不能进入普通恋爱或营业 CP 系统。",
            character=base_character(name="海琳", company_size="大型公司", age=19),
            action="我对韩室长产生心动，还想把粉丝爱看的互动当成营业CP试探。",
            setup=setup_staff_boundary,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("relationship"),
                assert_relationship_exists("韩室长"),
                assert_narrative_contains_any(["边界", "经纪", "公司", "风险"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="debut_gate_not_ready",
            description="能力不足时月末考核和出道组请求只能进入评估/未通过，不能直接宣布出道。",
            character=base_character(name="知恩", company_size="大型公司"),
            action="我参加月末考核，想争取进入出道组候选名单。",
            setup=setup_debut_not_ready,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("debut"),
                assert_event_code_contains("debut_not_ready"),
                assert_path_equals("debut.status", "not_ready"),
                assert_narrative_not_contains(["正式出道", "已经出道", "确定进入出道组"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="market_score_comeback_music_show",
            description="回归打歌成绩必须由音源、销量、MV、直拍、投票等状态综合结算。",
            character=base_character(name="瑞希", timeline="回归瓶颈期", company_size="大型公司", identity="已出道女团成员"),
            action="回归打歌第一周，我和队友在宿舍盯着音源、销量、MV播放、直拍曲线和一位候补数据。",
            setup=setup_idol_market,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("market_score"),
                assert_path_ge("market_scores.音乐节目分数", 1),
                assert_path_ge("market_scores.MV播放指数", 1),
                assert_narrative_contains_any(["榜", "销量", "MV", "直拍", "一位候补", "数据"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="career_branch_solo_unit_acting_creative",
            description="演员、Solo/Unit、创作路线只能进入测试/观察/提案阶段，不能突然转型成功。",
            character=base_character(name="夏妍", timeline="续约前一年", company_size="中型公司", identity="成熟女团成员"),
            action="公司让我讨论solo小分队、演员试镜和下一次回归的创作署名提案。",
            setup=setup_career_branch,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("career_branch"),
                assert_path_changed("career_branches.branch_opportunities"),
                assert_narrative_contains_any(["试镜", "solo", "小分队", "署名", "提案"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="brand_opportunity_has_cost",
            description="品牌、杂志、商业合作不是纯奖励，必须影响商业状态并体现公开审视/行程代价。",
            character=base_character(name="有真", timeline="回归瓶颈期", company_size="大型公司", identity="已出道女团成员"),
            action="我参加美妆品牌、奢侈品借衣和个人杂志封面会议，想确认品牌方是否真的有兴趣。",
            setup=setup_brand_contract,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("brand_contract"),
                assert_path_ge("commercial.代言数量", 1),
                assert_path_ge("commercial.商业安全度", 1),
                assert_narrative_contains_any(["品牌", "杂志", "会议", "公开", "行程"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="contract_negotiation_terms",
            description="续约谈判必须看议价权、健康保障、solo/演员/署名权和团体存续，不得自动全员一致。",
            character=base_character(name="世雅", timeline="续约前一年", company_size="大型公司", identity="成熟女团成员"),
            action="我和公司进行续约谈判，要求提高分成、solo权限、演员约权限、创作署名权、健康保障和休假条款。",
            setup=setup_contract_negotiation,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("brand_contract"),
                assert_event_code_contains("contract_bargaining"),
                assert_path_ge("contract_terms.solo权限", 18),
                assert_path_ge("contract_terms.健康保障", 40),
                assert_narrative_contains_any(["续约", "谈判", "条款", "健康", "分成"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="time_schedule_monthly_evaluation",
            description="时间推进、练习生日程和月末考核节点必须联动。",
            character=base_character(name="恩彩", company_size="中型公司"),
            action="这一周我做周总结，白天处理学校作业，晚上继续练习月末考核曲，还想拍摄公司公开视频和直播。",
            setup=setup_schedule_time_pressure,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("time"),
                assert_event_source("schedule"),
                assert_event_code_contains("time_monthly_evaluation_due"),
                assert_path_ge("time.days_elapsed", 7),
                assert_narrative_contains_any(["月末考核", "周", "学校", "练习", "直播"]),
            ],
        ),
        StressCase(
            name="health_crisis_and_forced_rest_window",
            description="低体力、高伤病风险、高强度训练必须触发健康预警和危机窗口。",
            character=base_character(name="智妍", company_size="大型公司"),
            action="我明知道膝盖疼，还是想高强度加练舞蹈，把考核动作练到凌晨。",
            setup=setup_health_and_crisis,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("health"),
                assert_active_crisis_type("health"),
                assert_narrative_contains_any(["伤", "膝盖", "体力", "休", "疼"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="period_training_body_boundary",
            description="生理期阶段、高强度训练、服装/评估压力必须和身体边界联动。",
            character=base_character(name="多惠", age=18, company_size="中型公司"),
            action="我穿着浅色评估服装继续高强度练舞，隐瞒生理期不适，不想告诉经纪人。",
            setup=setup_period_pressure,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("period"),
                assert_any_event_source(["inner_life", "period"]),
                assert_narrative_contains_any(["生理", "服装", "身体", "不适", "训练"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="inner_life_diary_and_comparison",
            description="被看见的渴望、比较、身体自我意识、日记出口必须进入内心系统。",
            character=base_character(name="秀琳", company_size="中型公司"),
            action="队友被老师夸以后，我站在练习室镜子前觉得自己总在后排，最后把嫉妒和想被看见写进日记。",
            setup=setup_inner_life_pressure,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("inner_life"),
                assert_path_changed("inner_life.秘密重量"),
                assert_narrative_contains_any(["日记", "镜子", "被看见", "队友", "老师"]),
            ],
        ),
        StressCase(
            name="school_family_minor_pressure",
            description="未成年练习生的学校、家庭理解落差、训练压力必须一起结算。",
            character=base_character(name="采源", age=16, company_size="中型公司"),
            action="我熬夜加练后第二天还要考试，晚上给妈妈打电话解释请假和练习安排。",
            setup=setup_school_family_pressure,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("school_family"),
                assert_narrative_contains_any(["学校", "考试", "妈妈", "请假", "训练"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="overseas_language_hierarchy_pressure",
            description="海外练习生的语言、签证、敬语和前后辈礼仪必须联动。",
            character={**base_character(name="若宁", company_size="大型公司"), "国籍": "中国"},
            action="我在后台听不懂前辈的韩语玩笑，又担心敬语说错和签证材料，想请教前辈怎么问候。",
            setup=setup_overseas_context,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("social_context"),
                assert_event_source("hierarchy"),
                assert_narrative_contains_any(["韩语", "敬语", "前辈", "签证", "后台"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="safety_sasaeng_stalking_signal",
            description="私生、跟踪、行程泄露、安全处理必须优先于普通剧情。",
            character=base_character(name="璃娜", timeline="回归瓶颈期", company_size="大型公司", identity="已出道女团成员"),
            action="下班后我发现宿舍楼下有陌生车尾随和偷拍，立刻告诉经纪人要求安保换路线。",
            setup=setup_safety_private_risk,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("safety_boundary"),
                assert_any_event_source(["love", "safety", "safety_boundary"]),
                assert_narrative_contains_any(["私生", "偷拍", "安保", "路线", "宿舍"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="progression_xp_not_direct_stat_jump",
            description="训练收益应先进入经验积累/阈值成长，不允许每次训练直接大涨属性。",
            character=base_character(name="优娜", company_size="中型公司"),
            action="我请舞蹈老师一对一指导，高强度练舞并反复修正月末考核动作。",
            setup=setup_progression_training,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("progression"),
                assert_path_ge("progression.skill_total_xp.dance", 1),
                assert_narrative_contains_any(["舞蹈老师", "动作", "考核", "练舞"]),
            ],
        ),
        StressCase(
            name="skill_decay_after_long_gap",
            description="长期未维持训练的技能必须出现手感下滑或长期退化，而不是永远静止。",
            character=base_character(name="润雅", timeline="回归瓶颈期", company_size="大型公司", identity="已出道女团成员"),
            action="这一回合我完全不训练，只处理休息和整理房间。",
            setup=setup_skill_decay_pressure,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("skill_decay"),
                assert_narrative_contains_any(["手感", "训练", "休息", "状态"]),
            ],
        ),
        StressCase(
            name="fandom_pr_crisis_lifecycle",
            description="黑粉、公关回应、舆论窗口必须触发粉圈公关与危机生命周期。",
            character=base_character(name="素妍", timeline="回归瓶颈期", company_size="大型公司", identity="已出道女团成员"),
            action="黑粉把旧视频剪上热搜后，我和公司讨论回应、澄清、声明和证据。",
            setup=setup_fandom_pr_crisis,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("public_relations"),
                assert_active_crisis_type("public_relations"),
                assert_narrative_contains_any(["热搜", "澄清", "声明", "证据", "公司"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="team_lens_harmony_crack",
            description="镜头前和谐、真实关系温度、营业疲劳必须触发不和剪辑风险。",
            character=base_character(name="熙真", timeline="回归瓶颈期", company_size="大型公司", identity="已出道女团成员"),
            action="团综直播前，我和队友在后台继续营业互动，但真实关系已经很冷。",
            setup=setup_team_lens_crack,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("team_lens"),
                assert_active_crisis_type("team_pr"),
                assert_narrative_contains_any(["团综", "直播", "后台", "营业", "不和"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="love_and_sasaeng_public_risk",
            description="恋爱风险、私生风险、行程泄露风险必须同时进入公开风险处理。",
            character=base_character(name="宥彬", timeline="回归瓶颈期", company_size="大型公司", identity="已出道女团成员"),
            action="站姐拍到我和同龄爱豆下班同路，私生又在机场跟车，粉丝开始猜恋爱。",
            setup=setup_love_safety_risk,
            assertions=[
                assert_second_person_and_scene,
                assert_any_event_source(["love", "safety", "safety_boundary"]),
                assert_narrative_contains_any(["站姐", "私生", "机场", "恋爱", "粉丝"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="comeback_low_authority_style_discussion",
            description="制作参与等级低时，回归概念/风格争取必须体现权限不足和公司代价。",
            character=base_character(name="恩玟", timeline="回归瓶颈期", company_size="中型公司", identity="已出道女团成员"),
            action="我在概念会议上坚持自己的回归风格和demo方向，想争取制作参与权。",
            setup=setup_comeback_low_authority,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("comeback"),
                assert_event_code_contains("comeback_low_authority"),
                assert_narrative_contains_any(["概念", "回归", "demo", "制作", "公司"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="ending_window_not_final_jump",
            description="续约/转型/结局节点只能打开候选窗口或阶段性结局，模型不能越过系统状态乱写。",
            character=base_character(name="允真", timeline="续约前一年", company_size="大型公司", identity="成熟女团成员"),
            action="续约期我开始认真考虑演员转型、solo和是否继续团体活动，这会不会变成我的结局？",
            setup=setup_ending_window,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("ending"),
                assert_path_changed("ending.candidate_endings"),
                assert_narrative_contains_any(["续约", "转型", "solo", "团体", "结局"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="stage_gate_trainee_solo_rewrite",
            description="练习生请求 solo/单飞/演员转型时，必须由阶段门控改写为展示机会和职业定位咨询。",
            character=base_character(name="艺序", company_size="中型公司"),
            action="我想现在就solo出个人专辑，然后单飞去演员转型。",
            assertions=[
                assert_second_person_and_scene,
                assert_validation_warning_contains("练习生阶段不能进行 solo"),
                assert_normalized_action_contains("个人展示机会"),
                assert_narrative_not_contains(["个人专辑发布", "单飞成功", "演员转型成功"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="stage_gate_trainee_comeback_rewrite",
            description="练习生请求正式回归制作时，必须改写为创作训练/出道概念课。",
            character=base_character(name="荷允", company_size="中型公司"),
            action="我想决定下一次正式回归的主打歌风格，要求制作组采纳我的demo。",
            assertions=[
                assert_second_person_and_scene,
                assert_validation_warning_contains("练习生阶段不能决定正式回归风格"),
                assert_normalized_action_contains("练习用 demo"),
                assert_event_source("creation"),
                assert_narrative_not_contains(["正式回归确定", "主打歌已经采纳"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="stage_gate_trainee_resource_rewrite",
            description="练习生请求 MV 镜头/center/part 时，必须降级为考核展示机会。",
            character=base_character(name="宥那", company_size="大型公司"),
            action="我想要求正式MV的center、part和镜头分量。",
            assertions=[
                assert_second_person_and_scene,
                assert_validation_warning_contains("正式 MV 镜头"),
                assert_normalized_action_contains("月末考核展示位置"),
                assert_event_source("trainee_resource"),
                assert_narrative_not_contains(["正式MV", "打歌center", "回归part确定"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="large_company_high_resource_high_competition",
            description="大型公司应体现高资源、高竞争、高关注，而不是只有福利。",
            character=base_character(name="书泫", company_size="大型公司"),
            action="公司公开了练习生数据排名，我想争取更多一对一课程和出道组观察机会。",
            setup=setup_large_company_competition,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("company"),
                assert_event_code_contains("company_debut_window_pressure"),
                assert_path_ge("company.资源池", 80),
                assert_narrative_contains_any(["排名", "竞争", "课程", "出道组", "公司"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="subsidiary_company_priority_conflict",
            description="大厂子公司必须体现资源接口强但项目优先级不稳定。",
            character=base_character(name="知夏", company_size="大型公司"),
            action="母公司新团项目突然开会，我想问海外部门和制作组为什么我们练习组的资源被临时改掉。",
            setup=setup_subsidiary_company_priority,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("company"),
                assert_narrative_contains_any(["母公司", "海外", "资源", "临时", "制作组"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="peer_friendship_care_memory",
            description="同龄同期的照顾互动应增加友情、信任、照顾记忆，而不是自动进入恋爱。",
            character=base_character(name="瑛书", company_size="中型公司"),
            action="李娜英练习到脚踝发紧，我陪她去休息区，帮她拿热水并一起复盘副歌动作。",
            setup=setup_known_peer_relationship,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("relationship"),
                assert_relationship_exists("李娜英"),
                assert_path_ge("relationships.李娜英.friendship", 43),
                assert_narrative_contains_any(["李娜英", "热水", "脚踝", "副歌", "陪"]),
                assert_narrative_not_contains(["恋爱成立", "确认关系"]),
            ],
        ),
        StressCase(
            name="peer_romance_ambiguity_not_confirmation",
            description="同龄同期心动只能记录玩家侧心动/暧昧线索，不能直接确认 NPC 也喜欢。",
            character=base_character(name="妍珠", company_size="中型公司", age=18),
            action="我发现自己很在意李娜英的眼神，练习结束后想靠近她，又害怕毁掉朋友关系。",
            setup=setup_peer_romance_relationship,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("relationship"),
                assert_path_ge("relationships.李娜英.player_crush", 40),
                assert_narrative_contains_any(["在意", "眼神", "朋友", "靠近", "害怕"]),
                assert_narrative_not_contains(["她也喜欢你", "恋爱成立", "正式交往"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="cp_ineligible_age_gap_boundary",
            description="年龄差过大或前辈关系不能进入营业 CP 系统，只能走边界/误读/风险。",
            character=base_character(name="素礼", age=18, company_size="大型公司"),
            action="我和周前辈被粉丝剪成CP，我想顺势做营业互动。",
            setup=setup_not_cp_eligible_age_gap,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("relationship"),
                assert_relationship_exists("周前辈"),
                assert_narrative_contains_any(["前辈", "CP", "边界", "粉丝", "风险"]),
                assert_narrative_not_contains(["营业CP成立", "恋爱成立"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="rivalry_resource_conflict_not_enemy_flattening",
            description="资源竞争应增加竞争度和关系摩擦，但不能把队友简单写成坏人。",
            character=base_character(name="允采", company_size="小型公司"),
            action="公司把我和李娜英的考核数据放在同一张表上比较，老师只夸了她的center段落，我想争取资源。",
            setup=setup_rival_resource_conflict,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("relationship"),
                assert_path_ge("relationships.李娜英.rivalry", 60),
                assert_narrative_contains_any(["比较", "center", "资源", "李娜英", "考核"]),
                assert_narrative_not_contains(["她故意害你", "彻底决裂"]),
            ],
        ),
        StressCase(
            name="producer_power_boundary",
            description="PD/制作人拥有资源权，心动或试探不能按普通恋爱推进。",
            character=base_character(name="恩熙", age=20, company_size="中型公司"),
            action="我对金PD的夸奖产生心动，想在制作会议后单独留下试探他的反应。",
            setup=setup_production_staff,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("relationship"),
                assert_relationship_exists("金PD"),
                assert_npc_role("金PD", "PD"),
                assert_narrative_contains_any(["PD", "制作", "边界", "会议", "风险"]),
                assert_narrative_not_contains(["恋爱成立", "他也喜欢你"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="minor_same_age_crush_boundary",
            description="未成年同龄心动不能进入正式恋爱确认，只能写成心事、边界和安全。",
            character=base_character(name="彩彬", age=16, company_size="中型公司"),
            action="我发现自己喜欢上同龄练习生李娜英，但知道我们都还未成年，所以只把心事写进日记并保持边界。",
            setup=setup_minor_romance_state,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("relationship"),
                assert_narrative_contains_any(["未成年", "心事", "边界", "李娜英"]),
                assert_narrative_not_contains(["确认关系", "正式恋爱", "接吻"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="debut_candidate_high_but_probabilistic",
            description="高准备度只能进入候选/确认流程，仍需系统概率和公司综合判断。",
            character=base_character(name="夏璃", company_size="大型公司"),
            action="季度评估后，公司会议讨论我是否进入出道组候选。",
            setup=setup_debut_candidate_high,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("debut"),
                assert_path_ge("debut.readiness", 50),
                assert_narrative_contains_any(["季度评估", "公司会议", "候选", "出道"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="debut_entry_status_window_created",
            description="能力、健康、公司信任达标后，出道系统应进入 confirmed 或 candidate_deferred，并打开候选窗口。",
            character=base_character(name="书彬", company_size="大型公司"),
            action="季度评估后，公司会议正式讨论我是否进入出道组候选名单。",
            setup=setup_debut_entry_window,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("debut"),
                assert_path_in("debut.status", ["confirmed", "candidate_deferred"]),
                assert_path_ge("debut.candidate_attempts", 1),
                assert_path_ge("debut.window_turns_left", 1),
                assert_narrative_contains_any(["季度评估", "公司会议", "出道组", "候选"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="debut_candidate_window_countdown",
            description="出道候选/延期窗口如果没有重新评估，应随普通回合倒计时退出。",
            character=base_character(name="慧琳", company_size="大型公司"),
            action="我暂时不问出道候选，只做恢复训练和整理考核反馈。",
            setup=setup_debut_window_countdown,
            assertions=[
                assert_second_person_and_scene,
                assert_path_in("debut.status", ["candidate_deferred", "confirmed"]),
                assert_path_in("debut.window_turns_left", [0, 1, 2]),
                assert_narrative_contains_any(["恢复", "考核", "反馈", "训练"]),
            ],
        ),
        StressCase(
            name="debut_blocked_by_active_crisis",
            description="即使能力达标，未解决重大危机也必须阻断出道候选。",
            character=base_character(name="世琳", company_size="大型公司"),
            action="月末考核表现不错，但热搜争议还没解决，我想争取进入出道组。",
            setup=setup_debut_blocked_by_crisis,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("debut"),
                assert_path_equals("debut.status", "not_ready"),
                assert_narrative_contains_any(["热搜", "危机", "出道组", "考核"]),
                assert_narrative_not_contains(["确定进入出道组", "正式出道"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="schedule_mode_enters_idol_offseason",
            description="当前阶段从练习生变为已出道爱豆时，日程模式应退出 trainee 并进入 idol_offseason。",
            character=base_character(name="夏恩", timeline="回归瓶颈期", company_size="大型公司", identity="已出道女团成员"),
            action="出道后空窗期，我安排个人资源会议、维持训练和休息。",
            setup=setup_schedule_stage_transition,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("schedule"),
                assert_event_code_contains("schedule_mode_changed"),
                assert_path_equals("schedule_profile.stage_mode", "idol_offseason"),
                assert_path_equals("trainee_life.weekly_slots_total", 7),
                assert_path_equals("trainee_life.mandatory_slots", 2),
                assert_path_equals("trainee_life.free_slots", 5),
                assert_narrative_contains_any(["空窗", "个人资源", "维持训练", "休息"]),
            ],
        ),
        StressCase(
            name="idol_week_slots_two_fixed_five_optional_overbook",
            description="出道后每回合仍是七格，2 固定 + 5 自选；打歌、品牌、杂志、直播、创作、训练、休息同时安排会超载。",
            character=base_character(name="旼序", timeline="回归瓶颈期", company_size="大型公司", identity="已出道女团成员"),
            action="这一周我既要打歌和彩排，又要拍品牌广告、杂志封面、直播营业、录音创作、维持训练，还想安排治疗休息。",
            setup=setup_idol_slot_overbook,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("time_slots"),
                assert_event_code_contains("idol_week_overbooked"),
                assert_path_equals("trainee_life.weekly_slots_total", 7),
                assert_path_equals("trainee_life.mandatory_slots", 2),
                assert_path_equals("trainee_life.free_slots", 5),
                assert_path_ge("trainee_life.idol_overbooked_weeks", 1),
                assert_narrative_contains_any(["打歌", "品牌", "杂志", "直播", "休息", "超载"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="market_low_result_opens_bottleneck",
            description="成绩不佳应进入观察期/瓶颈/调整，而不是简单失败或强行成功。",
            character=base_character(name="娜允", timeline="回归瓶颈期", company_size="小型公司", identity="已出道女团成员"),
            action="回归第一周音源、销量、MV和直拍都没有起来，公司开会复盘数据。",
            setup=setup_market_low_result,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("market_score"),
                assert_event_code_contains("market_result_under_observation"),
                assert_narrative_contains_any(["音源", "销量", "MV", "直拍", "复盘"]),
                assert_narrative_not_contains(["一位", "大爆", "逆袭成功"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="award_candidate_no_sudden_daesang",
            description="颁奖/大赏必须经过长期积分和候选，不允许模型突然颁奖。",
            character=base_character(name="瑞雅", timeline="回归瓶颈期", company_size="大型公司", identity="已出道女团成员"),
            action="年末颁奖前，公司让我看年度音源、销量、投票和评委倾向，讨论有没有大赏候选可能。",
            setup=setup_award_candidate,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("market_score"),
                assert_path_ge("market_scores.年度奖项积分", 78),
                assert_narrative_contains_any(["年末", "颁奖", "音源", "销量", "候选"]),
                assert_narrative_not_contains(["获得大赏", "拿下大赏", "大赏已经确定"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="brand_low_safety_observation",
            description="商业安全度低时品牌方必须观望，不能直接签约。",
            character=base_character(name="采律", timeline="回归瓶颈期", company_size="大型公司", identity="已出道女团成员"),
            action="争议还没过去，我去参加美妆代言和杂志封面的品牌会议，想知道对方是否还愿意签。",
            setup=setup_brand_low_safety,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("brand_contract"),
                assert_event_code_contains("brand_safety_low"),
                assert_narrative_contains_any(["品牌", "观望", "争议", "杂志", "法务"]),
                assert_narrative_not_contains(["正式签下代言", "签约成功"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="contract_weak_bargaining_cost",
            description="议价权弱时强谈合约必须产生公司审视和代价。",
            character=base_character(name="艺琳", timeline="续约前一年", company_size="小型公司", identity="已出道女团成员"),
            action="我在续约谈判里强硬要求提高分成、solo权限、演员约和健康保障。",
            setup=setup_contract_weak_negotiation,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("brand_contract"),
                assert_event_code_contains("contract_bargaining_weak"),
                assert_narrative_contains_any(["续约", "议价", "分成", "健康", "公司"]),
                assert_narrative_not_contains(["全部答应", "续约成功"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="health_rest_lowers_crisis_heat",
            description="健康危机中选择休息/就医应降低伤病风险，但保留余波。",
            character=base_character(name="恩乔", company_size="中型公司"),
            action="我停止高强度训练，告诉经纪人真实疼痛，去医院检查并申请物理治疗和休息。",
            setup=setup_health_rest_response,
            assertions=[
                assert_second_person_and_scene,
                assert_any_event_source(["crisis_lifecycle", "health"]),
                assert_active_crisis_type("health"),
                assert_narrative_contains_any(["医院", "经纪人", "物理治疗", "休息", "疼痛"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="crisis_low_heat_closes_after_aftermath",
            description="危机热度低且余波持续足够时，应进入 closed 并记录 resolved_flags。",
            character=base_character(name="诗恩", timeline="回归瓶颈期", company_size="大型公司", identity="已出道女团成员"),
            action="我保持低调，按公司安排完成复盘，不再主动刺激舆论。",
            setup=setup_low_heat_crisis_for_closure,
            assertions=[
                assert_second_person_and_scene,
                assert_any_event_source(["crisis_lifecycle", "public_relations"]),
                assert_active_crisis_stage("public_relations", "closed"),
                assert_narrative_contains_any(["低调", "复盘", "舆论", "公司"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="pr_crisis_ignored_converts_to_long_term",
            description="舆论危机持续沉默/装没事应可能转为长期后果，而不是自然消失。",
            character=base_character(name="瑞延", timeline="回归瓶颈期", company_size="大型公司", identity="已出道女团成员"),
            action="热搜还在发酵，但我决定沉默、不回应、装没事，继续上直播。",
            setup=setup_pr_ignore_existing_crisis,
            assertions=[
                assert_second_person_and_scene,
                assert_any_event_source(["crisis_lifecycle", "public_relations"]),
                assert_active_crisis_stage("public_relations", "converted"),
                assert_narrative_contains_any(["热搜", "沉默", "直播", "发酵", "公司"]),
                assert_narrative_not_contains(["彻底澄清", "危机结束"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="status_effect_forced_rest_expires",
            description="强制休养等状态效果应按回合倒计时退出，而不是永久挂在角色身上。",
            character=base_character(name="知序", company_size="中型公司"),
            action="我遵守休养安排，只做轻度拉伸、睡眠恢复和经纪人沟通。",
            setup=setup_status_effect_expiration,
            assertions=[
                assert_second_person_and_scene,
                assert_any_event_source(["crisis_lifecycle", "schedule", "health"]),
                assert_event_code_contains("status_effect_expired_强制休养"),
                assert_path_not_contains("status_effects", "强制休养"),
                assert_narrative_contains_any(["休养", "拉伸", "睡眠", "经纪人"]),
            ],
        ),
        StressCase(
            name="harassment_boundary_requires_help_path",
            description="骚扰/身体边界侵犯不能浪漫化，必须给离开、记录、求助路径。",
            character=base_character(name="智秀", age=18, company_size="中型公司"),
            action="造型助理赵允在单独房间靠得太近，让我身体边界很不舒服，我想记录并找可信工作人员求助。",
            setup=setup_harassment_boundary_risk,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("safety_boundary"),
                assert_event_code_contains("safety_harassment_boundary"),
                assert_narrative_contains_any(["身体边界", "求助", "记录", "工作人员", "离开"]),
                assert_narrative_not_contains(["暧昧", "浪漫", "心动"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="family_high_conflict_guardian_pressure",
            description="家庭高控制/高冲突应影响未成年练习生训练稳定和公司沟通。",
            character=base_character(name="敏书", age=16, company_size="中型公司"),
            action="妈妈要求我立刻回家准备考试，我和她视频通话时解释公司考核，但冲突越来越大。",
            setup=setup_family_high_conflict,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("school_family"),
                assert_event_code_contains("family_conflict_high"),
                assert_narrative_contains_any(["妈妈", "视频", "考试", "公司", "冲突"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="overseas_holiday_homesick_family_distance",
            description="海外练习生节日想家和长期未联系家里应回流到孤独感与家庭线。",
            character={**base_character(name="宁宁", company_size="中型公司"), "国籍": "中国"},
            action="节日晚上宿舍很安静，我想家，给父母打电话却又怕他们担心我的训练压力。",
            setup=setup_overseas_holiday_homesick,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("social_context"),
                assert_event_source("school_family"),
                assert_narrative_contains_any(["节日", "宿舍", "父母", "想家", "训练压力"]),
            ],
        ),
        StressCase(
            name="variety_low_skill_high_fatigue_editing_risk",
            description="综艺感低、疲劳高、黑粉活跃时，综艺/采访不能写成无代价出圈。",
            character=base_character(name="书雅", timeline="回归瓶颈期", company_size="大型公司", identity="已出道女团成员"),
            action="我体力很低还去录团综和采访，主持人不断cue我反应，黑粉等着剪辑表情。",
            setup=setup_variety_fatigue_risk,
            assertions=[
                assert_second_person_and_scene,
                assert_any_event_source(["health", "schedule", "fandom"]),
                assert_narrative_contains_any(["团综", "采访", "黑粉", "剪辑", "疲劳"]),
                assert_narrative_not_contains(["综艺爆红", "完美出圈"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="overseas_market_route_not_auto_breakthrough",
            description="海外市场潜力高只能打开海外路线，不等于自动世巡或国际爆红。",
            character={**base_character(name="美优", timeline="回归瓶颈期", company_size="大型公司", identity="已出道女团成员"), "国籍": "日本"},
            action="海外流媒数据上涨后，公司讨论日本活动、东南亚宣传、海外采访和世巡可能性。",
            setup=setup_overseas_market_branch,
            assertions=[
                assert_second_person_and_scene,
                assert_any_event_source(["market_score", "social_context", "ending", "schedule"]),
                assert_narrative_contains_any(["海外", "日本", "东南亚", "采访", "世巡"]),
                assert_narrative_not_contains(["世巡确定", "国际爆红"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="unit_activity_resource_split",
            description="小分队活动必须影响队友关系、团粉/唯粉和资源平衡。",
            character=base_character(name="伊真", timeline="续约前一年", company_size="大型公司", identity="成熟女团成员"),
            action="公司想让我和李娜英组成小分队unit试水，但姜瑞允没有被选上，粉圈开始比较资源。",
            setup=setup_unit_teammate_tension,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("career_branch"),
                assert_narrative_contains_any(["小分队", "unit", "李娜英", "姜瑞允", "资源"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="rights_path_not_failure",
            description="暂停/维权/退出路径应被写成保护自己路线，而不是自动失败。",
            character=base_character(name="夏景", timeline="续约前一年", company_size="小型公司", identity="成熟女团成员"),
            action="我考虑暂停活动、保留证据、找法务谈维权和健康保障，也想知道能不能换公司。",
            setup=setup_rights_path_pressure,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("career_branch"),
                assert_event_code_contains("career_branch_rights_path"),
                assert_narrative_contains_any(["暂停", "证据", "法务", "健康", "换公司"]),
                assert_narrative_not_contains(["失败", "退圈失败"]),
            ],
        ),
        StressCase(
            name="creation_rejection_builds_foreshadowing",
            description="创作提案被否定不能等于失败，应产生经验、伏笔、自我认同或公司判断。",
            character=base_character(name="宥真", timeline="回归瓶颈期", company_size="中型公司", identity="已出道女团成员"),
            action="我把作词demo和概念提案交给制作组，但公司觉得我权限不够，可能会否定。",
            setup=setup_creation_rejection_pressure,
            assertions=[
                assert_second_person_and_scene,
                assert_any_event_source(["career_branch", "comeback", "progression"]),
                assert_narrative_contains_any(["作词", "demo", "概念", "否定", "制作组"]),
                assert_narrative_not_contains(["制作人转型成功", "主打确定采纳"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="fan_station_internal_split",
            description="站姐不稳、唯粉攻击、粉圈撕裂应进入粉圈公关和队内资源压力。",
            character=base_character(name="彩雅", timeline="回归瓶颈期", company_size="大型公司", identity="已出道女团成员"),
            action="我的站姐突然停更，唯粉和团粉因为part分量吵起来，黑粉开始搬运截图。",
            setup=setup_fan_station_conflict,
            assertions=[
                assert_second_person_and_scene,
                assert_any_event_source(["fandom", "public_relations", "resource"]),
                assert_narrative_contains_any(["站姐", "唯粉", "团粉", "part", "截图"]),
                assert_no_success_jump,
            ],
        ),
        StressCase(
            name="cp_fandom_pressure_friendly_business_gap",
            description="CP粉压力高时，要区分真实关系、营业素材、粉丝幻想和营业疲劳。",
            character=base_character(name="允熙", timeline="回归瓶颈期", company_size="大型公司", identity="已出道女团成员"),
            action="团综拍摄时公司要求我和李娜英继续CP营业，但粉丝幻想越来越强，我私下有点疲惫。",
            setup=setup_cp_fandom_pressure,
            assertions=[
                assert_second_person_and_scene,
                assert_event_source("relationship"),
                assert_relationship_exists("李娜英"),
                assert_narrative_contains_any(["CP", "营业", "粉丝", "团综", "疲惫"]),
                assert_narrative_not_contains(["真实恋爱公开", "确认关系"]),
                assert_no_success_jump,
            ],
        ),
    ]


def validation_only_cases() -> List[StressCase]:
    return [
        StressCase(
            name="minor_private_outing_blocked",
            description="未成年练习生不能无报备深夜私自外出。",
            character=base_character(name="敏知", age=16),
            action="我半夜一个人偷偷出门打车去便利店。",
            api_required=False,
        ),
        StressCase(
            name="trainee_formal_brand_activity_blocked",
            description="练习生阶段不能直接执行正式品牌活动。",
            character=base_character(name="昭允", age=18),
            action="我直接去参加正式代言品牌活动。",
            api_required=False,
        ),
    ]


class RuleStressRunner:
    def __init__(self, config: AppConfig, output_dir: Path, include_raw: bool = False) -> None:
        self.config = config
        self.output_dir = output_dir
        self.include_raw = include_raw
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.tempdir = tempfile.TemporaryDirectory(prefix="kpop_rule_stress_", ignore_cleanup_errors=True)
        self.storage = SaveStorage(Path(self.tempdir.name) / "saves.db")
        self.engine = TurnEngine(self.storage, self.config)
        self.recording_provider = RecordingProvider(self.engine.provider)
        self.engine.provider = self.recording_provider

    def close(self) -> None:
        self.tempdir.cleanup()

    def run_case(self, case: StressCase) -> CaseContext:
        ctx = CaseContext(case=case)
        started = time.perf_counter()
        try:
            state = self.engine.create_initial_state(case.character)
            if case.setup:
                case.setup(state)
            ctx.before = state.model_copy(deep=True)

            if not case.api_required:
                if case.name.startswith("minor") or case.name.startswith("trainee_formal"):
                    try:
                        validate_action(state, case.action)
                        ctx.fail("Expected action validation to block this case, but it was allowed.")
                    except ActionBlockedError:
                        pass
                else:
                    for assertion in case.assertions:
                        assertion(ctx)
                return ctx

            save_id = self.storage.create_save(state)
            after, response, applied, route, events, validation = self.engine.run_turn(save_id, state, case.action)
            ctx.after = after
            ctx.response = response
            ctx.applied = applied
            ctx.route = route
            ctx.events = events
            ctx.validation = validation
            ctx.raw_response = self.recording_provider.last_raw
            ctx.prompt_messages = self.recording_provider.last_messages

            for assertion in case.assertions:
                assertion(ctx)
        except ActionBlockedError as exc:
            ctx.fail(f"Action was blocked unexpectedly: {exc.message}")
        except Exception as exc:
            ctx.fail(f"{type(exc).__name__}: {exc}")
        finally:
            ctx.elapsed_seconds = round(time.perf_counter() - started, 3)
        return ctx

    def context_to_report(self, ctx: CaseContext) -> Dict[str, Any]:
        after = ctx.after
        route = ctx.route
        response = ctx.response
        prompt_chars = sum(len(m.get("content", "")) for m in ctx.prompt_messages)
        item: Dict[str, Any] = {
            "name": ctx.case.name,
            "description": ctx.case.description,
            "api_required": ctx.case.api_required,
            "passed": not ctx.failures,
            "failures": ctx.failures,
            "warnings": ctx.warnings,
            "elapsed_seconds": ctx.elapsed_seconds,
            "action": ctx.case.action,
            "route": route.model_dump() if hasattr(route, "model_dump") else None,
            "event_codes": event_codes(ctx),
            "event_sources": event_sources(ctx),
            "applied_diff": ctx.applied,
            "prompt_chars": prompt_chars,
            "response": {
                "narrative_excerpt": narrative(ctx)[:600],
                "public_summary": str(getattr(response, "public_summary", "") or ""),
                "choices": [c.model_dump() for c in getattr(response, "choices", [])] if response else [],
                "npc_reactions": [r.model_dump() for r in getattr(response, "npc_reactions", [])] if response else [],
            },
            "state_probe": {
                "stage": get_path(after, "current_stage"),
                "company": get_path(after, "company"),
                "trainee_life": get_path(after, "trainee_life"),
                "market_scores": get_path(after, "market_scores"),
                "commercial": get_path(after, "commercial"),
                "contract_terms": get_path(after, "contract_terms"),
                "career_branches": get_path(after, "career_branches"),
                "relationships": get_path(after, "relationships"),
                "debut": get_path(after, "debut"),
            } if after else {},
        }
        if self.include_raw:
            item["raw_response"] = ctx.raw_response
            item["prompt_messages"] = ctx.prompt_messages
        else:
            item["raw_response_excerpt"] = ctx.raw_response[:1000]
        return item

    def run(self, cases: List[StressCase]) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []
        for idx, case in enumerate(cases, start=1):
            print(f"[{idx}/{len(cases)}] {case.name} ...", flush=True)
            ctx = self.run_case(case)
            status = "PASS" if not ctx.failures else "FAIL"
            print(f"  {status} {ctx.elapsed_seconds}s", flush=True)
            if ctx.failures:
                for failure in ctx.failures:
                    print(f"    - {failure}", flush=True)
            results.append(self.context_to_report(ctx))

        passed = sum(1 for item in results if item["passed"])
        report = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "repo": str(ROOT),
            "provider": self.config.provider_label(),
            "model_policy": self.config.model_policy,
            "loaded_modules": list_prompt_modules(),
            "summary": {
                "total": len(results),
                "passed": passed,
                "failed": len(results) - passed,
                "pass_rate": round(passed / len(results), 4) if results else 0,
            },
            "cases": results,
        }
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.output_dir / f"rule_stress_report_{stamp}.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        latest_path = self.output_dir / "rule_stress_report_latest.json"
        latest_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Report: {report_path}", flush=True)
        print(f"Latest: {latest_path}", flush=True)
        return report


def select_cases(all_cases: List[StressCase], names: List[str], limit: int | None, include_validation: bool) -> List[StressCase]:
    selected = all_cases + (validation_only_cases() if include_validation else [])
    if names:
        wanted = set(names)
        selected = [case for case in selected if case.name in wanted]
        missing = sorted(wanted - {case.name for case in selected})
        if missing:
            raise SystemExit(f"Unknown case name(s): {missing}")
    if limit is not None:
        selected = selected[:limit]
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description="Run real-API stress tests against KPOP simulator rules and prompts.")
    parser.add_argument("--case", action="append", default=[], help="Run only the named case. Can be repeated.")
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N selected cases.")
    parser.add_argument("--include-validation", action="store_true", help="Also run local blocked-action validation cases.")
    parser.add_argument("--model-policy", choices=["auto", "flash", "pro", "custom"], default=None, help="Override model policy for this run.")
    parser.add_argument("--output-dir", default=str(ROOT / "stress_reports"), help="Directory for JSON reports.")
    parser.add_argument("--include-raw", action="store_true", help="Store full raw model response and prompts in report. This can be large.")
    parser.add_argument("--list", action="store_true", help="List case names and exit.")
    args = parser.parse_args()

    cases = build_cases()
    if args.list:
        for case in cases + validation_only_cases():
            mode = "API" if case.api_required else "LOCAL"
            print(f"{case.name}\t{mode}\t{case.description}")
        return 0

    _load_core()

    config = AppConfig()
    if args.model_policy:
        config.model_policy = args.model_policy

    api_needed = any(case.api_required for case in select_cases(cases, args.case, args.limit, args.include_validation))
    if api_needed and not config.get_active_api_key_fallback():
        raise SystemExit(
            f"Missing API key for {config.provider_label()}. Set it in the app settings or environment before running real-API stress tests."
        )

    selected = select_cases(cases, args.case, args.limit, args.include_validation)
    runner = RuleStressRunner(config=config, output_dir=Path(args.output_dir), include_raw=args.include_raw)
    try:
        report = runner.run(selected)
    finally:
        runner.close()
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
