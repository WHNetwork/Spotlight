from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger
from PySide6.QtCore import QObject, Property, Signal, Slot

from core.free_actions import FreeActionError, assign_free_action
from core.models import (
    CompanyCourse,
    ExplorationDomain,
    FreeAction,
    FreeActionKind,
    GameState,
    PersonalActionType,
    SkillId,
    SlotKind,
)
from core.storage import SaveStorage

_WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

_SKILL_ITEMS = [
    ("dance", "舞蹈"),
    ("vocal", "声乐"),
    ("rap", "说唱"),
    ("stage", "舞台"),
    ("camera", "镜头"),
    ("language", "语言"),
    ("acting", "演技"),
    ("creation", "创作"),
]

_TRAIN_SKILL_KEYS = ["dance", "vocal", "rap", "stage", "camera", "language"]
_EXPLORE_SKILL_KEYS = ["acting", "creation"]

_CONDITION_ITEMS = [
    ("energy", "精力"),
    ("muscle_fatigue", "肌肉疲劳"),
    ("injury_risk", "受伤风险"),
    ("voice_condition", "嗓音状态"),
    ("sleep_condition", "睡眠状态"),
    ("stress", "压力"),
    ("mood", "心情"),
    ("confidence", "自信"),
]

_COURSE_LABELS = {
    CompanyCourse.DANCE: "舞蹈",
    CompanyCourse.VOCAL: "声乐",
    CompanyCourse.RAP: "说唱",
    CompanyCourse.STAGE: "舞台",
    CompanyCourse.CAMERA: "镜头",
    CompanyCourse.LANGUAGE: "语言",
    CompanyCourse.FITNESS: "体能",
}

_KIND_LABELS = {
    SlotKind.REST: "休息",
    SlotKind.SCHOOL: "学校",
    SlotKind.COMPANY: "公司",
    SlotKind.FREE: "自由",
}

_KIND_ROOM_LABELS = {
    SlotKind.REST: "休息时间",
    SlotKind.SCHOOL: "学校时间",
    SlotKind.COMPANY: "公司课程",
    SlotKind.FREE: "自由活动时间",
}

_ACTION_ITEMS = [
    (FreeActionKind.TRAIN.value, "训练"),
    (FreeActionKind.SOCIAL.value, "社交"),
    (FreeActionKind.RECOVER.value, "恢复"),
    (FreeActionKind.EXPLORE.value, "探索"),
    (FreeActionKind.PERSONAL.value, "个人事务"),
]

_PERSONAL_ITEMS = [
    (PersonalActionType.STUDY.value, "学习"),
    (PersonalActionType.FAMILY.value, "家庭"),
    (PersonalActionType.LEISURE.value, "休闲"),
    (PersonalActionType.OUTING.value, "外出"),
]


