from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.action_validator import ActionBlockedError
from core.config import AppConfig
from core.engine import TurnEngine
from core.models import GameState
from core.prompts import list_prompt_modules
from core.storage import SaveStorage


StateSetup = Callable[[GameState], None]


@dataclass
class JourneyStep:
    name: str
    action: str
    description: str = ""
    expect_blocked: bool = False
    expect_route_kinds: set[str] = field(default_factory=set)
    expect_event_sources: set[str] = field(default_factory=set)
    expect_event_codes: set[str] = field(default_factory=set)
    expect_event_code_fragments: list[str] = field(default_factory=list)
    expect_applied_keys: set[str] = field(default_factory=set)
    expect_state_paths: dict[str, Any] = field(default_factory=dict)
    expect_state_path_changed: set[str] = field(default_factory=set)
    expect_relationships: set[str] = field(default_factory=set)
    expect_turn_duration_days: int | None = None
    expect_prompt_weekly_contract: bool | None = None
    narrative_focus: str = ""
    narrative_any: list[str] = field(default_factory=list)
    narrative_none: list[str] = field(default_factory=list)


@dataclass
class PlayerJourney:
    name: str
    description: str
    character: dict[str, Any]
    setup: StateSetup | None
    steps: list[JourneyStep]


@dataclass
class RecordingProvider:
    delegate: Any
    last_messages: list[dict[str, str]] = field(default_factory=list)
    last_raw: str = ""

    def generate(self, messages: list[dict[str, str]], model: str | None = None) -> str:
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
    nationality: str = "韩国",
) -> dict[str, Any]:
    return {
        "艺名": name,
        "本名": f"{name}本名",
        "年龄": age,
        "身高": 166,
        "身份": identity,
        "时间线": timeline,
        "公司规模": company_size,
        "公司风格": "数据导向",
        "国籍": nationality,
        "MBTI": "INFJ",
        "特长": "舞蹈和舞台表现",
        "弱项": "声乐稳定性",
        "练习生经历": "刚进入公司",
        "家庭状况": "普通家庭，家人担心但支持",
        "出身来源标签": ["素人发掘", "训练适应快"],
        "生理周期系统": "极致",
    }


def get_path(obj: Any, path: str, default: Any = None) -> Any:
    cur = obj.model_dump() if hasattr(obj, "model_dump") else obj
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur


def event_codes(events: list[Any]) -> set[str]:
    return {str(getattr(event, "code", "")) for event in events}


def event_sources(events: list[Any]) -> set[str]:
    return {str(getattr(event, "source_system", "")) for event in events}


def response_choices(response: Any) -> list[Any]:
    return list(getattr(response, "choices", []) or [])


def response_narrative(response: Any) -> str:
    return str(getattr(response, "narrative", "") or "")


def applied_keys(applied: dict[str, Any]) -> set[str]:
    return {str(key) for key in applied.keys()}


def setup_small_company_trainee(state: GameState) -> None:
    state.company.update({
        "公司规模": "小型公司",
        "公司风格": "舞台型",
        "资源池": 24,
        "出道窗口压力": 76,
        "公司信任度": 58,
    })
    state.team.update({"队内竞争度": 68, "真实关系温度": 35, "宿舍安全感": 34})
    state.body.update({"体力": 62, "睡眠质量": 58, "伤病风险": 24})
    state.mind.update({"精神压力": 58, "孤独感": 48})
    state.time["next_evaluation_days"] = 3


def setup_debut_ready_trainee(state: GameState) -> None:
    setup_small_company_trainee(state)
    state.career.update({
        "舞蹈实力": 60,
        "声乐实力": 56,
        "RAP能力": 42,
        "舞台感染力": 62,
        "形象指数": 54,
        "语言能力": 48,
    })
    state.company.update({"公司信任度": 80, "资源池": 72, "资源倾斜度": 60})
    state.team["团队默契度"] = 74
    state.body.update({"体力": 80, "伤病风险": 18, "嗓音状态": 78})
    state.mind["精神压力"] = 42
    state.fans["个人粉丝数"] = 65000


def setup_idol_comeback(state: GameState) -> None:
    state.current_stage = "已出道爱豆阶段"
    state.current_mainline = "回归打歌期"
    state.current_schedule = "回归第一周打歌和彩排"
    state.company.update({
        "公司规模": "大型公司",
        "公司风格": "数据导向",
        "资源池": 78,
        "资源倾斜度": 62,
        "主推指数": 58,
        "公司信任度": 66,
        "个人议价权": 44,
    })
    state.career.update({
        "舞蹈实力": 72,
        "声乐实力": 68,
        "RAP能力": 56,
        "舞台感染力": 78,
        "综艺感": 62,
        "形象指数": 76,
        "演技潜力": 54,
        "创作能力": 50,
    })
    state.market.update({
        "话题度": 66,
        "品牌价值": 60,
        "韩国本土影响力": 52,
        "音源潜力": 66,
        "销量潜力": 72,
        "短视频传播力": 74,
    })
    state.fans.update({
        "个人粉丝数": 120000,
        "团体粉丝数": 520000,
        "团粉稳定度": 72,
        "唯粉规模": 36,
        "粉丝信任基础": 70,
        "路人好感": 62,
        "站姐稳定度": 60,
    })
    state.comeback.update({"回归阶段": "打歌期", "风格适配度": 70, "制作参与等级": 0})


