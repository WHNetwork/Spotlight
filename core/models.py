from __future__ import annotations

import calendar
from datetime import date, timedelta
from enum import Enum
from typing import Annotated, Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field, field_validator, model_validator


def _coerce_int_diff(value: Any) -> Dict[str, int]:
    if not isinstance(value, dict):
        return {}
    fixed: Dict[str, int] = {}
    for key, raw in value.items():
        try:
            if isinstance(raw, bool):
                continue
            fixed[str(key)] = int(round(float(raw)))
        except (TypeError, ValueError):
            continue
    return fixed


# ---------------------------------------------------------------------------
# 旧 LLM 协议（暂时保留，与新的权威 GameState 完全分离）
# 引用方：core/llm.py, core/storage.py, core/prompts.py, ui/sections/*
# ---------------------------------------------------------------------------


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

    @field_validator("suggested_diff", mode="before")
    @classmethod
    def coerce_suggested_diff(cls, value: Any) -> Dict[str, int]:
        return _coerce_int_diff(value)


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

    @field_validator("suggested_diff", mode="before")
    @classmethod
    def coerce_suggested_diff(cls, value: Any) -> Dict[str, int]:
        return _coerce_int_diff(value)


# ---------------------------------------------------------------------------
# 新版权威 GameState
#
# 只保存“当前时刻已经确定为真的世界事实”。禁止把剧情文本、日志、
# 长期记忆、Prompt、LLM 推测、diff / flags / private_notes 放进来。
# ---------------------------------------------------------------------------


class MetaState(BaseModel):
    """存档元信息。

    rng_seed：当前存档世界的根随机种子。
    只在新建存档的正式创建流程（core.initial_allocator.allocate_initial_state）
    中通过 secrets.randbits(64) 随机生成一次，之后保存进存档；
    读档时原样恢复，绝不根据角色资料、日期或 save_id 重新生成。
    save_id 是存档身份，rng_seed 是模拟世界随机根，两者语义分离。
    """

    save_id: int = 0
    schema_version: int = 8
    rng_seed: int = 0


class TimeState(BaseModel):
    """真实 Gregorian Calendar 时间基础。

    只保存权威字段 created_date / current_date，
    其余日期信息一律通过派生 property 实时计算，避免冗余矛盾。
    游戏进度唯一权威来源是日期本身。
    """

    created_date: date = Field(default_factory=date.today)
    current_date: date = Field(default_factory=lambda: date.today() + timedelta(days=1))

    @property
    def trainee_day(self) -> int:
        """练习生第几天 = 入社日期到当前日期的天数（建档/入社当天 = 0，次日 = 1）。

        只读派生值，不可单独修改、不序列化。
        """
        return (self.current_date - self.created_date).days

    @property
    def year(self) -> int:
        return self.current_date.year

    @property
    def month(self) -> int:
        return self.current_date.month

    @property
    def day(self) -> int:
        return self.current_date.day

    @property
    def weekday(self) -> int:
        """真实星期（周一=0 … 周日=6）。"""
        return self.current_date.weekday()

    @property
    def weekday_name(self) -> str:
        """真实星期英文名，来自 calendar 标准库。"""
        return calendar.day_name[self.current_date.weekday()]

    @property
    def is_weekend(self) -> bool:
        return self.current_date.weekday() >= 5

    @property
    def days_in_month(self) -> int:
        return calendar.monthrange(self.current_date.year, self.current_date.month)[1]

    @property
    def is_month_end(self) -> bool:
        return self.current_date.day == self.days_in_month

    @property
    def days_until_month_end(self) -> int:
        return self.days_in_month - self.current_date.day


class EducationStatus(str, Enum):
    """角色当前教育状态（简单人物事实）。

    是否继续上学由玩家在创建角色时自己决定；
    创建流程未提供时为 UNSPECIFIED，不允许按年龄等规则自动猜测。
    本轮不建立学校 / 教育系统。
    """

    ENROLLED = "ENROLLED"
    NOT_ENROLLED = "NOT_ENROLLED"
    UNSPECIFIED = "UNSPECIFIED"


class PlayerState(BaseModel):
    """相对稳定的人物事实。动态状态（心情、压力、技能等）一律不放在这里。"""

    name: str = ""
    stage_name: str = ""
    birthday: Optional[date] = None
    starting_age: Optional[int] = None
    nationality: str = ""
    background: str = ""
    personality: str = ""
    appearance: str = ""
    interests: str = ""
    family_background: str = ""
    education_status: EducationStatus = EducationStatus.UNSPECIFIED

    height_cm: Optional[int] = None
    identity_source: str = ""
    mbti: str = ""
    mbti_profile: Dict[str, Any] = Field(default_factory=dict)
    strengths: str = ""
    weak_points: str = ""
    trainee_position: str = ""
    player_wish: str = ""
    story_boundary: str = ""
    extra_notes: str = ""
    avatar: str = ""
    source_tags: List[str] = Field(default_factory=list)

    def age_on(self, on: date) -> Optional[int]:
        """年龄为派生值：由 birthday + 指定日期 实时计算。

        仅当 birthday 真实存在时返回精确年龄；
        birthday 为 None（创建流程只提供年龄）时不伪造具体生日。
        """
        if self.birthday is None:
            return None
        return (
            on.year
            - self.birthday.year
            - int((on.month, on.day) < (self.birthday.month, self.birthday.day))
        )