class MainGameController(QObject):
    """轻量桥接：主游戏页 → 正式 GameState（只读展示）。

    只负责：接收 save_id → SaveStorage.load_save() → 以 Qt Property 暴露
    主界面需要的展示数据。不复制后端 mechanics，不在 Controller 内重新
    计算任何正式状态。
    """

    stateChanged = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._storage = SaveStorage()
        self._save_id: Optional[int] = None
        self._state: Optional[GameState] = None
        self._load_error = ""

    # ---- load ------------------------------------------------------------
    @Slot(int, result=bool)
    def loadSave(self, save_id: int) -> bool:  # noqa: N802
        try:
            state = self._storage.load_save(int(save_id))
        except Exception as exc:  # noqa: BLE001
            logger.exception(f"MainGameController load_save failed: save_id={save_id}")
            self._save_id = None
            self._state = None
            self._load_error = f"读取存档失败：{exc}"
            self.stateChanged.emit()
            return False
        self._save_id = int(save_id)
        self._state = state
        self._load_error = ""
        self.stateChanged.emit()
        return True

    @Slot(result=bool)
    def loadLatestSave(self) -> bool:  # noqa: N802
        try:
            save_id = self._storage.latest_save_id()
        except Exception as exc:  # noqa: BLE001
            logger.exception("MainGameController latest_save_id failed")
            self._save_id = None
            self._state = None
            self._load_error = f"读取最新存档失败：{exc}"
            self.stateChanged.emit()
            return False
        if save_id is None:
            self._save_id = None
            self._state = None
            self._load_error = "尚未找到任何存档。"
            self.stateChanged.emit()
            return False
        return self.loadSave(save_id)

    # ---- basic state -----------------------------------------------------
    @Property(int, notify=stateChanged)
    def saveId(self) -> int:  # noqa: N802
        return self._save_id or 0

    @Property(bool, notify=stateChanged)
    def hasLoaded(self) -> bool:  # noqa: N802
        return self._state is not None

    @Property(str, notify=stateChanged)
    def loadErrorText(self) -> str:  # noqa: N802
        return self._load_error

    def _state_or_none(self) -> Optional[GameState]:
        return self._state

    # ---- player ----------------------------------------------------------
    @Property(str, notify=stateChanged)
    def stageName(self) -> str:  # noqa: N802
        state = self._state_or_none()
        return state.player.stage_name if state else ""

    @Property(str, notify=stateChanged)
    def realName(self) -> str:  # noqa: N802
        state = self._state_or_none()
        return state.player.name if state else ""

    @Property(str, notify=stateChanged)
    def ageText(self) -> str:  # noqa: N802
        state = self._state_or_none()
        if state is None or state.player.starting_age is None:
            return "—"
        return f"{state.player.starting_age} 岁"

    @Property(str, notify=stateChanged)
    def nationality(self) -> str:  # noqa: N802
        state = self._state_or_none()
        return state.player.nationality if state else ""

    @Property(str, notify=stateChanged)
    def avatar(self) -> str:  # noqa: N802
        state = self._state_or_none()
        return state.player.avatar if state else ""

    @Property(int, notify=stateChanged)
    def trainingLevel(self) -> int:  # noqa: N802
        state = self._state_or_none()
        return state.trainee.training_level if state else 1

    @Property(str, notify=stateChanged)
    def evaluationText(self) -> str:  # noqa: N802
        state = self._state_or_none()
        if state is None or state.trainee.latest_evaluation_score is None:
            return "尚未进行"
        return f"{state.trainee.latest_evaluation_score:.0f} 分"

    # ---- time ------------------------------------------------------------
    @Property(int, notify=stateChanged)
    def dayNumber(self) -> int:  # noqa: N802
        state = self._state_or_none()
        return state.time.trainee_day + 1 if state else 1

    @Property(str, notify=stateChanged)
    def dateText(self) -> str:  # noqa: N802
        state = self._state_or_none()
        if state is None:
            return ""
        return f"{state.time.month}月{state.time.day}日"

    @Property(str, notify=stateChanged)
    def weekdayText(self) -> str:  # noqa: N802
        state = self._state_or_none()
        if state is None:
            return ""
        return _WEEKDAYS[state.time.weekday]

    @Property(int, notify=stateChanged)
    def currentSlotIndex(self) -> int:  # noqa: N802
        state = self._state_or_none()
        if state is None:
            return -1
        return state.day.current_slot if state.day.current_slot is not None else -1

    @Property(str, notify=stateChanged)
    def slotText(self) -> str:  # noqa: N802
        state = self._state_or_none()
        if state is None:
            return ""
        current = state.day.current_slot
        if current is None:
            return "8 格已全部完成" if state.day.slots else "今日日程未生成"
        return f"第 {current + 1} / 8 时间格"

    # ---- skills ----------------------------------------------------------
    @Property("QVariantList", notify=stateChanged)
    def skillsModel(self) -> list:  # noqa: N802
        state = self._state_or_none()
        if state is None:
            return []
        rows: List[Dict[str, Any]] = []
        for key, label in _SKILL_ITEMS:
            skill = getattr(state.skills, key)
            rows.append({
                "key": key,
                "label": label,
                "value": skill.value if skill.unlocked else None,
                "unlocked": skill.unlocked,
            })
        return rows

    # ---- condition -------------------------------------------------------
    @Property("QVariantList", notify=stateChanged)
    def conditionModel(self) -> list:  # noqa: N802
        state = self._state_or_none()
        if state is None:
            return []
        rows: List[Dict[str, Any]] = []
        for key, label in _CONDITION_ITEMS:
            value = getattr(state.condition, key)
            rows.append({
                "key": key,
                "label": label,
                "value": int(round(float(value))),
            })
        return rows

    # ---- day slots -------------------------------------------------------
    @Property("QVariantList", notify=stateChanged)
    def slotsModel(self) -> list:  # noqa: N802
        state = self._state_or_none()
        if state is None:
            return []
        current = state.day.current_slot
        rows: List[Dict[str, Any]] = []
        for slot in state.day.slots:
            kind_label = _KIND_LABELS.get(slot.kind, slot.kind.value)
            course_label = ""
            if slot.kind == SlotKind.COMPANY and slot.company_course is not None:
                course_label = _COURSE_LABELS.get(slot.company_course, slot.company_course.value)
            label = course_label or kind_label
            assigned_label = ""
            if slot.free_action is not None:
                assigned_label = self._action_summary(state, slot.free_action)
                label = assigned_label
            rows.append({
                "index": slot.index,
                "label": label,
                "kind": slot.kind.value,
                "completed": slot.status.value == "COMPLETED",
                "current": slot.index == current,
                "assigned": slot.free_action is not None,
            })
        return rows

    # ---- narrative -------------------------------------------------------
    @Property(str, notify=stateChanged)
    def contextText(self) -> str:  # noqa: N802
        state = self._state_or_none()
        if state is None:
            return ""
        slot = self._current_slot()
        if slot is None:
            return "日程"
        if slot.kind == SlotKind.COMPANY and slot.company_course is not None:
            course = _COURSE_LABELS.get(slot.company_course, slot.company_course.value)
            return f"{course}教室 · 公司课程"
        return _KIND_ROOM_LABELS.get(slot.kind, "日程")

    @Property(str, notify=stateChanged)
    def narrativeText(self) -> str:  # noqa: N802
        state = self._state_or_none()
        if state is None:
            return self._load_error or "没有可用的游戏状态。"
        if not state.day.slots:
            return "今天的基础日程尚未生成。"
        if state.day.is_day_complete:
            return "今天 8 个时间格已经全部完成，等待日终结算。"
        slot = self._current_slot()
        if slot is None:
            return "今天 8 个时间格已经全部完成，等待日终结算。"
        if slot.kind == SlotKind.COMPANY and slot.company_course is not None:
            course = _COURSE_LABELS.get(slot.company_course, slot.company_course.value)
            return f"今天的{course}课程即将开始。跟着公司安排完成这一时间格的训练。"
        if slot.kind == SlotKind.FREE:
            return "现在是自由活动时间，你可以安排接下来的行动。"
        if slot.kind == SlotKind.REST:
            return "当前时间格为休息时间。"
        if slot.kind == SlotKind.SCHOOL:
            return "当前时间格为学校时间。"
        return "当前时间格即将开始。"

    # ---- actions ---------------------------------------------------------
    @Property("QVariantList", notify=stateChanged)
    def actionsModel(self) -> list:  # noqa: N802
        state = self._state_or_none()
        if state is None:
            return []
        slot = self._current_slot()
        if slot is None or slot.kind != SlotKind.FREE:
            return []
        return [{"key": key, "label": label} for key, label in _ACTION_ITEMS]

    @Property("QVariantList", notify=stateChanged)
    def trainSkillsModel(self) -> list:  # noqa: N802
        """FREE 行动「训练」可选的已解锁技能（acting / creation 永不出现）。"""
        state = self._state_or_none()
        if state is None:
            return []
        rows: List[Dict[str, Any]] = []
        for key in _TRAIN_SKILL_KEYS:
            skill = getattr(state.skills, key)
            if skill.unlocked:
                label = next((lb for k, lb in _SKILL_ITEMS if k == key), key)
                rows.append({"key": key, "label": label})
        return rows

    @Property("QVariantList", notify=stateChanged)
    def exploreDomainsModel(self) -> list:  # noqa: N802
        """FREE 行动「探索」仍锁定的方向（遵循现有 EXPLORE 规则，仅显示未解锁）。"""
        state = self._state_or_none()
        if state is None:
            return []
        rows: List[Dict[str, Any]] = []
        for key in _EXPLORE_SKILL_KEYS:
            skill = getattr(state.skills, key)
            if not skill.unlocked:
                label = next((lb for k, lb in _SKILL_ITEMS if k == key), key)
                rows.append({"key": key, "label": label})
        return rows

    @Property("QVariantList", notify=stateChanged)
    def personalActionsModel(self) -> list:  # noqa: N802
        """FREE 行动「个人事务」允许的结构化个人生活类型。"""
        return [{"key": key, "label": label} for key, label in _PERSONAL_ITEMS]

    @Property("QVariantList", notify=stateChanged)
    def npcsModel(self) -> list:  # noqa: N802
        """FREE 行动「社交」可选择的当前有效 NPC。"""
        state = self._state_or_none()
        if state is None:
            return []
        rows: List[Dict[str, Any]] = []
        for profile in state.npcs.values():
            if profile.active:
                rows.append({"key": profile.npc_id, "label": profile.name})
        return rows

    # ---- free action assignment ------------------------------------------
    @Property(bool, notify=stateChanged)
    def currentSlotAssigned(self) -> bool:  # noqa: N802
        state = self._state_or_none()
        if state is None:
            return False
        slot = self._current_slot()
        return slot is not None and slot.free_action is not None

    @Property(str, notify=stateChanged)
    def currentSlotActionText(self) -> str:  # noqa: N802
        state = self._state_or_none()
        if state is None:
            return ""
        slot = self._current_slot()
        if slot is None or slot.free_action is None:
            return ""
        return self._action_summary(state, slot.free_action)

    @Slot(str, str, result=str)
    def assignAction(self, category: str, sub_key: str) -> str:  # noqa: N802
        """把玩家选择的行动正式安排到当前 FREE Slot（走正式 assign_free_action）。"""
        state = self._state_or_none()
        if state is None:
            return "安排失败：没有可用的游戏状态。"
        try:
            kind = FreeActionKind(category)
            if kind == FreeActionKind.TRAIN:
                action = FreeAction(kind=kind, skill=SkillId(sub_key))
            elif kind == FreeActionKind.SOCIAL:
                action = FreeAction(kind=kind, target_npc_id=sub_key)
            elif kind == FreeActionKind.RECOVER:
                action = FreeAction(kind=kind)
            elif kind == FreeActionKind.EXPLORE:
                action = FreeAction(kind=kind, exploration_domain=ExplorationDomain(sub_key))
            elif kind == FreeActionKind.PERSONAL:
                action = FreeAction(kind=kind, personal_type=PersonalActionType(sub_key))
            else:  # pragma: no cover
                return "安排失败：未知行动类型。"
            assign_free_action(state.day, state.skills, action, state.npcs)
            self._storage.update_save(self._save_id, state)
            self.stateChanged.emit()
            return f"已安排：{self._action_summary(state, action)}"
        except (FreeActionError, ValueError) as exc:
            return f"安排失败：{exc}"
        except Exception as exc:  # noqa: BLE001
            logger.exception("assign free action failed")
            return f"安排失败：{exc}"

    def _action_summary(self, state: GameState, action: FreeAction) -> str:
        if action.kind == FreeActionKind.TRAIN and action.skill is not None:
            label = next((lb for k, lb in _SKILL_ITEMS if k == action.skill.value), action.skill.value)
            return f"训练 · {label}"
        if action.kind == FreeActionKind.SOCIAL and action.target_npc_id:
            npc = state.npcs.get(action.target_npc_id)
            name = npc.name if npc else action.target_npc_id
            return f"社交 · {name}"
        if action.kind == FreeActionKind.RECOVER:
            return "恢复"
        if action.kind == FreeActionKind.EXPLORE and action.exploration_domain is not None:
            label = next(
                (lb for k, lb in _SKILL_ITEMS if k == action.exploration_domain.value),
                action.exploration_domain.value,
            )
            return f"探索 · {label}"
        if action.kind == FreeActionKind.PERSONAL and action.personal_type is not None:
            label = next(
                (lb for k, lb in _PERSONAL_ITEMS if k == action.personal_type.value),
                action.personal_type.value,
            )
            return f"个人事务 · {label}"
        return action.kind.value

    @Property(str, notify=stateChanged)
    def actionHintText(self) -> str:  # noqa: N802
        state = self._state_or_none()
        if state is None:
            return ""
        if not state.day.slots:
            return ""
        if state.day.is_day_complete:
            return "今天 8 个时间格已全部完成，等待日终结算。"
        slot = self._current_slot()
        if slot is None:
            return ""
        if slot.kind == SlotKind.FREE:
            return "选择你在这格要做的事："
        return f"当前为{_KIND_LABELS.get(slot.kind, '日程')}时间，由公司日程自动推进。"

    def _current_slot(self):
        state = self._state_or_none()
        if state is None:
            return None
        current = state.day.current_slot
        if current is None:
            return None
        for slot in state.day.slots:
            if slot.index == current:
                return slot
        return None