def setup_boundary_minor(state: GameState) -> None:
    state.age_context.update({"age": 16, "is_minor": True, "guardian_required": True})
    state.school.update({"enrolled": True, "attendance_pressure": 70, "exam_pressure": 64})
    state.family.update({"career_understanding": 30, "conflict_level": 64})
    state.important_npcs = [
        {"name": "李娜英", "role": "同期练习生", "age": 16},
        {"name": "韩老师", "role": "舞蹈老师", "age": 32},
    ]
    state.safety.update({"dorm_security": 42, "boundary_violation_risk": 45})


def setup_overseas_context(state: GameState) -> None:
    state.age_context.update({"age": 17, "is_minor": True, "guardian_required": True})
    state.social_context.update({
        "nationality": "中国",
        "is_overseas": True,
        "language_barrier": 62,
        "cultural_adaptation": 28,
        "visa_pressure": 66,
        "family_distance": 78,
    })
    state.hierarchy.update({
        "honorific_adaptation": 30,
        "etiquette_pressure": 72,
        "backstage_protocol_familiarity": 28,
    })
    state.school.update({"enrolled": True, "attendance_pressure": 68, "homework_pressure": 60})
    # Ordinary/focus turns advance several days before period evaluation. Day 22
    # lands on day 1 after a 7-day ordinary turn, which reliably tests entry.
    state.period.update({"enabled": True, "mode": "极致", "cycle_day": 22, "irregularity_risk": 44})


def setup_mature_branching(state: GameState) -> None:
    setup_idol_comeback(state)
    state.current_mainline = "续约前一年"
    state.current_schedule = "个人路线评估期"
    state.turn = 156
    state.company.update({"个人议价权": 86, "主推指数": 80, "续约倾向": 54})
    state.market.update({"品牌价值": 86, "话题度": 78})
    state.fans.update({"个人粉丝数": 320000, "团体粉丝数": 900000})
    state.career.update({"演技潜力": 74, "创作能力": 72, "制作人能力": 28, "综艺感": 70})
    state.body["伤病风险"] = 62


def require_common_response_contract(failures: list[str], response: Any, raw: str) -> None:
    narrative = response_narrative(response)
    if "你" not in narrative:
        failures.append("模型剧情没有使用第二人称“你”。")
    scene_words = ["练习室", "会议室", "宿舍", "走廊", "后台", "保姆车", "榜单", "办公室", "录音室", "舞台", "手机", "屏幕"]
    if not any(word in narrative for word in scene_words):
        failures.append("模型剧情缺少具体场景锚点。")
    if len(response_choices(response)) < 4:
        failures.append("模型返回的 choices 少于 4 个。")
    if raw.strip().startswith("```"):
        failures.append("模型返回了 Markdown 代码块，而不是裸 JSON。")