class SkillState(BaseModel):
    """单个技能状态。

    value：长期真实能力（0–100，locked 技能为 None）；
    xp：当前 Skill Level 向下一级成长的隐藏进度（float）；
    form：近期手感 / 当前熟练状态（0–100，float，允许趋近式增长产生小数）；
    talent：隐藏学习天赋（0–100，只影响学习效率，不决定技能上限）；
    unlocked：是否已被正式发现 / 解锁；
    last_practiced_date：上次正式训练日期。
    """

    value: Optional[int] = None
    xp: float = 0.0
    form: Optional[float] = None
    talent: int = 50
    unlocked: bool = False
    last_practiced_date: Optional[date] = None


class TraitState(BaseModel):
    trait_id: str
    unlocked_date: date
    source_memory_id: str


class SkillsState(BaseModel):
    dance: SkillState = Field(default_factory=SkillState)
    vocal: SkillState = Field(default_factory=SkillState)
    rap: SkillState = Field(default_factory=SkillState)
    stage: SkillState = Field(default_factory=SkillState)
    camera: SkillState = Field(default_factory=SkillState)
    language: SkillState = Field(default_factory=SkillState)
    acting: SkillState = Field(default_factory=SkillState)
    creation: SkillState = Field(default_factory=SkillState)
    traits: List[TraitState] = Field(default_factory=list)


class ActiveCondition(BaseModel):
    """此时此刻仍然存在的身体问题。已恢复的问题从列表移除，历史由数据库记录。"""

    type: str
    severity: int = 50
    started_on: date


class ConditionState(BaseModel):
    """身体 / 心理即时状态。

    八个数值统一 0–100 且允许小数（float，避免逐 Slot 取整产生累积误差）：
    越高越好：energy / voice_condition / sleep_condition / mood / confidence；
    越高越糟：muscle_fatigue / injury_risk / stress。
    active_conditions 只保存“已经真实存在”的身体问题，与风险数值无关。
    """

    energy: float = Field(80.0, ge=0, le=100)
    voice_condition: float = Field(80.0, ge=0, le=100)
    sleep_condition: float = Field(70.0, ge=0, le=100)
    mood: float = Field(70.0, ge=0, le=100)
    confidence: float = Field(55.0, ge=0, le=100)
    muscle_fatigue: float = Field(20.0, ge=0, le=100)
    injury_risk: float = Field(15.0, ge=0, le=100)
    stress: float = Field(35.0, ge=0, le=100)

    active_conditions: List[ActiveCondition] = Field(default_factory=list)


class ConditionSnapshot(BaseModel):
    """八个 Condition 数值的只读快照（不包含 active_conditions）。"""

    energy: float
    voice_condition: float
    sleep_condition: float
    mood: float
    confidence: float
    muscle_fatigue: float
    injury_risk: float
    stress: float


class ConditionResolutionResult(BaseModel):
    """当前 Slot 引起的 Condition 即时变化记录（不持久化进 GameState）。

    以后进入 Daily Log / Memory / DB 历史。
    """

    slot_index: int
    before: ConditionSnapshot
    after: ConditionSnapshot
    training_load_multiplier: float


class MenstrualSymptomTendency(str, Enum):
    """角色长期相对稳定的身体不适倾向（轻量个人 baseline，非医学诊断）。"""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class MenstrualSymptomLevel(str, Enum):
    """某一天实际的不适程度。"""

    NONE = "NONE"
    MILD = "MILD"
    MODERATE = "MODERATE"
    STRONG = "STRONG"


class MenstrualFlowLevel(str, Enum):
    """某一天的实际经量（与 symptom 独立）。"""

    NONE = "NONE"
    LIGHT = "LIGHT"
    MODERATE = "MODERATE"
    HEAVY = "HEAVY"


class MenstrualPhase(str, Enum):
    """由 cycle day 推导的近似阶段（游戏层 context，不直接修改 Condition）。"""

    MENSTRUAL = "MENSTRUAL"
    FOLLICULAR = "FOLLICULAR"
    OVULATORY = "OVULATORY"
    LUTEAL = "LUTEAL"


class MenstrualCycleState(BaseModel):
    """生理周期持久世界事实（独立 Domain，不属于 Calendar / Condition / Player）。

    日期唯一权威来源是 TimeState.current_date；cycle_start_date 是当前周期的
    日期 anchor（cycle_day = (target_date - cycle_start_date).days + 1）。
    不持久化 cycle_day / phase / flow / symptom —— 全部由
    MenstrualCycleState + target_date + rng_seed 稳定推导。
    """

    enabled: bool = True
    baseline_cycle_length: int = Field(ge=21, le=35)
    baseline_period_length: int = Field(ge=3, le=7)
    symptom_tendency: MenstrualSymptomTendency
    cycle_start_date: date
    cycle_index: int = Field(default=0, ge=0)
    current_cycle_length: int = Field(ge=21, le=35)
    current_period_length: int = Field(ge=3, le=7)
    last_physiology_applied_date: Optional[date] = None

    @model_validator(mode="after")
    def _validate_cycle_state(self) -> "MenstrualCycleState":
        if self.current_period_length >= self.current_cycle_length:
            raise ValueError("current_period_length 必须小于 current_cycle_length。")
        return self


