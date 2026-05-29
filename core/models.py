from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Choice(BaseModel):
    id: str
    text: str


class NPCReaction(BaseModel):
    name: str
    reaction: str
    role: Optional[str] = None
    age: Optional[int] = None


class SystemEvent(BaseModel):
    code: str
    title: str
    severity: str = "info"
    description: str
    source_system: str
    suggested_diff: Dict[str, int] = Field(default_factory=dict)
    new_flags: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class ActiveCrisis(BaseModel):
    crisis_id: str
    crisis_type: str
    title: str
    stage: str = "signal"
    heat: int = 50
    duration: int = 0
    truth_clarity: int = 30
    company_involvement: int = 20
    player_response: str = ""
    exit_condition: str = ""
    failure_flag: str = ""
    notes: str = ""


class RouteInfo(BaseModel):
    model_tier: str = "flash"
    turn_kind: str = "ordinary"
    reason: str = "普通养成回合，使用 Flash。"
    actual_model: str = ""


class TurnResponse(BaseModel):
    narrative: str = ""
    npc_reactions: List[NPCReaction] = Field(default_factory=list)
    choices: List[Choice] = Field(default_factory=list)
    suggested_diff: Dict[str, int] = Field(default_factory=dict)
    new_flags: List[str] = Field(default_factory=list)
    resolved_flags: List[str] = Field(default_factory=list)
    public_summary: str = ""
    private_notes: str = ""