def check_step_expectations(
    step: JourneyStep,
    before: GameState,
    after: GameState,
    response: Any,
    applied: dict[str, Any],
    route: Any,
    events: list[Any],
    raw_response: str,
    prompt_messages: list[dict[str, str]],
) -> list[str]:
    failures: list[str] = []
    require_common_response_contract(failures, response, raw_response)

    codes = event_codes(events)
    sources = event_sources(events)
    keys = applied_keys(applied)
    narrative = response_narrative(response)

    if step.expect_route_kinds and str(getattr(route, "turn_kind", "")) not in step.expect_route_kinds:
        failures.append(f"{step.name}: route_kind 应在 {sorted(step.expect_route_kinds)}，实际为 {getattr(route, 'turn_kind', None)!r}。")

    if step.expect_turn_duration_days is not None:
        actual_days = get_path(after, "time.turn_duration_days")
        if actual_days != step.expect_turn_duration_days:
            failures.append(f"{step.name}: 本回合应推进 {step.expect_turn_duration_days} 天，实际推进 {actual_days!r} 天。")

    if step.expect_prompt_weekly_contract is not None:
        contract = prompt_turn_time_contract(prompt_messages)
        actual = contract.get("has_weekly_plan")
        if actual is not step.expect_prompt_weekly_contract:
            failures.append(f"{step.name}: prompt turn_time_contract.has_weekly_plan 应为 {step.expect_prompt_weekly_contract!r}，实际为 {actual!r}。")
        if step.expect_prompt_weekly_contract:
            rule_text = str(contract.get("rule", ""))
            if "一周" not in rule_text or "不缩短" not in rule_text:
                failures.append(f"{step.name}: prompt turn_time_contract 没有明确一周跨度和不缩短规则：{contract!r}。")

    missing_sources = sorted(step.expect_event_sources - sources)
    if missing_sources:
        failures.append(f"{step.name}: 缺少系统来源 {missing_sources}，实际来源 {sorted(sources)}。")

    missing_codes = sorted(step.expect_event_codes - codes)
    if missing_codes:
        failures.append(f"{step.name}: 缺少事件 code {missing_codes}，实际 codes {sorted(codes)}。")

    for fragment in step.expect_event_code_fragments:
        if not any(fragment in code for code in codes):
            failures.append(f"{step.name}: 没有任何事件 code 包含 {fragment!r}，实际 codes {sorted(codes)}。")

    missing_keys = sorted(step.expect_applied_keys - keys)
    if missing_keys:
        failures.append(f"{step.name}: applied_diff 缺少 {missing_keys}，实际 keys {sorted(keys)}。")

    for path, expected in step.expect_state_paths.items():
        actual = get_path(after, path)
        if actual != expected:
            failures.append(f"{step.name}: 状态 {path} 应为 {expected!r}，实际为 {actual!r}。")

    for path in step.expect_state_path_changed:
        old = get_path(before, path)
        new = get_path(after, path)
        if old == new:
            failures.append(f"{step.name}: 状态 {path} 没有变化，仍为 {new!r}。")

    rels = getattr(after, "relationships", {}) or {}
    missing_rels = sorted(name for name in step.expect_relationships if name not in rels)
    if missing_rels:
        failures.append(f"{step.name}: 缺少关系档案 {missing_rels}，实际关系 {sorted(rels.keys())}。")

    if step.narrative_any and not any(word in narrative for word in step.narrative_any):
        failures.append(f"{step.name}: 剧情没有包含任一关键词 {step.narrative_any}。")

    failures.extend(check_narrative_focus(step, narrative))

    forbidden = list(step.narrative_none) + [
        "直接拿下一位",
        "正式获得一位",
        "续约成功",
        "转型成功",
        "solo成功",
        "正式签下代言",
        "危机彻底结束",
        "争议彻底解决",
    ]
    found = [word for word in forbidden if word in narrative]
    if found:
        failures.append(f"{step.name}: 剧情出现不应直接宣布的终局词 {found}。")

    return failures


def prompt_turn_time_contract(prompt_messages: list[dict[str, str]]) -> dict[str, Any]:
    if not prompt_messages:
        return {}
    try:
        payload = json.loads(prompt_messages[-1].get("content", "{}"))
    except Exception:
        return {}
    value = payload.get("turn_time_contract")
    return value if isinstance(value, dict) else {}


def check_narrative_focus(step: JourneyStep, narrative: str) -> list[str]:
    if not step.narrative_focus:
        return []
    text = str(narrative or "")
    focus_words = {
        "ordinary": ["本周", "一周", "训练", "休息", "作息", "周常", "几天"],
        "focus": ["关键", "会议", "考核", "展示", "demo", "镜头", "重点"],
        "crisis": ["热搜", "回应", "澄清", "声明", "公关", "危机", "舆论"],
        "mainline": ["续约", "谈判", "权限", "条款", "分成", "健康保障", "阶段"],
    }
    forbidden_words = {
        "ordinary": ["危机彻底结束", "续约成功", "正式获得一位", "转型成功"],
        "focus": ["已经出道成功", "正式获得一位", "主打确定采纳"],
        "crisis": ["危机彻底结束", "彻底澄清", "所有争议消失"],
        "mainline": ["续约成功", "solo成功", "转型成功", "最终结局确定"],
    }
    required = focus_words.get(step.narrative_focus, [])
    if required and not any(word in text for word in required):
        return [f"{step.name}: 剧情没有体现 {step.narrative_focus} 叙事重心，缺少任一关键词 {required}。"]
    found_forbidden = [word for word in forbidden_words.get(step.narrative_focus, []) if word in text]
    if found_forbidden:
        return [f"{step.name}: {step.narrative_focus} 叙事重心出现不该直达的结果词 {found_forbidden}。"]
    return []