class MenstrualDailyState(BaseModel):
    """某一天的周期 / 生理 daily state（transient：可由 cycle + date + seed 重新推导）。"""

    game_date: date
    cycle_index: int
    cycle_day: int
    cycle_length: int
    phase: MenstrualPhase
    is_menstruating: bool
    period_day: Optional[int] = None
    period_length: Optional[int] = None
    flow_level: MenstrualFlowLevel
    symptom_level: MenstrualSymptomLevel
    days_until_next_period: int
    is_premenstrual_window: bool

    @model_validator(mode="after")
    def _validate_daily_state(self) -> "MenstrualDailyState":
        if not (1 <= self.cycle_day <= self.cycle_length):
            raise ValueError(f"cycle_day 必须在 1..{self.cycle_length} 内（当前 {self.cycle_day}）。")
        if self.is_menstruating:
            if self.period_day is None or not (1 <= self.period_day <= (self.period_length or 0)):
                raise ValueError("is_menstruating 时 period_day 必须存在且在经期内。")
            if self.flow_level == MenstrualFlowLevel.NONE:
                raise ValueError("is_menstruating 时 flow 不能为 NONE。")
        else:
            if self.period_day is not None or self.flow_level != MenstrualFlowLevel.NONE:
                raise ValueError("非经期时 period_day 必须为 None 且 flow 为 NONE。")
        return self


class MenstrualDailyEffectResult(BaseModel):
    """每天一次 applied 的生理影响结果（transient，不入 DB）。"""

    game_date: date
    daily_state: MenstrualDailyState
    condition_before: ConditionSnapshot
    condition_after: ConditionSnapshot


class TraineeState(BaseModel):
    """练习生在公司的当前位置。

    所有角色都从入社第一天开始，正式入社日期即 TimeState.created_date，
    不再单独保存 joined_date。

    评价类数据只保留正式 Monthly Evaluation 的结果：
    latest_evaluation_score / latest_evaluation_date（首次月评前为 None，即真正 Unknown）。
    已删除无可靠机制来源的 company_evaluation / attendance / discipline /
    teacher_impression（不保留 50 = 未知还是一般的模糊状态）。
    """

    status: str = "active"
    training_level: int = 1
    latest_evaluation_score: Optional[float] = None
    latest_evaluation_date: Optional[date] = None


class CompanySize(str, Enum):
    """公司规模。只用于生成 resource_level 的范围，不决定培养方向/强度/管理方式/课程数量。"""

    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    LARGE = "LARGE"


class TrainingStyle(str, Enum):
    """公司培养方向（语义标签）。"""

    BALANCED = "BALANCED"
    PERFORMANCE = "PERFORMANCE"
    VOCAL = "VOCAL"
    HIPHOP = "HIPHOP"
    GLOBAL = "GLOBAL"


class ManagementStyle(str, Enum):
    """公司管理练习生的方式。本步骤不参与课程生成，只保存公司事实。"""

    BALANCED = "BALANCED"
    STRICT = "STRICT"
    RESULTS_DRIVEN = "RESULTS_DRIVEN"
    SUPPORTIVE = "SUPPORTIVE"


class CompanyCourse(str, Enum):
    """公司课程类型。课程生成逻辑内部一律使用该枚举，不使用自由字符串。"""

    DANCE = "DANCE"
    VOCAL = "VOCAL"
    RAP = "RAP"
    STAGE = "STAGE"
    CAMERA = "CAMERA"
    LANGUAGE = "LANGUAGE"
    FITNESS = "FITNESS"


class TrainingWeights(BaseModel):
    """培养权重：公司实际分配给各类训练课程的比例。

    由 TrainingStyle 对应的官方基础模板填充（见 core/company_curriculum.py），
    每组权重总和必须为 1.0。默认 0.0 仅表示“尚未填充”，不代表任何课程策略。
    """

    dance: float = 0.0
    vocal: float = 0.0
    rap: float = 0.0
    stage: float = 0.0
    camera: float = 0.0
    language: float = 0.0
    fitness: float = 0.0


class CompanyState(BaseModel):
    """公司世界事实。

    六个维度语义独立，互不推导：
    size 公司规模；training_style 培养方向；training_intensity 同类课程的实际训练负荷；
    resource_level 师资 / 设施 / 专业指导等训练资源；management_style 管理方式；
    training_weights 公司实际分配给各类课程的比例。
    规模不决定培养风格 / 强度 / 管理方式 / 课程数量。
    """

    name: str = ""
    size: CompanySize = CompanySize.MEDIUM
    training_style: Optional[TrainingStyle] = None
    training_intensity: int = 50
    resource_level: int = 50
    management_style: Optional[ManagementStyle] = None
    training_weights: Optional[TrainingWeights] = None


class NPCRole(str, Enum):
    """NPC 基础身份类型。老师的专业领域用 specialty 表达，不扩展 role。"""

    TRAINEE = "TRAINEE"
    TEACHER = "TEACHER"
    STAFF = "STAFF"
    MANAGER = "MANAGER"


