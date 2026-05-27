from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field
from core.models import GameState, SystemEvent


class ActionBlockedError(Exception):
    def __init__(self, message: str, suggestions: List[str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.suggestions = suggestions or []


class ActionValidationResult(BaseModel):
    allowed: bool = True
    consumes_turn: bool = True
    original_action: str
    normalized_action: str
    warnings: List[str] = Field(default_factory=list)
    blocked_reason: str = ""
    system_events: List[SystemEvent] = Field(default_factory=list)


HIGH_INTENSITY_WORDS = ["高强度", "加练", "继续练", "硬撑", "不休息", "练到", "熬夜训练"]
FORMAL_IDOL_FORBIDDEN = ["打歌", "一位", "大赏", "颁奖", "演唱会", "世巡", "续约", "代言", "品牌活动"]
FORMAL_RESOURCE_WORDS = ["mv", "MV", "镜头", "part", "center", "killing", "分量", "资源", "主推"]
COMEBACK_WORDS = ["回归", "主打", "概念", "风格", "制作", "demo", "作词", "作曲"]
SOLO_WORDS = ["solo", "单飞", "个人专辑", "演员转型"]


def _event(code: str, title: str, desc: str, severity: str = "warning") -> SystemEvent:
    return SystemEvent(
        code=code,
        title=title,
        severity=severity,
        description=desc,
        source_system="action_validator",
        new_flags=[title],
        tags=["validator"],
    )


def validate_action(state: GameState, action: str) -> ActionValidationResult:
    text = action.strip()
    lower = text.lower()
    result = ActionValidationResult(original_action=action, normalized_action=action)

    # 强制健康闸门
    if state.body.get("体力", 100) < 20 and any(w in text for w in HIGH_INTENSITY_WORDS):
        raise ActionBlockedError(
            "当前体力低于 20，不能继续执行高强度训练。你需要先休息、康复、就医或向经纪人说明状态。",
            ["选择休息恢复体力", "申请物理治疗", "告诉经纪人身体状态", "降低训练强度"]
        )

    if state.body.get("伤病风险", 0) > 90 and any(w in text for w in HIGH_INTENSITY_WORDS + ["舞蹈", "练舞"]):
        raise ActionBlockedError(
            "伤病风险已经高于 90，继续训练会直接触发严重伤病。当前行动被阻止。",
            ["去医院检查", "申请休养", "和老师讨论降低动作强度", "告诉队友真实状态"]
        )

    if state.mind.get("精神压力", 0) > 95 and any(w in text for w in ["直播", "回应", "公关", "综艺", "考核"]):
        raise ActionBlockedError(
            "精神压力已经接近崩溃阈值，当前不适合进行公开回应、直播、综艺或高压考核。",
            ["先做心理评估", "找可信队友谈话", "让公司代为回应", "申请暂缓"]
        )

    # 状态效果锁
    if state.status_effects.get("强制休养", 0) > 0 and any(w in text for w in HIGH_INTENSITY_WORDS + ["练舞", "舞蹈", "考核"]):
        raise ActionBlockedError(
            f"你仍处于强制休养状态，剩余 {state.status_effects.get('强制休养')} 回合。不能进行高强度训练或考核。",
            ["休息", "康复训练", "和经纪人沟通后续安排", "整理歌词或写日记"]
        )

    is_trainee = state.is_trainee_stage()

    if is_trainee:
        if any(w in text for w in SOLO_WORDS):
            result.warnings.append("练习生阶段不能进行 solo / 单飞 / 演员转型。行动已转化为个人展示与职业方向探索。")
            result.normalized_action = "我想在练习生阶段争取一次个人展示机会，并向老师询问我的长期职业定位。"
            result.system_events.append(_event("action_stage_rewrite_solo", "阶段门控：solo 行动已降级", "练习生阶段的 solo/单飞/转型请求被改写为个人展示机会与职业定位咨询。"))

        elif any(w in text for w in FORMAL_RESOURCE_WORDS):
            result.warnings.append("练习生阶段没有正式 MV 镜头、打歌 center 或回归 part。行动已转化为月末考核展示位置/评估录像机会。")
            result.normalized_action = "我向老师和经纪人询问月末考核展示位置、评估录像表现机会，以及自己能否在考核曲里承担更清晰的展示段落。"
            result.system_events.append(_event("action_stage_rewrite_resource", "阶段门控：正式资源行动已降级", "正式爱豆资源请求被改写为练习生考核展示机会。"))

        elif any(w in text for w in COMEBACK_WORDS):
            result.warnings.append("练习生阶段不能决定正式回归风格。行动已转化为作词作曲训练、demo 练习或出道组概念课。")
            result.normalized_action = "我想参加作词作曲训练，尝试写一个练习用 demo，并询问老师公司对出道组概念课的要求。"
            result.system_events.append(_event("action_stage_rewrite_comeback", "阶段门控：回归制作行动已降级", "正式回归制作请求被改写为练习生创作训练和出道组概念学习。"))

        elif any(w in text for w in FORMAL_IDOL_FORBIDDEN):
            raise ActionBlockedError(
                "当前仍是练习生阶段，不能执行正式爱豆阶段行为，如打歌、一位、大赏、续约、代言、演唱会等。",
                ["询问月末考核安排", "争取练习生评估展示机会", "向老师请教定位", "处理练习生阶段的人际关系"]
            )


    # 年龄、出行和安全边界。未成年练习生不能深夜私自出入或赴陌生邀约。
    private_outing_words = ["偷偷出门", "私自出门", "自己出门", "凌晨出门", "深夜出门", "自己去便利店", "独自去便利店", "自己打车", "网约车"]
    stranger_words = ["见网友", "陌生人邀约", "陌生人", "私下见面", "不告诉公司", "单独去陌生地方"]
    risky_staff_meeting = ["前辈单独见面", "老师单独见面", "工作人员单独见面", "单独去房间", "单独去酒店"]

    minor_private_outing_detected = any(w in text for w in private_outing_words)
    minor_private_outing_detected = minor_private_outing_detected or (
        any(w in text for w in ["凌晨", "深夜", "半夜", "晚上"]) and any(w in text for w in ["出门", "外出", "便利店", "打车", "网约车"])
    )
    minor_private_outing_detected = minor_private_outing_detected or (
        any(w in text for w in ["自己", "独自", "一个人", "偷偷"]) and any(w in text for w in ["出门", "外出", "便利店", "打车", "网约车"])
    )

    if state.age_context.get("is_minor", False) and minor_private_outing_detected:
        raise ActionBlockedError(
            "当前角色未成年，不能在无许可、无同行、无报备的情况下深夜或私自外出。该行动被阻止。",
            ["向经纪人申请外出", "请队友或工作人员同行", "在宿舍内解决需求", "给家长或经纪人发消息报备"]
        )

    if any(w in text for w in stranger_words):
        raise ActionBlockedError(
            "陌生邀约或不告知公司的私下见面属于安全风险，不能作为普通行动执行。",
            ["拒绝邀约", "告知经纪人", "保留聊天记录", "让公司或家长介入"]
        )

    if any(w in text for w in risky_staff_meeting):
        raise ActionBlockedError(
            "该行动涉及权力差异或单独密闭空间风险，不能按普通剧情推进。请改为公开场合、多人在场或寻求可信成年人陪同。",
            ["要求公开场合沟通", "请经纪人或女性工作人员在场", "拒绝单独见面", "记录并上报不适行为"]
        )

    # 未成年或高权力差关系的正式恋爱推进先阻止。
    # 低权力、同龄工作人员的“喜欢/在意”不阻止，但由 relationship_system 转入职业边界风险。
    romance_confirm_words = ["表白", "确认关系", "成为恋人", "谈恋爱", "接吻", "约会"]
    high_power_words = ["经纪人", "老师", "粉丝", "PD", "主管", "制作人", "社长", "代表"]
    low_power_staff_words = ["工作人员", "造型", "化妆", "妆发", "服装助理", "造型助理", "助理"]
    if any(w in text for w in romance_confirm_words):
        if state.age_context.get("is_minor", False):
            raise ActionBlockedError(
                "当前角色未成年，不能推进正式恋爱确认、成人化亲密或高风险约会。可以改为整理心情、写日记、保持边界或与同龄朋友谈心。",
                ["把心事写进日记", "和同龄队友谈心", "保持朋友边界", "向可信成年人求助"]
            )
        if any(w in text for w in high_power_words):
            raise ActionBlockedError(
                "该关系存在明显权力差异，不能作为普通恋爱线推进。系统将这类内容归入边界与安全问题。",
                ["保持职业边界", "拒绝单独见面", "向可信成年人或法务求助", "记录不适行为"]
            )
        if any(w in text for w in low_power_staff_words):
            result.system_events.append(_event(
                "staff_romance_boundary_warning",
                "行动警告：同龄工作人员关系高风险",
                "你可以选择表达在意，但工作人员关系不能按同龄练习生恋爱线处理。继续推进会带来职业边界、公司审视和舆论代价。",
                "warning",
            ))

    return result