def build_journeys() -> list[PlayerJourney]:
    return [
        PlayerJourney(
            name="weekly_plan_narrative_focus_modes",
            description="同样是一周安排，分别检查普通、重点、危机、主线回合是否写出不同叙事重心。",
            character=base_character(name="多恩", timeline="回归瓶颈期", company_size="大型公司", identity="已出道女团成员"),
            setup=setup_idol_comeback,
            steps=[
                JourneyStep(
                    name="weekly_ordinary_routine_focus",
                    action=(
                        "我按照本周安排稳定推进，不追求额外事件。\n\n"
                        "【本周安排】本周七格安排：固定2格（职业状态维持、公司/团队基础行程）；"
                        "自选3/5格（维持训练、恢复治疗、粉丝营业）。"
                        " 具体自选：自选安排舞蹈声乐维持训练；自选安排休息、睡眠、治疗和康复；自选安排粉丝营业。"
                    ),
                    expect_route_kinds={"ordinary"},
                    expect_turn_duration_days=7,
                    expect_prompt_weekly_contract=True,
                    narrative_focus="ordinary",
                    narrative_any=["训练", "恢复", "粉丝"],
                    narrative_none=["热搜", "续约成功", "正式获得一位"],
                ),
                JourneyStep(
                    name="weekly_focus_key_scene",
                    action=(
                        "我按照本周安排推进，但把demo和概念会议当成本周最关键的重点场景。\n\n"
                        "【本周安排】本周七格安排：固定2格（职业状态维持、公司/团队基础行程）；"
                        "自选4/5格（创作会议、录音/MV、维持训练、恢复治疗）。"
                        " 具体自选：自选安排demo创作、概念会议或制作讨论；自选安排录音、MV或拍摄；自选安排舞蹈声乐维持训练；自选安排休息和康复。"
                    ),
                    expect_route_kinds={"focus"},
                    expect_turn_duration_days=7,
                    expect_prompt_weekly_contract=True,
                    narrative_focus="focus",
                    narrative_any=["demo", "概念", "会议", "重点"],
                    narrative_none=["主打确定采纳", "制作人转型成功"],
                ),
                JourneyStep(
                    name="weekly_crisis_response_focus",
                    action=(
                        "旧采访片段被剪上热搜后，我按照本周安排和公司准备回应、澄清和声明。\n\n"
                        "【本周安排】本周七格安排：固定2格（职业状态维持、公司/团队基础行程）；"
                        "自选4/5格（公关回应、恢复治疗、粉丝营业、维持训练）。"
                        " 具体自选：自选安排公司公关回应；自选安排休息、睡眠、治疗和康复；自选安排粉丝营业；自选安排舞蹈声乐维持训练。"
                    ),
                    expect_route_kinds={"crisis"},
                    expect_event_sources={"public_relations"},
                    expect_turn_duration_days=7,
                    expect_prompt_weekly_contract=True,
                    narrative_focus="crisis",
                    narrative_any=["热搜", "回应", "澄清", "公司"],
                    narrative_none=["危机彻底结束", "彻底澄清"],
                ),
                JourneyStep(
                    name="weekly_mainline_contract_focus",
                    action=(
                        "续约谈判周，我按照本周安排要求solo权限、演员约权限、创作署名权、健康保障和更合理的分成比例。\n\n"
                        "【本周安排】本周七格安排：固定2格（职业状态维持、公司/团队基础行程）；"
                        "自选5/5格（续约谈判、创作会议、品牌/杂志、恢复治疗、维持训练）。"
                        " 具体自选：自选安排续约合同谈判；自选安排demo创作、概念会议或制作讨论；自选安排品牌和杂志会议；自选安排休息、睡眠、治疗和康复；自选安排舞蹈声乐维持训练。"
                    ),
                    expect_route_kinds={"mainline"},
                    expect_event_sources={"brand_contract", "career_branch"},
                    expect_turn_duration_days=7,
                    expect_prompt_weekly_contract=True,
                    narrative_focus="mainline",
                    narrative_any=["续约", "谈判", "权限", "健康"],
                    narrative_none=["续约成功", "solo成功", "转型成功"],
                ),
            ],
        ),
        PlayerJourney(
            name="trainee_small_company_to_debut_gate",
            description="小公司练习生从时间格压力、同伴关系、月末考核一路跑到出道候选门槛。",
            character=base_character(name="知序", age=18, company_size="小型公司"),
            setup=setup_debut_ready_trainee,
            steps=[
                JourneyStep(
                    name="overbook_training_week",
                    action="白天学校考试，晚上高强度加练舞蹈声乐，还写demo、观察公司资源和出道窗口压力。",
                    expect_route_kinds={"focus", "ordinary"},
                    expect_event_sources={"company", "trainee_life"},
                    expect_event_code_fragments=["overbooked", "company"],
                    expect_state_paths={
                        "trainee_life.weekly_slots_total": 7,
                        "trainee_life.mandatory_slots": 4,
                        "trainee_life.free_slots": 3,
                    },
                    expect_applied_keys={"身体状态.体力", "身体状态.睡眠质量", "心理状态.精神压力"},
                    narrative_any=["学校", "练习", "demo", "公司"],
                ),
                JourneyStep(
                    name="weekly_plan_ui_marker_three_free_slots",
                    action="我按照界面选择的本周安排推进训练。\n\n【本周安排】本周七格安排：固定4格（舞蹈课、声乐课、体能课、形象/语言/团队课）；自选3/3格（舞蹈加练、声乐加练、创作 demo）。 具体自选：自选安排舞蹈加练；自选安排声乐加练；自选安排作词作曲训练和demo创作。",
                    expect_route_kinds={"ordinary", "focus"},
                    expect_event_sources={"progression"},
                    expect_state_paths={
                        "trainee_life.weekly_slots_total": 7,
                        "trainee_life.mandatory_slots": 4,
                        "trainee_life.free_slots": 3,
                    },
                    expect_state_path_changed={"progression.skill_xp.dance", "progression.skill_xp.vocal", "progression.skill_xp.creative"},
                    narrative_any=["本周安排", "舞蹈", "声乐", "demo"],
                ),
                JourneyStep(
                    name="new_peer_relationship_unlock",
                    action="李娜英在练习室帮我数拍，我递热水给她，陪她一起练并谈心。",
                    expect_event_sources={"relationship"},
                    expect_event_codes={"rel_friendship_signal"},
                    expect_relationships={"李娜英"},
                    expect_state_path_changed={"relationships.李娜英.friendship", "relationships.李娜英.trust"},
                    expect_applied_keys={"团队关系.真实关系温度", "心理状态.孤独感"},
                    narrative_any=["李娜英", "热水", "练习"],
                ),
                JourneyStep(
                    name="monthly_evaluation_debut_window",
                    action="季度评估和月末考核结束后，公司会议讨论我是否进入出道组候选。",
                    expect_route_kinds={"focus"},
                    expect_event_sources={"time", "debut"},
                    expect_event_code_fragments=["debut"],
                    expect_state_paths={"debut.window_turns_left": 8},
                    expect_state_path_changed={"debut.status", "debut.readiness", "debut.probability"},
                    narrative_any=["考核", "会议", "出道组"],
                    narrative_none=["已经出道成功"],
                ),
            ],
        ),
        PlayerJourney(
            name="idol_comeback_market_brand_contract",
            description="出道爱豆在回归、市场成绩、商业资源、公关危机和续约之间连续推进。",
            character=base_character(name="书雅", timeline="回归瓶颈期", company_size="大型公司", identity="已出道女团成员"),
            setup=setup_idol_comeback,
            steps=[
                JourneyStep(
                    name="comeback_low_authority_concept",
                    action="回归概念会议上，我拿出自己写的demo和风格想法，但公司提醒我目前制作参与权限还不高。",
                    expect_route_kinds={"focus", "mainline"},
                    expect_event_sources={"comeback", "progression"},
                    expect_event_code_fragments=["comeback", "progression"],
                    expect_applied_keys={"心理状态.自我认同", "公司与合约.公司满意度"},
                    narrative_any=["概念", "demo", "公司", "会议"],
                    narrative_none=["主打确定采纳", "制作人转型成功"],
                ),
                JourneyStep(
                    name="first_week_market_scores",
                    action="回归打歌第一周，我和经纪人一起看音源、销量、MV、直拍、投票和一位候补数据。",
                    expect_route_kinds={"focus", "mainline"},
                    expect_event_sources={"schedule", "market_score"},
                    expect_event_code_fragments=["market"],
                    expect_state_path_changed={"market_scores.音源成绩", "market_scores.音乐节目分数", "market_scores.一位概率"},
                    narrative_any=["音源", "销量", "直拍", "一位"],
                    narrative_none=["正式获得一位"],
                ),
                JourneyStep(
                    name="brand_meeting_after_market",
                    action="美妆品牌和杂志封面团队来公司会议室评估我，但经纪人提醒商业安全度和舆论风险也会被看见。",
                    expect_event_sources={"brand_contract"},
                    expect_event_code_fragments=["brand"],
                    expect_state_path_changed={"commercial.商业安全度", "commercial.品牌适配度"},
                    narrative_any=["品牌", "杂志", "会议"],
                    narrative_none=["正式签下代言"],
                ),
                JourneyStep(
                    name="public_relation_response_window",
                    action="旧采访片段被黑粉剪上热搜后，我和公司准备回应、澄清和声明。",
                    expect_route_kinds={"crisis"},
                    expect_event_sources={"public_relations"},
                    expect_event_codes={"pr_response_window"},
                    expect_event_code_fragments=["crisis"],
                    expect_applied_keys={"公司与合约.危机关注度"},
                    narrative_any=["热搜", "回应", "公司"],
                    narrative_none=["危机彻底结束", "彻底澄清"],
                ),
                JourneyStep(
                    name="contract_negotiation_rights",
                    action="续约谈判时，我要求solo权限、演员约权限、创作署名权、健康保障和更合理的分成比例。",
                    expect_route_kinds={"mainline", "crisis"},
                    expect_event_sources={"brand_contract", "career_branch"},
                    expect_event_code_fragments=["contract", "career_branch"],
                    expect_state_path_changed={"contract_terms.solo权限", "contract_terms.演员约权限", "contract_terms.健康保障"},
                    narrative_any=["续约", "谈判", "权限", "健康"],
                    narrative_none=["续约成功"],
                ),
            ],
        ),
        PlayerJourney(
            name="minor_relationship_boundary_and_safety",
            description="未成年练习生连续触发同龄关系、老师边界、身体边界和非法外出阻断。",
            character=base_character(name="敏知", age=16, company_size="中型公司"),
            setup=setup_boundary_minor,
            steps=[
                JourneyStep(
                    name="same_age_friendship_not_romance",
                    action="李娜英陪我在宿舍走廊背歌词，我有点依赖她，但我们只是互相照顾和谈心。",
                    expect_event_sources={"relationship"},
                    expect_event_codes={"rel_friendship_signal"},
                    expect_relationships={"李娜英"},
                    expect_state_path_changed={"relationships.李娜英.friendship", "relationships.李娜英.trust"},
                    narrative_any=["李娜英", "宿舍", "歌词"],
                    narrative_none=["确认关系", "恋爱成立"],
                ),
                JourneyStep(
                    name="teacher_power_boundary",
                    action="韩老师课后单独夸我，我有点心动但也知道这是老师关系，所以主动保持职业边界。",
                    expect_event_sources={"relationship"},
                    expect_event_code_fragments=["boundary"],
                    expect_relationships={"韩老师"},
                    expect_state_path_changed={"relationships.韩老师.relationship_risk"},
                    narrative_any=["韩老师", "边界", "课后"],
                    narrative_none=["暧昧", "恋爱"],
                ),
                JourneyStep(
                    name="harassment_help_path",
                    action="造型助理靠得太近让我身体边界很不舒服，我离开房间、记录细节并找可信工作人员求助。",
                    expect_event_sources={"safety_boundary"},
                    expect_event_code_fragments=["harassment"],
                    expect_applied_keys={"心理状态.精神压力", "心理状态.边界感", "公司与合约.危机关注度"},
                    narrative_any=["身体边界", "记录", "求助"],
                    narrative_none=["暧昧", "浪漫"],
                ),
                JourneyStep(
                    name="minor_private_outing_blocked",
                    action="我半夜一个人偷偷出门打车去便利店。",
                    expect_blocked=True,
                    narrative_any=[],
                ),
            ],
        ),
        PlayerJourney(
            name="overseas_school_period_hierarchy",
            description="海外未成年练习生把学校、家庭、签证、敬语和生理期压力连续压到同一存档里。",
            character=base_character(name="宁宁", age=17, company_size="中型公司", nationality="中国"),
            setup=setup_overseas_context,
            steps=[
                JourneyStep(
                    name="school_family_overseas_pressure",
                    action="考试前一天我还要参加训练，请假后给父母打电话解释，但他们担心我在韩国太累。",
                    expect_event_sources={"school_family", "social_context"},
                    expect_event_code_fragments=["school", "family"],
                    expect_applied_keys={"心理状态.精神压力"},
                    narrative_any=["考试", "父母", "韩国", "训练"],
                ),
                JourneyStep(
                    name="language_hierarchy_mistake",
                    action="后台采访前我听不懂韩语玩笑，还说错敬语，忘记向前辈问候。",
                    expect_event_sources={"social_context", "hierarchy"},
                    expect_event_codes={"social_language_pressure", "hierarchy_etiquette_mistake"},
                    expect_applied_keys={"心理状态.精神压力"},
                    narrative_any=["韩语", "敬语", "前辈", "后台"],
                ),
                JourneyStep(
                    name="period_high_intensity_training",
                    action="生理期前段我穿浅色评估服继续高强度练舞，隐瞒不说，也没有及时准备用品。",
                    expect_event_sources={"period"},
                    expect_event_code_fragments=["period"],
                    expect_applied_keys={"身体状态.体力", "身体状态.伤病风险"},
                    expect_state_path_changed={"period.phase"},
                    narrative_any=["生理期", "评估服", "练舞"],
                ),
            ],
        ),
        PlayerJourney(
            name="mature_idol_branching_and_ending",
            description="成熟期爱豆连续测试演员、solo/unit、创作、暂停维权和结局窗口。",
            character=base_character(name="夏景", timeline="续约前一年", company_size="大型公司", identity="成熟女团成员"),
            setup=setup_mature_branching,
            steps=[
                JourneyStep(
                    name="acting_solo_creative_branch",
                    action="公司讨论演员试镜、solo小分队unit、创作署名和个人综艺路线，我想知道哪些只是测试机会。",
                    expect_route_kinds={"mainline", "focus"},
                    expect_event_sources={"career_branch"},
                    expect_event_code_fragments=["career_branch"],
                    expect_state_path_changed={"career_branches.branch_opportunities"},
                    narrative_any=["演员", "solo", "unit", "创作"],
                    narrative_none=["转型成功", "solo成功"],
                ),
                JourneyStep(
                    name="rights_path_health_pause",
                    action="我考虑暂停活动、保留证据、找法务谈维权和健康保障，也想知道能不能换公司。",
                    expect_route_kinds={"mainline", "crisis"},
                    expect_event_sources={"career_branch", "brand_contract"},
                    expect_event_code_fragments=["rights", "contract"],
                    expect_state_path_changed={"career_branches.rights_path_stage", "contract_terms.健康保障"},
                    narrative_any=["暂停", "证据", "法务", "健康"],
                    narrative_none=["退圈失败"],
                ),
                JourneyStep(
                    name="ending_window_decision",
                    action="续约期最后，公司让我在继续团体、solo、演员转型和换公司之间做阶段性选择。",
                    expect_route_kinds={"mainline"},
                    expect_event_sources={"ending", "brand_contract"},
                    expect_event_code_fragments=["ending"],
                    expect_state_paths={"ending.window": "open"},
                    expect_state_path_changed={"ending.candidate_endings"},
                    narrative_any=["续约", "团体", "solo", "演员", "公司"],
                    narrative_none=["最终结局确定"],
                ),
            ],
        ),
    ]