class NPCCharacterLevel(str, Enum):
    """Character Facts 三档水平（无连续伪精确心理数值）。"""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class NPCSpeechVerbosity(str, Enum):
    """NPC 通常说话多少的稳定倾向（不是每次对白固定长度）。"""

    BRIEF = "BRIEF"
    BALANCED = "BALANCED"
    TALKATIVE = "TALKATIVE"


class NPCBehaviorHabit(str, Enum):
    """通用生活质感小习惯（不参与任何 mechanics）。"""

    TAKES_NOTES = "TAKES_NOTES"
    KEEPS_DRINK_NEARBY = "KEEPS_DRINK_NEARBY"
    TIDIES_SMALL_ITEMS = "TIDIES_SMALL_ITEMS"
    CHECKS_PHONE_DURING_BREAKS = "CHECKS_PHONE_DURING_BREAKS"
    ARRIVES_A_LITTLE_EARLY = "ARRIVES_A_LITTLE_EARLY"
    TAPS_RHYTHM_WHEN_IDLE = "TAPS_RHYTHM_WHEN_IDLE"
    HUMS_WHEN_FOCUSED = "HUMS_WHEN_FOCUSED"
    STRETCHES_WHILE_WAITING = "STRETCHES_WHILE_WAITING"
    WATCHES_BEFORE_JOINING = "WATCHES_BEFORE_JOINING"
    PLAYS_WITH_PEN_OR_BOTTLE_CAP = "PLAYS_WITH_PEN_OR_BOTTLE_CAP"
    RUBS_NECK_WHEN_TIRED = "RUBS_NECK_WHEN_TIRED"
    PACKS_THINGS_CAREFULLY = "PACKS_THINGS_CAREFULLY"


class NPCCharacterFacts(BaseModel):
    """NPC 稳定写作指导事实（100% narrative-only；永不作为 mechanics modifier）。

    character_facts 只回答“同样的机械事实，这个 NPC 会以什么方式表现出来”。
    """

    social_energy: NPCCharacterLevel
    warmth: NPCCharacterLevel
    directness: NPCCharacterLevel
    expressiveness: NPCCharacterLevel
    conscientiousness: NPCCharacterLevel
    humor_tendency: NPCCharacterLevel
    competitive_drive: Optional[NPCCharacterLevel] = None
    speech_verbosity: NPCSpeechVerbosity
    habits: Tuple[NPCBehaviorHabit, ...] = ()

    @model_validator(mode="after")
    def _validate_facts(self) -> "NPCCharacterFacts":
        if len(self.habits) != 2:
            raise ValueError(f"habits 必须恰好 2 个（当前 {len(self.habits)}）。")
        if len(set(self.habits)) != len(self.habits):
            raise ValueError("habits 不允许重复。")
        return self


class NPCProfile(BaseModel):
    """最小 NPC 档案（随 GameState 持久化，不建独立 NPC 表）。

    只回答：这个人是谁 / 什么角色 / 是否仍有效 / 老师主要教什么领域 /
    稳定写作指导事实（character_facts）。
    不包含生日 / MBTI / backstory / 日程 / 隐藏动机等完整人物模拟字段。
    """

    npc_id: str
    name: str
    role: NPCRole
    specialty: Optional[CompanyCourse] = None
    active: bool = True
    character_facts: NPCCharacterFacts

    @model_validator(mode="after")
    def _validate_profile(self) -> "NPCProfile":
        if not self.npc_id or not str(self.npc_id).strip():
            raise ValueError("npc_id 必须非空。")
        if not self.name or not str(self.name).strip():
            raise ValueError("name 必须非空。")
        if self.role != NPCRole.TEACHER and self.specialty is not None:
            raise ValueError("非 TEACHER 的 NPC 不允许设置 specialty。")
        if self.role != NPCRole.TRAINEE:
            if self.character_facts.competitive_drive is not None:
                raise ValueError("非 TRAINEE 的 character_facts.competitive_drive 必须为 None。")
        else:
            if self.character_facts.competitive_drive is None:
                raise ValueError("TRAINEE 的 character_facts.competitive_drive 必须存在。")
        return self


class RelationshipState(BaseModel):
    """双方当前关系事实（dict key = npc_id，不重复保存 npc_id）。

    四维语义独立：familiarity 熟悉程度 / closeness 私人亲近 / trust 信任 /
    tension 张力（越高越差）。
    新关系初始值：familiarity=5（至少接触过）、closeness/trust/tension=0
    （尚未建立亲近、信任，也没有默认矛盾）——不使用假中立 50。
    """

    familiarity: float = Field(5.0, ge=0, le=100)
    closeness: float = Field(0.0, ge=0, le=100)
    trust: float = Field(0.0, ge=0, le=100)
    tension: float = Field(0.0, ge=0, le=100)
    last_interaction_date: Optional[date] = None


class RelationshipInteractionResult(BaseModel):
    """一次 SOCIAL 关系互动机械上发生了什么（作为 SlotResolutionResult 组成部分持久化）。

    即使 closeness / trust / tension 不变也记录 before/after，
    表示这次互动的完整结构化事实。
    """

    npc_id: str
    interaction_date: date
    familiarity_before: float
    familiarity_after: float
    familiarity_gain: float
    closeness_before: float
    closeness_after: float
    trust_before: float
    trust_after: float
    tension_before: float
    tension_after: float