class GameState(BaseModel):
    save_name: str = "未命名存档"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    turn: int = 0
    current_stage: str = "角色创建后"
    current_mainline: str = "进入公司前的准备"
    current_schedule: str = "暂无固定行程"
    next_milestone: str = "等待第一回合"

    character: Dict[str, Any] = Field(default_factory=dict)

    age_context: Dict[str, Any] = Field(default_factory=lambda: {
        "age": None,
        "age_group": "未知",
        "is_minor": False,
        "guardian_required": False,
        "romance_allowed": True,
    })

    relationships: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    time: Dict[str, Any] = Field(default_factory=lambda: {
        "current_date": "2026-01-01",
        "age_years": None,
        "age_months": None,
        "days_elapsed": 0,
        "turn_duration_days": 0,
        "trainee_month": 1,
        "next_evaluation_days": 28,
        "last_turn_kind": "none",
        "last_time_note": "角色创建",
    })

    school: Dict[str, Any] = Field(default_factory=lambda: {
        "enrolled": False,
        "school_type": "非在学",
        "attendance_pressure": 0,
        "exam_pressure": 0,
        "homework_pressure": 0,
        "classmate_relationship": 0,
        "leave_risk": 0,
    })

    family: Dict[str, Any] = Field(default_factory=lambda: {
        "emotional_support": 45,
        "financial_support": 55,
        "career_understanding": 35,
        "control_level": 30,
        "conflict_level": 20,
        "distance_from_home": 30,
        "guardian_trust_company": 50,
        "last_contact_days": 7,
    })

    social_context: Dict[str, Any] = Field(default_factory=lambda: {
        "nationality": "未填写",
        "is_overseas": False,
        "language_barrier": 20,
        "cultural_adaptation": 55,
        "visa_pressure": 0,
        "family_distance": 30,
        "overseas_market_link": "韩国本土",
        "holiday_homesick_risk": 20,
        "cultural_misread_risk": 10,
    })

    safety: Dict[str, Any] = Field(default_factory=lambda: {
        "outing_permission": 50,
        "dorm_security": 65,
        "trusted_adults": ["经纪人", "舞蹈老师"],
        "boundary_violation_risk": 10,
        "bullying_risk": 12,
        "harassment_risk": 8,
        "report_history": [],
        "independent_outing_allowed": True,
        "curfew_violation_risk": 5,
    })

    hierarchy: Dict[str, Any] = Field(default_factory=lambda: {
        "honorific_adaptation": 55,
        "senior_relationship": 40,
        "etiquette_pressure": 25,
        "industry_reputation": 30,
        "senior_support": 15,
        "senior_pressure": 20,
        "backstage_protocol_familiarity": 50,
    })

    profile_tags: List[str] = Field(default_factory=list)
    initial_allocation_log: List[str] = Field(default_factory=list)
    abilities: List[str] = Field(default_factory=list)
    ability_cooldowns: Dict[str, int] = Field(default_factory=dict)
    growth_history: List[str] = Field(default_factory=list)

    talents: Dict[str, int] = Field(default_factory=lambda: {
        "舞蹈天赋": 50,
        "声乐天赋": 50,
        "RAP天赋": 50,
        "镜头天赋": 50,
        "综艺天赋": 50,
        "语言天赋": 50,
        "演技天赋": 50,
        "创作天赋": 50,
        "体能天赋": 50,
        "抗压天赋": 50,
        "社交天赋": 50,
    })

    career: Dict[str, int] = Field(default_factory=lambda: {
        "舞蹈实力": 5,
        "声乐实力": 5,
        "RAP能力": 3,
        "舞台感染力": 4,
        "综艺感": 3,
        "语言能力": 5,
        "形象指数": 5,
        "演技潜力": 2,
        "创作能力": 2,
        "制作人能力": 0,
    })

    body: Dict[str, int] = Field(default_factory=lambda: {
        "体力": 80,
        "睡眠质量": 70,
        "免疫状态": 75,
        "肌肉疲劳": 20,
        "伤病风险": 15,
        "旧伤负担": 0,
        "嗓音状态": 80,
        "饮食稳定度": 70,
        "体重管理压力": 30,
    })

    mind: Dict[str, int] = Field(default_factory=lambda: {
        "心情": 70,
        "精神压力": 35,
        "孤独感": 30,
        "职业倦怠": 10,
        "自我认同": 55,
        "边界感": 40,
    })

    company: Dict[str, Any] = Field(default_factory=lambda: {
        "公司满意度": 50,
        "公司信任度": 45,
        "主推指数": 35,
        "资源倾斜度": 30,
        "危机关注度": 10,
        "合约稳定度": 70,
        "个人议价权": 10,
        "续约倾向": 50,
        "公司规模": "中型公司",
        "公司路线": "均衡培养",
        "资源池": 50,
        "出道窗口压力": 45,
    })

    team: Dict[str, int] = Field(default_factory=lambda: {
        "团队默契度": 45,
        "队内信任度": 45,
        "队内竞争度": 35,
        "队内资源平衡": 60,
        "镜头前和谐度": 60,
        "真实关系温度": 45,
        "宿舍安全感": 55,
        "营业疲劳": 15,
    })

    fans: Dict[str, int] = Field(default_factory=lambda: {
        "个人粉丝数": 0,
        "团体粉丝数": 0,
        "团粉稳定度": 50,
        "唯粉规模": 0,
        "唯粉攻击性": 10,
        "CP粉规模": 0,
        "CP粉幻想强度": 0,
        "路人好感": 40,
        "黑粉活跃度": 10,
        "站姐稳定度": 50,
        "粉丝信任基础": 50,
        "粉圈撕裂度": 5,
    })

    market: Dict[str, int] = Field(default_factory=lambda: {
        "话题度": 15,
        "品牌价值": 10,
        "韩国本土影响力": 5,
        "中国市场影响力": 0,
        "日本市场影响力": 0,
        "东南亚市场影响力": 0,
        "欧美市场影响力": 0,
        "音源潜力": 30,
        "销量潜力": 25,
        "短视频传播力": 25,
        "直拍传播力": 20,
        "海外流媒潜力": 0,
    })

    risks: Dict[str, int] = Field(default_factory=lambda: {
        "恋爱风险": 0,
        "私生风险": 0,
        "行程泄露风险": 0,
        "住址暴露风险": 0,
        "霸凌排挤风险": 10,
        "队内不和曝光风险": 5,
        "伤病爆发风险": 10,
        "公关危机风险": 5,
    })

    comeback: Dict[str, Any] = Field(default_factory=lambda: {
        "当前回归风格": "未定",
        "制作参与等级": 0,
        "风格适配度": 50,
        "概念争议度": 10,
        "回归阶段": "无回归计划",
    })

    period: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": True,
        "mode": "简化",
        "cycle_day": 8,
        "cycle_length": 28,
        "phase": "稳定期",
        "pain_level": 0,
        "flow_pressure": 0,
        "irregularity_risk": 5,
        "has_supplies": True,
        "told_manager": False,
        "told_teammate": False,
        "last_event_turn": -1,
    })

    inner_life: Dict[str, Any] = Field(default_factory=lambda: {
        "被看见的渴望": 45,
        "亲密需求": 35,
        "比较敏感": 35,
        "自我羞耻感": 25,
        "秘密重量": 10,
        "日记倾向": 35,
        "身体自我意识": 30,
        "心动值": 0,
        "对未来的幻想": 45,
    })

    schedule_profile: Dict[str, Any] = Field(default_factory=lambda: {
        "stage_mode": "trainee",
        "current_profile": {
            "训练": 62,
            "学校生活": 16,
            "公司考察": 10,
            "公开曝光": 2,
            "恢复休息": 10,
        },
        "last_action_type": "none",
        "practice_quota_need": 0,
        "workload_pressure": 0,
        "discipline_score": 50,
        "recent_schedule_notes": [],
    })

    progression: Dict[str, Any] = Field(default_factory=lambda: {
        "skill_xp": {
            "dance": 0,
            "vocal": 0,
            "rap": 0,
            "stage": 0,
            "variety": 0,
            "language": 0,
            "image": 0,
            "acting": 0,
            "creative": 0,
            "producer": 0,
        },
        "skill_total_xp": {
            "dance": 0,
            "vocal": 0,
            "rap": 0,
            "stage": 0,
            "variety": 0,
            "language": 0,
            "image": 0,
            "acting": 0,
            "creative": 0,
            "producer": 0,
        },
        "growth_log": [],
        "last_growth_turn": {},
    })

    skill_proficiency: Dict[str, int] = Field(default_factory=lambda: {
        "dance": 70,
        "vocal": 70,
        "rap": 65,
        "stage": 68,
        "variety": 60,
        "language": 60,
        "acting": 55,
        "creative": 60,
        "producer": 50,
    })

    skill_last_practiced: Dict[str, int] = Field(default_factory=lambda: {
        "dance": 0,
        "vocal": 0,
        "rap": 0,
        "stage": 0,
        "variety": 0,
        "language": 0,
        "acting": 0,
        "creative": 0,
        "producer": 0,
    })
    skill_decay_log: List[Dict[str, Any]] = Field(default_factory=list)

    debut: Dict[str, Any] = Field(default_factory=lambda: {
        "status": "not_candidate",
        "readiness": 0,
        "probability": 0,
        "window_turns_left": 0,
        "last_evaluation_turn": -1,
        "candidate_attempts": 0,
        "last_result": "",
        "history": [],
    })

    ending: Dict[str, Any] = Field(default_factory=lambda: {
        "status": "ongoing",
        "window": "closed",
        "candidate_endings": [],
        "last_evaluation_turn": -1,
        "final_result": "",
        "history": [],
    })
    inner_secrets: List[Dict[str, Any]] = Field(default_factory=list)
    crush_threads: List[Dict[str, Any]] = Field(default_factory=list)
    emotional_outlets: List[str] = Field(default_factory=list)

    status_effects: Dict[str, int] = Field(default_factory=dict)
    locked_actions: List[str] = Field(default_factory=list)
    active_crises: List[ActiveCrisis] = Field(default_factory=list)

    teammates: List[Dict[str, Any]] = Field(default_factory=list)
    important_npcs: List[Dict[str, Any]] = Field(default_factory=list)

    trainee_life: Dict[str, Any] = Field(default_factory=lambda: {
        "weekly_slots_total": 7,
        "mandatory_slots": 4,
        "free_slots": 3,
        "slot_stage": "trainee",
        "fixed_slot_plan": ["舞蹈课", "声乐课", "体能课", "形象/语言/团队课"],
        "last_slot_usage": {},
        "overbooked_weeks": 0,
        "idol_overbooked_weeks": 0,
        "practice_room_access": 50,
        "dorm_friction": 20,
        "bullying_pressure": 15,
        "hidden_conflict": 0,
        "protected_someone_memory": 0,
        "recent_life_notes": [],
    })

    market_scores: Dict[str, Any] = Field(default_factory=lambda: {
        "音源成绩": 0,
        "专辑销量指数": 0,
        "首日销量": 0,
        "首周销量": 0,
        "MV播放指数": 0,
        "短视频传播力": 25,
        "直拍传播力": 20,
        "投票动员力": 0,
        "音乐节目分数": 0,
        "一位概率": 0,
        "年度奖项积分": 0,
        "本土热度": 0,
        "海外流媒": 0,
        "品牌询盘量": 0,
        "路人盘": 40,
        "核心粉购买力": 0,
        "last_market_result": "",
        "history": [],
    })

    commercial: Dict[str, Any] = Field(default_factory=lambda: {
        "商业安全度": 70,
        "品牌适配度": 45,
        "代言数量": 0,
        "杂志资源": 0,
        "奢侈品关系": 0,
        "个人收入": 0,
        "公司分成比例": 70,
        "粉丝购买力": 0,
        "争议商业风险": 10,
        "last_commercial_note": "",
    })

    contract_terms: Dict[str, Any] = Field(default_factory=lambda: {
        "合约剩余月数": 84,
        "玩家续约意愿": 50,
        "队友续约意向": 50,
        "分成比例": 70,
        "solo权限": 10,
        "演员约权限": 10,
        "创作署名权": 5,
        "休假保障": 25,
        "健康保障": 35,
        "工作室可能性": 0,
        "团体存续概率": 65,
        "last_contract_note": "",
    })

    career_branches: Dict[str, Any] = Field(default_factory=lambda: {
        "acting_path_stage": "未开启",
        "solo_path_stage": "未开启",
        "unit_path_stage": "未开启",
        "creative_path_stage": "未开启",
        "rights_path_stage": "未开启",
        "branch_opportunities": [],
        "branch_history": [],
    })

    current_choices: List[Choice] = Field(default_factory=list)
    flags: List[str] = Field(default_factory=list)
    resolved_flags: List[str] = Field(default_factory=list)
    major_events: List[str] = Field(default_factory=list)
    unresolved_conflicts: List[str] = Field(default_factory=list)
    hidden_notes: List[str] = Field(default_factory=list)

    system_events: List[SystemEvent] = Field(default_factory=list)
    route_history: List[RouteInfo] = Field(default_factory=list)

    last_public_summary: str = ""
    last_private_notes: str = ""

    def is_trainee_stage(self) -> bool:
        text = f"{self.current_stage} {self.current_mainline} {self.current_schedule}"
        return "练习生" in text or "初入公司" in text or "报到" in text

    def as_prompt_dict(self) -> Dict[str, Any]:
        return {
            "turn": self.turn,
            "current_stage": self.current_stage,
            "current_mainline": self.current_mainline,
            "current_schedule": self.current_schedule,
            "next_milestone": self.next_milestone,
            "character": self.character,
            "age_context": self.age_context,
            "relationships": self.relationships,
            "time": self.time,
            "school": self.school,
            "family": self.family,
            "social_context": self.social_context,
            "safety": self.safety,
            "hierarchy": self.hierarchy,
            "profile_tags": self.profile_tags,
            "initial_allocation_log": self.initial_allocation_log,
            "abilities": self.abilities,
            "ability_cooldowns": self.ability_cooldowns,
            "growth_history": self.growth_history[-20:],
            "talents": self.talents,
            "career": self.career,
            "body": self.body,
            "mind": self.mind,
            "company": self.company,
            "team": self.team,
            "fans": self.fans,
            "market": self.market,
            "risks": self.risks,
            "comeback": self.comeback,
            "period": self.period,
            "inner_life": self.inner_life,
            "schedule_profile": self.schedule_profile,
            "progression": self.progression,
            "skill_proficiency": self.skill_proficiency,
            "skill_last_practiced": self.skill_last_practiced,
            "debut": self.debut,
            "ending": self.ending,
            "inner_secrets": self.inner_secrets[-10:],
            "crush_threads": self.crush_threads[-5:],
            "emotional_outlets": self.emotional_outlets,
            "status_effects": self.status_effects,
            "locked_actions": self.locked_actions,
            "active_crises": [c.model_dump() for c in self.active_crises],
            "teammates": self.teammates,
            "important_npcs": self.important_npcs,
            "trainee_life": self.trainee_life,
            "market_scores": self.market_scores,
            "commercial": self.commercial,
            "contract_terms": self.contract_terms,
            "career_branches": self.career_branches,
            "flags": self.flags,
            "major_events": self.major_events,
            "unresolved_conflicts": self.unresolved_conflicts,
            "last_public_summary": self.last_public_summary,
            "recent_system_events": [e.model_dump() for e in self.system_events[-8:]],
        }