class PlayerJourneyRunner:
    def __init__(self, config: AppConfig, output_dir: Path, include_raw: bool = False, fail_fast: bool = False) -> None:
        self.config = config
        self.output_dir = output_dir
        self.include_raw = include_raw
        self.fail_fast = fail_fast
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.tempdir = tempfile.TemporaryDirectory(prefix="kpop_player_journey_", ignore_cleanup_errors=True)
        self.storage = SaveStorage(Path(self.tempdir.name) / "saves.db")
        self.engine = TurnEngine(self.storage, self.config)
        self.recording_provider = RecordingProvider(self.engine.provider)
        self.engine.provider = self.recording_provider

    def close(self) -> None:
        self.tempdir.cleanup()

    def run_journey(self, journey: PlayerJourney, max_steps: int | None = None) -> dict[str, Any]:
        state = self.engine.create_initial_state(journey.character)
        if journey.setup:
            journey.setup(state)
        save_id = self.storage.create_save(state)

        step_reports: list[dict[str, Any]] = []
        failures: list[str] = []
        selected_steps = journey.steps[:max_steps] if max_steps is not None else journey.steps

        for idx, step in enumerate(selected_steps, start=1):
            print(f"  [{idx}/{len(selected_steps)}] {step.name} ...", flush=True)
            started = time.perf_counter()
            before = state.model_copy(deep=True)
            raw_response = ""
            messages: list[dict[str, str]] = []
            report: dict[str, Any] = {
                "name": step.name,
                "description": step.description,
                "action": step.action,
                "expect_blocked": step.expect_blocked,
                "passed": False,
                "failures": [],
            }
            try:
                after, response, applied, route, events, validation = self.engine.run_turn(save_id, state, step.action)
                state = after
                raw_response = self.recording_provider.last_raw
                messages = self.recording_provider.last_messages

                if step.expect_blocked:
                    report["failures"].append("该步骤预期被行动门控阻断，但实际进入了模型回合。")
                else:
                    report["failures"].extend(
                        check_step_expectations(step, before, after, response, applied, route, events, raw_response, messages)
                    )

                report.update({
                    "route": route.model_dump(),
                    "validation": validation.model_dump(),
                    "event_sources": sorted(event_sources(events)),
                    "event_codes": sorted(event_codes(events)),
                    "applied_diff": applied,
                    "response": {
                        "narrative_excerpt": response_narrative(response)[:800],
                        "public_summary": str(getattr(response, "public_summary", "") or ""),
                        "choices": [choice.model_dump() for choice in response_choices(response)],
                        "npc_reactions": [reaction.model_dump() for reaction in getattr(response, "npc_reactions", [])],
                    },
                    "state_probe": {
                        "turn": after.turn,
                        "stage": after.current_stage,
                        "mainline": after.current_mainline,
                        "schedule": after.current_schedule,
                        "body": after.body,
                        "mind": after.mind,
                        "company": after.company,
                        "team": after.team,
                        "fans": after.fans,
                        "market": after.market,
                        "risks": after.risks,
                        "relationships": after.relationships,
                        "trainee_life": after.trainee_life,
                        "market_scores": after.market_scores,
                        "commercial": after.commercial,
                        "contract_terms": after.contract_terms,
                        "career_branches": after.career_branches,
                        "debut": after.debut,
                        "ending": after.ending,
                    },
                })
            except ActionBlockedError as exc:
                if step.expect_blocked:
                    report["blocked_reason"] = exc.message
                    report["suggestions"] = exc.suggestions
                    report["failures"] = []
                else:
                    report["failures"].append(f"行动被意外阻断：{exc.message}")
            except Exception as exc:
                report["failures"].append(f"{type(exc).__name__}: {exc}")

            report["elapsed_seconds"] = round(time.perf_counter() - started, 3)
            report["passed"] = not report["failures"]
            report["prompt_chars"] = sum(len(message.get("content", "")) for message in messages)
            if self.include_raw:
                report["raw_response"] = raw_response
                report["prompt_messages"] = messages
            elif raw_response:
                report["raw_response_excerpt"] = raw_response[:1000]

            if report["failures"]:
                for failure in report["failures"]:
                    print(f"    - {failure}", flush=True)
                failures.extend(f"{step.name}: {failure}" for failure in report["failures"])
            print(f"    {'PASS' if report['passed'] else 'FAIL'} {report['elapsed_seconds']}s", flush=True)
            step_reports.append(report)

            if self.fail_fast and failures:
                break

        return {
            "name": journey.name,
            "description": journey.description,
            "passed": not failures,
            "failures": failures,
            "steps_total": len(selected_steps),
            "steps_passed": sum(1 for item in step_reports if item["passed"]),
            "steps": step_reports,
        }

    def run(self, journeys: list[PlayerJourney], max_steps: int | None = None) -> dict[str, Any]:
        journey_reports: list[dict[str, Any]] = []
        for idx, journey in enumerate(journeys, start=1):
            print(f"[{idx}/{len(journeys)}] {journey.name}", flush=True)
            journey_reports.append(self.run_journey(journey, max_steps=max_steps))

        passed = sum(1 for item in journey_reports if item["passed"])
        total_steps = sum(item["steps_total"] for item in journey_reports)
        passed_steps = sum(item["steps_passed"] for item in journey_reports)
        report = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "repo": str(ROOT),
            "provider": self.config.provider_label(),
            "model_policy": self.config.model_policy,
            "loaded_modules": list_prompt_modules(),
            "summary": {
                "journeys_total": len(journey_reports),
                "journeys_passed": passed,
                "journeys_failed": len(journey_reports) - passed,
                "steps_total": total_steps,
                "steps_passed": passed_steps,
                "steps_failed": total_steps - passed_steps,
                "step_pass_rate": round(passed_steps / total_steps, 4) if total_steps else 0,
            },
            "journeys": journey_reports,
        }
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.output_dir / f"player_journey_stress_report_{stamp}.json"
        latest_path = self.output_dir / "player_journey_stress_report_latest.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        latest_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Report: {report_path}", flush=True)
        print(f"Latest: {latest_path}", flush=True)
        return report