class RelationshipSignal(str, Enum):
    """结构化关系经历类型（世界经历的机械解释，不是玩家可购买的数值操作）。

    未来 Event / LLM 只能引用这些预定义 Signal，
    禁止直接传任意 delta。
    """

    CASUAL_CONTACT = "CASUAL_CONTACT"
    SHARED_POSITIVE_EXPERIENCE = "SHARED_POSITIVE_EXPERIENCE"
    RELIABILITY_CONFIRMED = "RELIABILITY_CONFIRMED"
    FRICTION = "FRICTION"
    TRUST_BREACH = "TRUST_BREACH"
    REPAIR = "REPAIR"
    DISTANCING = "DISTANCING"


class RelationshipDevelopmentResult(BaseModel):
    """一次结构化关系经历在四维上的机械结果（transient，不入 DB）。

    数值全部来自 resolver 基于 before snapshot 的计算；不保存 delta
    （after - before 可推）、不保存原因/narrative/source。
    """

    npc_id: str
    interaction_date: date
    signal: RelationshipSignal
    familiarity_before: float = Field(ge=0, le=100)
    familiarity_after: float = Field(ge=0, le=100)
    closeness_before: float = Field(ge=0, le=100)
    closeness_after: float = Field(ge=0, le=100)
    trust_before: float = Field(ge=0, le=100)
    trust_after: float = Field(ge=0, le=100)
    tension_before: float = Field(ge=0, le=100)
    tension_after: float = Field(ge=0, le=100)


# ---------------------------------------------------------------------------
# 事件触发基础枚举（原 event_models 迁入，避免 models ↔ event_models 循环）
# ---------------------------------------------------------------------------


class EventTriggerMode(str, Enum):
    DETERMINISTIC = "DETERMINISTIC"
    PROBABILISTIC = "PROBABILISTIC"
    LLM_ASSISTED = "LLM_ASSISTED"


class EventCategory(str, Enum):
    SCHEDULED = "SCHEDULED"
    CONDITIONAL = "CONDITIONAL"
    OPPORTUNITY = "OPPORTUNITY"
    RELATIONSHIP = "RELATIONSHIP"
    CHAIN = "CHAIN"


class EventTier(str, Enum):
    MINOR = "MINOR"
    MAJOR = "MAJOR"


class EventInteractionMode(str, Enum):
    NON_INTERRUPTIVE = "NON_INTERRUPTIVE"
    INTERRUPTIVE = "INTERRUPTIVE"


# ---------------------------------------------------------------------------
# Step 15：Event Effects / Domain Actions
# ---------------------------------------------------------------------------


class ConditionSignal(str, Enum):
    """事件可引用的心理 Condition 领域事实（一个 Signal 只表达一个事实）。"""

    MOOD_LIFT = "MOOD_LIFT"
    MOOD_HIT = "MOOD_HIT"
    CONFIDENCE_GAIN = "CONFIDENCE_GAIN"
    CONFIDENCE_HIT = "CONFIDENCE_HIT"
    STRESS_INCREASE = "STRESS_INCREASE"
    STRESS_RELIEF = "STRESS_RELIEF"


class ConditionSignalResult(BaseModel):
    """一次心理 Condition Signal 的机械结果（transient）。"""

    signal: ConditionSignal
    condition_before: ConditionSnapshot
    condition_after: ConditionSnapshot


class EventActionKind(str, Enum):
    RELATIONSHIP = "RELATIONSHIP"
    CONDITION = "CONDITION"


class RelationshipActionTarget(str, Enum):
    CONTEXT_NPC = "CONTEXT_NPC"
    EXPLICIT_NPC = "EXPLICIT_NPC"


class RelationshipEventAction(BaseModel):
    kind: EventActionKind = EventActionKind.RELATIONSHIP
    target: RelationshipActionTarget
    signal: RelationshipSignal
    npc_id: Optional[str] = None

    @model_validator(mode="after")
    def _validate_target(self) -> "RelationshipEventAction":
        if self.target == RelationshipActionTarget.CONTEXT_NPC:
            if self.npc_id is not None:
                raise ValueError("CONTEXT_NPC action 不允许携带 npc_id。")
        else:
            if not self.npc_id or not str(self.npc_id).strip():
                raise ValueError("EXPLICIT_NPC action 必须携带非空 npc_id。")
        return self


class ConditionEventAction(BaseModel):
    kind: EventActionKind = EventActionKind.CONDITION
    signal: ConditionSignal


EventDomainAction = Annotated[
    Union[RelationshipEventAction, ConditionEventAction],
    Field(discriminator="kind"),
]


class EventEffectKind(str, Enum):
    RELATIONSHIP = "RELATIONSHIP"
    CONDITION = "CONDITION"


class AppliedRelationshipEffect(BaseModel):
    kind: EventEffectKind = EventEffectKind.RELATIONSHIP
    result: RelationshipDevelopmentResult


class AppliedConditionEffect(BaseModel):
    kind: EventEffectKind = EventEffectKind.CONDITION
    result: ConditionSignalResult


EventAppliedEffect = Annotated[
    Union[AppliedRelationshipEffect, AppliedConditionEffect],
    Field(discriminator="kind"),
]


