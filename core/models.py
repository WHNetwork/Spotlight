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
        "舞蹈实力": 35,
        "声乐实力": 35,
        "RAP能力": 25,
        "舞台感染力": 35,
        "综艺感": 30,
        "语言能力": 40,
        "形象指数": 45,
        "演技潜力": 20,
        "创作能力": 20,
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

    company: Dict[str, int] = Field(default_factory=lambda: {
        "公司满意度": 50,
        "公司信任度": 45,
        "主推指数": 35,
        "资源倾斜度": 30,
        "危机关注度": 10,
        "合约稳定度": 70,
        "个人议价权": 10,
        "续约倾向": 50,
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

    status_effects: Dict[str, int] = Field(default_factory=dict)
    locked_actions: List[str] = Field(default_factory=list)
    active_crises: List[ActiveCrisis] = Field(default_factory=list)

    teammates: List[Dict[str, Any]] = Field(default_factory=list)
    important_npcs: List[Dict[str, Any]] = Field(default_factory=list)

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
            "status_effects": self.status_effects,
            "locked_actions": self.locked_actions,
            "active_crises": [c.model_dump() for c in self.active_crises],
            "teammates": self.teammates,
            "important_npcs": self.important_npcs,
            "flags": self.flags,
            "major_events": self.major_events,
            "unresolved_conflicts": self.unresolved_conflicts,
            "last_public_summary": self.last_public_summary,
            "recent_system_events": [e.model_dump() for e in self.system_events[-8:]],
        }