def select_journeys(journeys: list[PlayerJourney], names: list[str], limit: int | None) -> list[PlayerJourney]:
    selected = journeys
    if names:
        wanted = set(names)
        selected = [journey for journey in selected if journey.name in wanted]
        missing = sorted(wanted - {journey.name for journey in selected})
        if missing:
            raise SystemExit(f"Unknown journey name(s): {missing}")
    if limit is not None:
        selected = selected[:limit]
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run real-API continuous player-journey stress tests against KPOP simulator rules."
    )
    parser.add_argument("--journey", action="append", default=[], help="Run only the named journey. Can be repeated.")
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N selected journeys.")
    parser.add_argument("--max-steps", type=int, default=None, help="Run only the first N steps inside each selected journey.")
    parser.add_argument("--model-policy", choices=["auto", "flash", "pro", "custom"], default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "stress_reports"))
    parser.add_argument("--include-raw", action="store_true", help="Store full raw model responses and prompts in report.")
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--list", action="store_true", help="List journeys and steps, then exit.")
    args = parser.parse_args()

    journeys = build_journeys()
    if args.list:
        for journey in journeys:
            print(f"{journey.name}\t{len(journey.steps)} steps\t{journey.description}")
            for step in journey.steps:
                mode = "BLOCK" if step.expect_blocked else "API"
                print(f"  - {step.name}\t{mode}\t{step.action}")
        return 0

    config = AppConfig()
    if args.model_policy:
        config.model_policy = args.model_policy
    if not config.get_active_api_key_fallback():
        raise SystemExit(
            f"Missing API key for {config.provider_label()}. Set it in the app settings or environment before running real-API journey tests."
        )

    selected = select_journeys(journeys, args.journey, args.limit)
    runner = PlayerJourneyRunner(
        config=config,
        output_dir=Path(args.output_dir),
        include_raw=args.include_raw,
        fail_fast=args.fail_fast,
    )
    try:
        report = runner.run(selected, max_steps=args.max_steps)
    finally:
        runner.close()
    return 0 if report["summary"]["steps_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