class PendingEventState(BaseModel):
    """世界此刻正在等待玩家处理的未解决事件（属于 GameState 当前事实）。

    context_npc_id：触发时绑定的 NPC（持久保存，Choice 时绝不重新推断）。
    """

    event_instance_id: str
    event_id: str
    triggered_date: date
    trigger_slot_index: int
    category: EventCategory
    trigger_mode: EventTriggerMode
    tier: EventTier
    interaction_mode: EventInteractionMode
    priority: int
    base_probability: float
    soft_relevance: Optional[float] = None
    effective_probability: float
    available_choice_ids: Tuple[str, ...] = ()
    context_npc_id: Optional[str] = None

    @model_validator(mode="after")
    def _validate_interruptive(self) -> "PendingEventState":
        if self.interaction_mode != EventInteractionMode.INTERRUPTIVE:
            raise ValueError("PendingEventState.interaction_mode 必须为 INTERRUPTIVE。")
        return self


class EventResult(BaseModel):
    """已经完整解决的历史事件（写入 event_history，不进入 GameState）。

    applied_effects 保存本次真正执行完成的 Domain Results
    （RelationshipDevelopmentResult / ConditionSignalResult）。
    """

    event_instance_id: str
    event_id: str
    game_date: date
    trigger_slot_index: int
    category: EventCategory
    trigger_mode: EventTriggerMode
    tier: EventTier
    interaction_mode: EventInteractionMode
    priority: int
    base_probability: float
    soft_relevance: Optional[float] = None
    effective_probability: float
    choice_id: Optional[str] = None
    context_npc_id: Optional[str] = None
    applied_effects: List[EventAppliedEffect] = Field(default_factory=list)


class FreeActionKind(str, Enum):
    """FREE Slot 的一级结构化行动类型。"""

    TRAIN = "TRAIN"
    SOCIAL = "SOCIAL"
    RECOVER = "RECOVER"
    EXPLORE = "EXPLORE"
    PERSONAL = "PERSONAL"


class SkillId(str, Enum):
    """正式 Skill 标识，与 SkillsState 字段一一对应。

    不包含 fitness / variety / social / resilience。
    """

    DANCE = "dance"
    VOCAL = "vocal"
    RAP = "rap"
    STAGE = "stage"
    CAMERA = "camera"
    LANGUAGE = "language"
    ACTING = "acting"
    CREATION = "creation"


class TrainingSource(str, Enum):
    """技能训练来源。"""

    COMPANY = "COMPANY"
    SELF_TRAINING = "SELF_TRAINING"


class SkillTrainingResult(BaseModel):
    """一次技能训练实际发生的记录（纯结果对象，不持久化进 GameState）。

    数值全部来自真实计算：读取 SkillState → 计算倍率 → 计算 effective_xp
    → 更新 SkillState → 构造本结果。以后进入 Daily Log / Memory / DB 历史。
    """

    skill: SkillId
    source: TrainingSource
    base_xp: float
    talent_multiplier: float
    repetition_index: int
    repetition_multiplier: float
    company_quality_multiplier: float
    condition_readiness: float
    condition_multiplier: float
    effective_xp: float
    value_before: int
    value_after: int
    xp_before: float
    xp_after: float
    form_before: float
    form_after: float
    levels_gained: int


class OvernightConditionResult(BaseModel):
    """跨夜 Condition 结算的简明事实（transient，不持久化）。"""

    before: ConditionSnapshot
    after: ConditionSnapshot
    sleep_target: float


class SkillFormSettlementResult(BaseModel):
    """单个技能跨日 Form 结算结果（transient，不持久化）。"""

    skill: SkillId
    unlocked: bool
    practiced_today: bool
    form_before: Optional[float] = None
    form_after: Optional[float] = None


class ExplorationDomain(str, Enum):
    """EXPLORE 第一版只允许的两个潜在方向。"""

    ACTING = "acting"
    CREATION = "creation"


class PersonalActionType(str, Enum):
    """PERSONAL 第一版允许的四个结构化个人生活 subtype。"""

    STUDY = "STUDY"
    FAMILY = "FAMILY"
    LEISURE = "LEISURE"
    OUTING = "OUTING"


class SlotKind(str, Enum):
    """基础时间段类型：休息 / 学校 / 公司 / 自由。"""

    REST = "REST"
    SCHOOL = "SCHOOL"
    COMPANY = "COMPANY"
    FREE = "FREE"


class SlotStatus(str, Enum):
    """时间段进度状态。本轮只有两种：待进行 / 已完成。"""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"


class FreeAction(BaseModel):
    """玩家在 FREE Slot 选择的结构化行动（Action Intent）。

    只表达“玩家想做什么”，不携带任何结果 / 数值 / 概率；
    第一版为按钮制，不允许自由文本。
    每种 kind 只允许对应的一组参数，非法组合直接失败。
    """

    kind: FreeActionKind
    skill: Optional[SkillId] = None
    target_npc_id: Optional[str] = None
    exploration_domain: Optional[ExplorationDomain] = None
    personal_type: Optional[PersonalActionType] = None

    @model_validator(mode="after")
    def _validate_action_combo(self) -> "FreeAction":
        kind = self.kind

        def others_present(*excluded: object) -> list[str]:
            fields = [
                (self.skill is not None, "skill"),
                (self.target_npc_id is not None, "target_npc_id"),
                (self.exploration_domain is not None, "exploration_domain"),
                (self.personal_type is not None, "personal_type"),
            ]
            return [name for present, name in fields if present and name not in excluded]

        if kind == FreeActionKind.TRAIN:
            if self.skill is None:
                raise ValueError("TRAIN 必须携带 skill。")
            extra = others_present("skill")
            if extra:
                raise ValueError(f"TRAIN 不允许携带多余字段：{', '.join(extra)}。")
        elif kind == FreeActionKind.SOCIAL:
            if self.target_npc_id is None or not str(self.target_npc_id or "").strip():
                raise ValueError("SOCIAL 必须携带非空 target_npc_id。")
            extra = others_present("target_npc_id")
            if extra:
                raise ValueError(f"SOCIAL 不允许携带多余字段：{', '.join(extra)}。")
        elif kind == FreeActionKind.RECOVER:
            extra = others_present()
            if extra:
                raise ValueError(f"RECOVER 不允许携带任何额外字段：{', '.join(extra)}。")
        elif kind == FreeActionKind.EXPLORE:
            if self.exploration_domain is None:
                raise ValueError("EXPLORE 必须携带 exploration_domain。")
            extra = others_present("exploration_domain")
            if extra:
                raise ValueError(f"EXPLORE 不允许携带多余字段：{', '.join(extra)}。")
        elif kind == FreeActionKind.PERSONAL:
            if self.personal_type is None:
                raise ValueError("PERSONAL 必须携带 personal_type。")
            extra = others_present("personal_type")
            if extra:
                raise ValueError(f"PERSONAL 不允许携带多余字段：{', '.join(extra)}。")
        return self


class SlotResolutionResult(BaseModel):
    """刚刚这一个 Slot 的机械世界事实（不持久化进 GameState）。

    保存执行时该 Slot 的 Action / Course 快照（company_course / free_action）
    与两个领域结算结果（skill_result / condition_result）。
    completed 恒为 True：统一 Resolver 只有在全部 Resolution 成功并
    mark_completed 后才构造本结果；失败直接抛错，不产生半成品。
    以后由 Daily Log / Database History 负责持久化结构化 Slot 事实。
    """

    slot_index: int
    slot_kind: SlotKind
    company_course: Optional[CompanyCourse] = None
    free_action: Optional[FreeAction] = None
    skill_result: Optional[SkillTrainingResult] = None
    condition_result: ConditionResolutionResult
    relationship_result: Optional[RelationshipInteractionResult] = None
    completed: bool

    @model_validator(mode="after")
    def _validate_relationship_consistency(self) -> "SlotResolutionResult":
        is_social = (
            self.slot_kind == SlotKind.FREE
            and self.free_action is not None
            and self.free_action.kind == FreeActionKind.SOCIAL
        )
        if is_social:
            if self.relationship_result is None:
                raise ValueError("SOCIAL Slot 必须带有 relationship_result。")
            if self.relationship_result.npc_id != self.free_action.target_npc_id:
                raise ValueError("relationship_result.npc_id 必须等于 free_action.target_npc_id。")
        else:
            if self.relationship_result is not None:
                raise ValueError("非 SOCIAL Slot 不允许携带 relationship_result。")
        return self


class TimeSlotState(BaseModel):
    """一天的 8 个有序时间段之一。

    index：0–7，一天内唯一，从白天到一天结束依次推进。
    kind：只能是最基础的四种类型之一。
    status：PENDING / COMPLETED。
    company_course：仅 COMPANY Slot 允许携带（可暂时为 None，表示课程未填入）。
    free_action：仅 FREE Slot 允许携带（可暂时为 None，表示尚未选择行动）。
    时间格不绑定具体钟点。
    """

    index: int = Field(ge=0, le=7)
    kind: SlotKind
    status: SlotStatus = SlotStatus.PENDING
    company_course: Optional[CompanyCourse] = None
    free_action: Optional[FreeAction] = None

    @model_validator(mode="after")
    def _validate_kind_content(self) -> "TimeSlotState":
        if self.kind == SlotKind.COMPANY:
            if self.free_action is not None:
                raise ValueError("COMPANY Slot 不能携带 free_action。")
        elif self.kind == SlotKind.FREE:
            if self.company_course is not None:
                raise ValueError("FREE Slot 不能携带 company_course。")
        else:
            if self.company_course is not None or self.free_action is not None:
                raise ValueError(f"{self.kind.value} Slot 不能携带 company_course / free_action。")
        return self


class DayState(BaseModel):
    """一天的 8 个有序时间段。

    slots 是一天进度的唯一权威来源；
    current_slot / completed_slots / is_day_complete / remaining_slots
    全部由 slots 实时派生，不单独保存，避免互相矛盾。
    本状态不保存日期：当前游戏日期只属于 GameState.time.current_date。

    数据不变量：slots 只允许两种形态——
    A. slots == []（当天尚未生成基础日程，例如 education_status 未确定时）；
    B. 完整且严格有序的 8 个 Slot（index 严格为 [0,1,2,3,4,5,6,7]）。
    重复 / 顺序错误 / 缺失 / 多余 / 1–7 个或 9 个以上，一律拒绝，不自动修复。
    """

    slots: List[TimeSlotState] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_day_slots(self) -> "DayState":
        if not self.slots:
            return self
        if len(self.slots) != 8:
            raise ValueError(f"DayState 必须包含完整的 8 个 Slot（当前 {len(self.slots)} 个），不允许部分初始化。")
        actual = [slot.index for slot in self.slots]
        expected = [0, 1, 2, 3, 4, 5, 6, 7]
        if actual != expected:
            raise ValueError(f"DayState 的 Slot index 必须严格按 0..7 顺序且不重复不缺失（当前 {actual}）。")
        return self

    @property
    def current_slot(self) -> Optional[int]:
        """第一个 status == PENDING 的 slot index；全部完成或未初始化时为 None。"""
        for slot in self.slots:
            if slot.status == SlotStatus.PENDING:
                return slot.index
        return None

    @property
    def completed_slots(self) -> List[int]:
        """已完成 slot 的 index 列表。"""
        return [slot.index for slot in self.slots if slot.status == SlotStatus.COMPLETED]

    @property
    def is_day_complete(self) -> bool:
        """8 个 slot 全部 COMPLETED 才算完成。"""
        return len(self.slots) == 8 and all(slot.status == SlotStatus.COMPLETED for slot in self.slots)

    @property
    def remaining_slots(self) -> int:
        """尚未完成（PENDING）的 slot 数量。"""
        return sum(1 for slot in self.slots if slot.status == SlotStatus.PENDING)

    def mark_completed(self, index: int) -> None:
        """严格按时间顺序完成当前 Slot。

        规则：
        1. DayState 必须已初始化为完整 8 Slot；slots 为空（未初始化）时明确失败，
           不会自动生成日程；
        2. 只能完成第一个 PENDING（即 current_slot）的 Slot；
        3. 不允许跳过未来 Slot、不允许补完成之前的 Slot、
           不允许重新完成已经 COMPLETED 的 Slot；
        4. 8 个 Slot 全部完成后，任何 mark_completed 调用都明确失败；
        5. 只修改 Slot 状态，不触发数值效果，不推进日期；
           日终结算（状态结算 / 日志 / Memory / 恢复 / 日期推进）由后续步骤统一负责。
        """
        if not self.slots:
            raise ValueError("DayState 尚未初始化（slots 为空）：无法标记完成，请先用 core.day_schedule 构造基础日程。")
        if self.is_day_complete:
            raise ValueError("今天 8 个 Slot 已全部完成，不能再标记完成任何 Slot。")
        current = self.current_slot
        if current is None:
            raise ValueError("DayState 没有可完成的 Slot（状态异常）。")
        if index != current:
            raise ValueError(f"Slot 必须按时间顺序完成：当前只能完成 index={current}，不能完成 index={index}。")
        for slot in self.slots:
            if slot.index == index:
                slot.status = SlotStatus.COMPLETED
                return
        raise IndexError(f"day slot index out of range: {index}")


class GameState(BaseModel):
    meta: MetaState = Field(default_factory=MetaState)
    time: TimeState = Field(default_factory=TimeState)
    player: PlayerState = Field(default_factory=PlayerState)
    skills: SkillsState = Field(default_factory=SkillsState)
    condition: ConditionState = Field(default_factory=ConditionState)
    trainee: TraineeState = Field(default_factory=TraineeState)
    company: CompanyState = Field(default_factory=CompanyState)
    npcs: Dict[str, NPCProfile] = Field(default_factory=dict)
    relationships: Dict[str, RelationshipState] = Field(default_factory=dict)
    day: DayState = Field(default_factory=DayState)
    pending_event: Optional[PendingEventState] = None
    menstrual_cycle: Optional[MenstrualCycleState] = None

    @model_validator(mode="after")
    def _validate_npc_relationship_consistency(self) -> "GameState":
        if set(self.npcs.keys()) != set(self.relationships.keys()):
            raise ValueError("npcs 与 relationships 的 key 集合必须完全一致（禁止单侧存在）。")
        for npc_id, profile in self.npcs.items():
            if profile.npc_id != npc_id:
                raise ValueError(f"NPCProfile.npc_id 必须等于 dict key：{npc_id}。")
        return self

    @property
    def save_name(self) -> str:
        return self.player.stage_name or self.player.name or "星光练习室存档"

    def is_trainee_stage(self) -> bool:
        return True

    def as_prompt_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Daily Writing Artifacts（player-visible generated text 的持久化记录；
# 非 GameState world fact，不进入 GameState；仅存玩家可见最终文本与来源 provider）
# ---------------------------------------------------------------------------


class DailyWritingArtifactType(str, Enum):
    DAILY_NARRATIVE = "DAILY_NARRATIVE"
    DIARY = "DIARY"


class DailyWritingArtifactRecord(BaseModel):
    save_id: int
    game_date: date
    artifact_type: DailyWritingArtifactType
    content: str
    provider_name: str
    created_at: str


class EventSceneArtifactRecord(BaseModel):
    """Interruptive Event Setup Scene 的持久化记录（非 GameState；仅玩家可见文本）。"""

    save_id: int
    event_instance_id: str
    game_date: date
    event_id: str
    slot_index: int
    content: str
    provider_name: str
    created_at: str
