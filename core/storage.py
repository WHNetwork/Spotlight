from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from core.event_triggers import EventHistorySnapshot
from core.event_lifecycle import PostSlotEventOutcome
from core.evaluation import MonthlyEvaluationResult
from core.day_settlement import DaySettlementResult
from core.models import GameState, TurnResponse, RouteInfo, SystemEvent, SlotKind, SlotStatus, SlotResolutionResult, EventResult, EventTier, DailyWritingArtifactType, DailyWritingArtifactRecord, EventSceneArtifactRecord

DB_PATH = Path(__file__).resolve().parent.parent / "storage" / "saves.db"

class SaveStorage:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS saves (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    state_json TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    save_id INTEGER NOT NULL,
                    turn_no INTEGER NOT NULL,
                    player_action TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    applied_diff_json TEXT NOT NULL,
                    route_json TEXT,
                    system_events_json TEXT,
                    validation_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(save_id) REFERENCES saves(id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS diary_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    save_id INTEGER NOT NULL,
                    turn_no INTEGER NOT NULL,
                    entry_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(save_id, turn_no),
                    FOREIGN KEY(save_id) REFERENCES saves(id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS slot_resolution_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    save_id INTEGER NOT NULL,
                    game_date TEXT NOT NULL,
                    slot_index INTEGER NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(save_id, game_date, slot_index),
                    FOREIGN KEY(save_id) REFERENCES saves(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS event_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    save_id INTEGER NOT NULL,
                    event_instance_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    game_date TEXT NOT NULL,
                    trigger_slot_index INTEGER NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(save_id, event_instance_id),
                    FOREIGN KEY(save_id) REFERENCES saves(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS monthly_evaluation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    save_id INTEGER NOT NULL,
                    evaluation_id TEXT NOT NULL,
                    evaluation_date TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(save_id, year, month),
                    UNIQUE(save_id, evaluation_id),
                    FOREIGN KEY(save_id) REFERENCES saves(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_writing_artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    save_id INTEGER NOT NULL,
                    game_date TEXT NOT NULL,
                    artifact_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    provider_name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(save_id, game_date, artifact_type),
                    FOREIGN KEY(save_id) REFERENCES saves(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS event_scene_artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    save_id INTEGER NOT NULL,
                    event_instance_id TEXT NOT NULL,
                    game_date TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    slot_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    provider_name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(save_id, event_instance_id),
                    FOREIGN KEY(save_id) REFERENCES saves(id) ON DELETE CASCADE
                )
            """)
            for ddl in [
                "ALTER TABLE turns ADD COLUMN route_json TEXT",
                "ALTER TABLE turns ADD COLUMN system_events_json TEXT",
                "ALTER TABLE turns ADD COLUMN validation_json TEXT",
            ]:
                try:
                    conn.execute(ddl)
                except sqlite3.OperationalError:
                    pass
            conn.commit()

    def create_save(self, state: GameState) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO saves (name, created_at, updated_at, state_json) VALUES (?, ?, ?, ?)",
                (state.save_name, now, now, "{}"),
            )
            save_id = int(cur.lastrowid)
            state.meta.save_id = save_id
            conn.execute("UPDATE saves SET state_json=? WHERE id=?", (state.model_dump_json(), save_id))
            conn.commit()
            return save_id

    def update_save(self, save_id: int, state: GameState) -> None:
        if state.meta.save_id > 0 and state.meta.save_id != save_id:
            raise ValueError(f"state.meta.save_id（{state.meta.save_id}）与 save_id（{save_id}）不一致。")
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as conn:
            cur = conn.execute("UPDATE saves SET name=?, updated_at=?, state_json=? WHERE id=?", (state.save_name, now, state.model_dump_json(), save_id))
            if cur.rowcount != 1:
                raise ValueError(f"存档不存在：{save_id}。")
            conn.commit()

    def load_save(self, save_id: int) -> GameState:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM saves WHERE id=?", (save_id,)).fetchone()
            if not row:
                raise ValueError(f"存档不存在：{save_id}")
            return GameState.model_validate_json(row["state_json"])

    def latest_save_id(self) -> Optional[int]:
        with self.connect() as conn:
            row = conn.execute("SELECT id FROM saves ORDER BY updated_at DESC LIMIT 1").fetchone()
            return int(row["id"]) if row else None

    def list_saves(self) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT id, name, created_at, updated_at FROM saves ORDER BY updated_at DESC").fetchall()
            return [dict(row) for row in rows]

    def save_slot_checkpoint(
        self,
        new_state: GameState,
        result: SlotResolutionResult,
        event_outcome: PostSlotEventOutcome,
    ) -> None:
        """原子保存 Slot checkpoint + Event Phase 结果（同一 SQLite transaction）。

        要求调用方必须提供 PostSlotEventOutcome（不允许绕过 Event Phase）。

        情况 A 无事件：UPDATE GameState + INSERT slot_resolution_history；
        情况 B NON_INTERRUPTIVE：额外 INSERT event_history（EventResult）；
        情况 C INTERRUPTIVE：UPDATE GameState（含 pending_event），不写 event_history。

        - save_id 取自 new_state.meta.save_id，game_date 取自 new_state.time.current_date；
        - 写入前做轻量一致性检查（Slot 已 COMPLETED 且与 result 一致；
          outcome 与 new_state 的 pending_event / event_result 相互一致）；
        - 任一步失败整体 ROLLBACK，不存在“Slot 已 COMPLETED 但 PendingEvent /
          Non-interruptive EventResult 丢失”的部分结果；
        - 重复写入由 UNIQUE 约束拒绝并抛错，不静默覆盖。
        """
        if not result.completed:
            raise ValueError("SlotResolutionResult.completed 必须为 True 才能持久化。")
        if not new_state.day.slots:
            raise ValueError("DayState 尚未初始化，无法保存 Slot checkpoint。")
        if not (0 <= result.slot_index <= 7):
            raise ValueError(f"Slot index {result.slot_index} 必须在 0..7 内。")
        if not (0 <= result.slot_index < len(new_state.day.slots)):
            raise ValueError(f"Slot index {result.slot_index} 超出当天范围。")
        slot = new_state.day.slots[result.slot_index]
        if slot.status != SlotStatus.COMPLETED:
            raise ValueError(f"Slot {result.slot_index} 尚未 COMPLETED，checkpoint 与 result 不一致。")
        completed_indices = [s.index for s in new_state.day.slots if s.status == SlotStatus.COMPLETED]
        if completed_indices != list(range(result.slot_index + 1)):
            raise ValueError(
                f"Slot 完成必须是从 0 到 {result.slot_index} 的连续前缀（当前 {completed_indices}）。"
            )
        if slot.kind != result.slot_kind:
            raise ValueError(f"Slot {result.slot_index} 的 kind（{slot.kind.value}）与 result（{result.slot_kind.value}）不一致。")
        if slot.kind == SlotKind.COMPANY and slot.company_course != result.company_course:
            raise ValueError(f"Slot {result.slot_index} 的 company_course 与 result 不一致。")
        if slot.kind == SlotKind.FREE and slot.free_action != result.free_action:
            raise ValueError(f"Slot {result.slot_index} 的 free_action 与 result 不一致。")

        if event_outcome.pending_event is not None:
            if new_state.pending_event is None:
                raise ValueError("event_outcome 声明 PendingEvent，但 new_state.pending_event 为 None。")
            if new_state.pending_event.event_instance_id != event_outcome.pending_event.event_instance_id:
                raise ValueError("event_outcome 与 new_state 的 PendingEvent instance_id 不一致。")
            if new_state.pending_event.trigger_slot_index != result.slot_index:
                raise ValueError("PendingEvent.trigger_slot_index 与 slot_result.slot_index 不一致。")
        if event_outcome.event_result is not None:
            if new_state.pending_event is not None:
                raise ValueError("event_outcome 声明 EventResult，但 new_state 仍有 pending_event。")
            if event_outcome.event_result.trigger_slot_index != result.slot_index:
                raise ValueError("EventResult.trigger_slot_index 与 slot_result.slot_index 不一致。")
            if event_outcome.event_result.game_date != new_state.time.current_date:
                raise ValueError("EventResult.game_date 与 new_state.time.current_date 不一致。")
        if event_outcome.pending_event is None and event_outcome.event_result is None:
            if new_state.pending_event is not None:
                raise ValueError("event_outcome 无事件，但 new_state 存在 pending_event。")

        save_id = new_state.meta.save_id
        if save_id <= 0:
            raise ValueError("new_state.meta.save_id 未设置，无法保存 checkpoint。")
        now = datetime.now().isoformat(timespec="seconds")
        game_date = new_state.time.current_date.isoformat()
        result_json = json.dumps(result.model_dump(mode="json"), ensure_ascii=False)

        with self.connect() as conn:
            conn.execute("BEGIN")
            try:
                cur = conn.execute(
                    "UPDATE saves SET name=?, updated_at=?, state_json=? WHERE id=?",
                    (new_state.save_name, now, new_state.model_dump_json(), save_id),
                )
                if cur.rowcount != 1:
                    raise ValueError(f"存档不存在：{save_id}，无法保存 checkpoint。")
                existing = [
                    int(r["slot_index"])
                    for r in conn.execute(
                        "SELECT slot_index FROM slot_resolution_history WHERE save_id=? AND game_date=? ORDER BY slot_index ASC",
                        (save_id, game_date),
                    ).fetchall()
                ]
                if existing != list(range(result.slot_index)):
                    raise ValueError(
                        f"slot_resolution_history 已有记录必须严格为 0..{result.slot_index - 1} 连续前缀"
                        f"（当前 {existing}），不能跳写/回写。"
                    )
                conn.execute(
                    "INSERT INTO slot_resolution_history (save_id, game_date, slot_index, result_json, created_at) VALUES (?, ?, ?, ?, ?)",
                    (save_id, game_date, result.slot_index, result_json, now),
                )
                if event_outcome.event_result is not None:
                    er = event_outcome.event_result
                    conn.execute(
                        "INSERT INTO event_history (save_id, event_instance_id, event_id, game_date, trigger_slot_index, result_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            save_id,
                            er.event_instance_id,
                            er.event_id,
                            er.game_date.isoformat(),
                            er.trigger_slot_index,
                            json.dumps(er.model_dump(mode="json"), ensure_ascii=False),
                            now,
                        ),
                    )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def load_slot_results(self, save_id: int, game_date: date) -> List[SlotResolutionResult]:
        """读取指定存档、指定游戏日期的全部 Slot Result，按 slot_index 升序返回。

        允许 0–8 条（玩家可能中途退出）；恢复为正式 SlotResolutionResult 模型。
        """
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT result_json FROM slot_resolution_history WHERE save_id=? AND game_date=? ORDER BY slot_index ASC",
                (save_id, game_date.isoformat()),
            ).fetchall()
        results: List[SlotResolutionResult] = []
        for row in rows:
            try:
                results.append(SlotResolutionResult.model_validate(json.loads(row["result_json"])))
            except Exception as exc:
                raise ValueError(
                    f"slot_resolution_history 记录损坏（save_id={save_id}, game_date={game_date.isoformat()}）：{exc}"
                ) from exc
        return results

    def save_event_resolution_checkpoint(self, new_state: GameState, event_result: EventResult) -> None:
        """玩家解决 PendingEvent 后原子保存：验证 PendingEvent → UPDATE GameState → INSERT EventResult。

        同一 SQLite transaction：
        ① 读取数据库当前存档的 GameState，确认 pending_event 存在且其全部机械字段
           与 event_result 完全一致（防止错配写入）；
        ② 校验 event_result.choice_id 非空且属于 pending.available_choice_ids；
        ③ new_state.pending_event 必须已清除、日期等于 event_result.game_date；
        ④ UPDATE GameState；⑤ INSERT event_history。
        COMMIT / 任一步失败 ROLLBACK。
        """
        save_id = new_state.meta.save_id
        if save_id <= 0:
            raise ValueError("new_state.meta.save_id 未设置，无法保存 Event resolution checkpoint。")
        now = datetime.now().isoformat(timespec="seconds")
        result_json = json.dumps(event_result.model_dump(mode="json"), ensure_ascii=False)

        with self.connect() as conn:
            conn.execute("BEGIN")
            try:
                row = conn.execute("SELECT state_json FROM saves WHERE id=?", (save_id,)).fetchone()
                if row is None:
                    raise ValueError(f"存档不存在：{save_id}。")
                persisted = GameState.model_validate_json(row["state_json"])
                if persisted.pending_event is None:
                    raise ValueError("数据库当前存档没有 PendingEvent，不能写入 EventResult。")
                pending = persisted.pending_event
                er = event_result
                mismatches = []
                if pending.event_instance_id != er.event_instance_id:
                    mismatches.append("event_instance_id")
                if pending.event_id != er.event_id:
                    mismatches.append("event_id")
                if pending.triggered_date != er.game_date:
                    mismatches.append("game_date/triggered_date")
                if pending.trigger_slot_index != er.trigger_slot_index:
                    mismatches.append("trigger_slot_index")
                if pending.category != er.category:
                    mismatches.append("category")
                if pending.trigger_mode != er.trigger_mode:
                    mismatches.append("trigger_mode")
                if pending.tier != er.tier:
                    mismatches.append("tier")
                if pending.interaction_mode != er.interaction_mode:
                    mismatches.append("interaction_mode")
                if pending.priority != er.priority:
                    mismatches.append("priority")
                if pending.base_probability != er.base_probability:
                    mismatches.append("base_probability")
                if pending.soft_relevance != er.soft_relevance:
                    mismatches.append("soft_relevance")
                if pending.effective_probability != er.effective_probability:
                    mismatches.append("effective_probability")
                if pending.context_npc_id != er.context_npc_id:
                    mismatches.append("context_npc_id")
                if not er.choice_id or er.choice_id not in pending.available_choice_ids:
                    mismatches.append("choice_id 不在 available_choice_ids")
                if new_state.pending_event is not None:
                    mismatches.append("new_state.pending_event 未清除")
                if new_state.time.current_date != er.game_date:
                    mismatches.append("日期推进（Event Choice 不推进日期）")
                if mismatches:
                    raise ValueError(f"Event resolution 与 PendingEvent 不一致：{', '.join(mismatches)}")
                cur = conn.execute(
                    "UPDATE saves SET name=?, updated_at=?, state_json=? WHERE id=?",
                    (new_state.save_name, now, new_state.model_dump_json(), save_id),
                )
                if cur.rowcount != 1:
                    raise ValueError(f"存档不存在：{save_id}。")
                conn.execute(
                    "INSERT INTO event_history (save_id, event_instance_id, event_id, game_date, trigger_slot_index, result_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        save_id,
                        event_result.event_instance_id,
                        event_result.event_id,
                        event_result.game_date.isoformat(),
                        event_result.trigger_slot_index,
                        result_json,
                        now,
                    ),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def load_event_results(self, save_id: int, game_date: Optional[date] = None) -> List[EventResult]:
        """读取已解决事件历史；可选按自然日过滤。

        按 game_date ASC、trigger_slot_index ASC、id ASC 稳定排序；
        返回正式 EventResult 模型，不返回裸 dict。
        """
        query = "SELECT result_json FROM event_history WHERE save_id=?"
        params: List[Any] = [save_id]
        if game_date is not None:
            query += " AND game_date=?"
            params.append(game_date.isoformat())
        query += " ORDER BY game_date ASC, trigger_slot_index ASC, id ASC"
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        results: List[EventResult] = []
        for row in rows:
            try:
                results.append(EventResult.model_validate(json.loads(row["result_json"])))
            except Exception as exc:
                raise ValueError(f"event_history 记录损坏（save_id={save_id}）：{exc}") from exc
        return results

    def build_event_history_snapshot(self, save_id: int, current_date: date) -> EventHistorySnapshot:
        """从已解决 EventResult 历史构建 Step 8A 的 EventHistorySnapshot。

        本方法位于 Persistence Layer；event_triggers.py 不直接访问 SQLite。
        """
        snapshot = EventHistorySnapshot()
        for result in self.load_event_results(save_id):
            snapshot.occurred_event_ids.add(result.event_id)
            snapshot.event_counts[result.event_id] = snapshot.event_counts.get(result.event_id, 0) + 1
            snapshot.last_event_dates[result.event_id] = result.game_date
            if result.game_date == current_date:
                if result.tier == EventTier.MAJOR:
                    snapshot.major_count_today += 1
                elif result.tier == EventTier.MINOR:
                    snapshot.minor_count_today += 1
        return snapshot

    # ------------------------------------------------------------------
    # Daily Writing Artifacts（player-visible 文本；与 GameState 无耦合）
    # ------------------------------------------------------------------

    def save_daily_writing_artifact(
        self,
        save_id: int,
        game_date: date,
        artifact_type: DailyWritingArtifactType,
        content: str,
        provider_name: str,
    ) -> None:
        """保存一条正式 daily writing artifact（默认禁止覆盖）。

        同 (save_id, game_date, artifact_type) 已存在时由 UNIQUE 约束抛
        sqlite3.IntegrityError；content 为空时明确失败，不写空 row。
        """
        if not content or not str(content).strip():
            raise ValueError("不能保存空的 writing artifact。")
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO daily_writing_artifacts (save_id, game_date, artifact_type, content, provider_name, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (save_id, game_date.isoformat(), artifact_type.value, content, provider_name, now),
            )
            conn.commit()

    def load_daily_writing_artifact(
        self,
        save_id: int,
        game_date: date,
        artifact_type: DailyWritingArtifactType,
    ) -> Optional[DailyWritingArtifactRecord]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT save_id, game_date, artifact_type, content, provider_name, created_at FROM daily_writing_artifacts WHERE save_id=? AND game_date=? AND artifact_type=?",
                (save_id, game_date.isoformat(), artifact_type.value),
            ).fetchone()
        if row is None:
            return None
        return DailyWritingArtifactRecord(
            save_id=int(row["save_id"]),
            game_date=date.fromisoformat(row["game_date"]),
            artifact_type=DailyWritingArtifactType(row["artifact_type"]),
            content=row["content"],
            provider_name=row["provider_name"],
            created_at=row["created_at"],
        )

    def load_daily_writing_artifacts(
        self,
        save_id: int,
        game_date: Optional[date] = None,
    ) -> List[DailyWritingArtifactRecord]:
        query = "SELECT save_id, game_date, artifact_type, content, provider_name, created_at FROM daily_writing_artifacts WHERE save_id=?"
        params: List[Any] = [save_id]
        if game_date is not None:
            query += " AND game_date=?"
            params.append(game_date.isoformat())
        query += " ORDER BY game_date ASC, id ASC"
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            DailyWritingArtifactRecord(
                save_id=int(row["save_id"]),
                game_date=date.fromisoformat(row["game_date"]),
                artifact_type=DailyWritingArtifactType(row["artifact_type"]),
                content=row["content"],
                provider_name=row["provider_name"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Event Scene Artifacts（Interruptive Event Setup Scene；独立表，因一天可多事件）
    # ------------------------------------------------------------------

    def save_event_scene_artifact(
        self,
        save_id: int,
        event_instance_id: str,
        game_date: date,
        event_id: str,
        slot_index: int,
        content: str,
        provider_name: str,
    ) -> None:
        """保存一条 Event Setup Scene（默认禁止覆盖）。

        同 (save_id, event_instance_id) 已存在时由 UNIQUE 约束抛
        sqlite3.IntegrityError；content 为空时明确失败。
        """
        if not content or not str(content).strip():
            raise ValueError("不能保存空的 event scene artifact。")
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO event_scene_artifacts (save_id, event_instance_id, game_date, event_id, slot_index, content, provider_name, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (save_id, event_instance_id, game_date.isoformat(), event_id, slot_index, content, provider_name, now),
            )
            conn.commit()

    def load_event_scene_artifact(
        self,
        save_id: int,
        event_instance_id: str,
    ) -> Optional[EventSceneArtifactRecord]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT save_id, event_instance_id, game_date, event_id, slot_index, content, provider_name, created_at FROM event_scene_artifacts WHERE save_id=? AND event_instance_id=?",
                (save_id, event_instance_id),
            ).fetchone()
        if row is None:
            return None
        return EventSceneArtifactRecord(
            save_id=int(row["save_id"]),
            event_instance_id=row["event_instance_id"],
            game_date=date.fromisoformat(row["game_date"]),
            event_id=row["event_id"],
            slot_index=int(row["slot_index"]),
            content=row["content"],
            provider_name=row["provider_name"],
            created_at=row["created_at"],
        )

    def load_event_scene_artifacts(
        self,
        save_id: int,
        game_date: Optional[date] = None,
    ) -> List[EventSceneArtifactRecord]:
        query = "SELECT save_id, event_instance_id, game_date, event_id, slot_index, content, provider_name, created_at FROM event_scene_artifacts WHERE save_id=?"
        params: List[Any] = [save_id]
        if game_date is not None:
            query += " AND game_date=?"
            params.append(game_date.isoformat())
        query += " ORDER BY game_date ASC, slot_index ASC, id ASC"
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            EventSceneArtifactRecord(
                save_id=int(row["save_id"]),
                event_instance_id=row["event_instance_id"],
                game_date=date.fromisoformat(row["game_date"]),
                event_id=row["event_id"],
                slot_index=int(row["slot_index"]),
                content=row["content"],
                provider_name=row["provider_name"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def add_turn(self, save_id: int, turn_no: int, player_action: str, response: TurnResponse, applied_diff: Dict[str, Any], route_info: RouteInfo, system_events: List[SystemEvent], validation_json: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO turns
                (save_id, turn_no, player_action, response_json, applied_diff_json, route_json, system_events_json, validation_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    save_id, turn_no, player_action, response.model_dump_json(),
                    json.dumps(applied_diff, ensure_ascii=False),
                    route_info.model_dump_json(),
                    json.dumps([e.model_dump() for e in system_events], ensure_ascii=False),
                    validation_json,
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
            conn.commit()


    def upsert_diary_entry(self, save_id: int, turn_no: int, entry: Dict[str, Any]) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO diary_entries (save_id, turn_no, entry_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(save_id, turn_no)
                DO UPDATE SET entry_json=excluded.entry_json, updated_at=excluded.updated_at
                """,
                (save_id, turn_no, json.dumps(entry, ensure_ascii=False), now, now),
            )
            conn.commit()

    def get_diary_entries(self, save_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT turn_no, entry_json, created_at, updated_at
                FROM diary_entries
                WHERE save_id=?
                ORDER BY turn_no DESC
                LIMIT ?
                """,
                (save_id, limit),
            ).fetchall()
        result: List[Dict[str, Any]] = []
        for row in rows:
            try:
                entry = json.loads(row["entry_json"] or "{}")
            except Exception:
                entry = {}
            entry.setdefault("turn", int(row["turn_no"]))
            entry.setdefault("created_at", row["created_at"])
            entry.setdefault("updated_at", row["updated_at"])
            result.append(entry)
        return result

    def get_diary_entry(self, save_id: int, turn_no: int) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT entry_json FROM diary_entries WHERE save_id=? AND turn_no=?",
                (save_id, turn_no),
            ).fetchone()
        if not row:
            return None
        try:
            return json.loads(row["entry_json"] or "{}")
        except Exception:
            return None

    def load_monthly_evaluation_results(self, save_id: int) -> List[MonthlyEvaluationResult]:
        """读取指定存档的全部正式月评结果，按 year ASC、month ASC、id ASC 稳定排序。

        返回正式 MonthlyEvaluationResult 模型，不返回裸 dict。
        """
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT result_json FROM monthly_evaluation_history WHERE save_id=? ORDER BY year ASC, month ASC, id ASC",
                (save_id,),
            ).fetchall()
        results: List[MonthlyEvaluationResult] = []
        for row in rows:
            try:
                results.append(MonthlyEvaluationResult.model_validate(json.loads(row["result_json"])))
            except Exception as exc:
                raise ValueError(f"monthly_evaluation_history 记录损坏（save_id={save_id}）：{exc}") from exc
        return results

    def save_day_settlement_checkpoint(self, new_state: GameState, result: DaySettlementResult) -> None:
        """原子 Day Settlement checkpoint：从完成的旧日进入下一自然日。

        同一 SQLite transaction：
        ① 读取数据库当前 persisted GameState，验证：
           current_date == result.settled_date、day.is_day_complete、pending_event is None；
        ② 验证 new_state：current_date == result.next_date、pending_event is None；
        ③ 若 result.monthly_evaluation 非空：做轻量一致性检查并 INSERT
           monthly_evaluation_history（重复由 UNIQUE 拒绝并整体 rollback）；
        ④ UPDATE saves.state_json 为 next-day GameState；
        COMMIT / 任一步失败 ROLLBACK。

        不重新计算任何评价分数；不自动处理 PendingEvent。
        """
        save_id = new_state.meta.save_id
        if save_id <= 0:
            raise ValueError("new_state.meta.save_id 未设置，无法保存 Day Settlement checkpoint。")
        now = datetime.now().isoformat(timespec="seconds")

        with self.connect() as conn:
            conn.execute("BEGIN")
            try:
                row = conn.execute("SELECT state_json FROM saves WHERE id=?", (save_id,)).fetchone()
                if row is None:
                    raise ValueError(f"存档不存在：{save_id}。")
                persisted = GameState.model_validate_json(row["state_json"])
                if persisted.time.current_date != result.settled_date:
                    raise ValueError(
                        f"数据库当前存档日期（{persisted.time.current_date}）与 settled_date"
                        f"（{result.settled_date}）不一致（可能已结算过这一天）。"
                    )
                if not persisted.day.is_day_complete:
                    raise ValueError("数据库当前存档当天尚未完成，不能 Day Settlement。")
                if persisted.pending_event is not None:
                    raise ValueError("数据库当前存档仍有 PendingEvent，不能 Day Settlement。")

                if new_state.time.current_date != result.next_date:
                    raise ValueError("new_state.current_date 必须等于 result.next_date。")
                if new_state.pending_event is not None:
                    raise ValueError("new_state 不应携带 PendingEvent（Day Settlement 后必须无待处理事件）。")

                # 应评必评：persisted 旧日若满足月评资格，则 result 必须携带月评；反之不得凭空携带。
                from core.evaluation import is_monthly_evaluation_eligible

                evaluation_eligible = is_monthly_evaluation_eligible(persisted)
                if evaluation_eligible and result.monthly_evaluation is None:
                    raise ValueError("当前旧日满足正式月评资格，但 result 未携带 monthly_evaluation（禁止伪造跳过）。")
                if not evaluation_eligible and result.monthly_evaluation is not None:
                    raise ValueError("当前旧日不满足月评资格，但 result 凭空携带了 monthly_evaluation。")

                # 最低一致性：result.condition_result.before 必须等于 persisted 当天结束 Condition 快照。
                from core.condition_resolution import snapshot_of

                persisted_condition = snapshot_of(persisted.condition)
                before_snapshot = result.condition_result.before
                for field in ("energy", "voice_condition", "sleep_condition", "mood", "confidence",
                              "muscle_fatigue", "injury_risk", "stress"):
                    if abs(getattr(before_snapshot, field) - getattr(persisted_condition, field)) > 1e-9:
                        raise ValueError(f"result.condition_result.before.{field} 与 persisted 当天结束 Condition 不一致。")

                # form_results 必须覆盖正式 8 个 Skill（顺序与 Core contract 一致）。
                from core.models import SkillId

                expected_form_order = [
                    SkillId.DANCE, SkillId.VOCAL, SkillId.RAP, SkillId.STAGE,
                    SkillId.CAMERA, SkillId.LANGUAGE, SkillId.ACTING, SkillId.CREATION,
                ]
                actual_form_order = [fr.skill for fr in result.form_results]
                if actual_form_order != expected_form_order:
                    raise ValueError("result.form_results 必须按正式 8 Skill 顺序完整覆盖（Core contract）。")

                if result.monthly_evaluation is not None:
                    evaluation = result.monthly_evaluation
                    if evaluation.evaluation_date != result.settled_date:
                        raise ValueError("monthly_evaluation.evaluation_date 必须等于 settled_date。")
                    if evaluation.year != result.settled_date.year or evaluation.month != result.settled_date.month:
                        raise ValueError("monthly_evaluation 的 year/month 必须与 settled_date 一致。")
                    if new_state.trainee.latest_evaluation_date != evaluation.evaluation_date:
                        raise ValueError("new_state.trainee.latest_evaluation_date 与 evaluation_date 不一致。")
                    if new_state.trainee.latest_evaluation_score != evaluation.overall_score:
                        raise ValueError("new_state.trainee.latest_evaluation_score 与 overall_score 不一致。")
                    conn.execute(
                        "INSERT INTO monthly_evaluation_history (save_id, evaluation_id, evaluation_date, year, month, result_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            save_id,
                            evaluation.evaluation_id,
                            evaluation.evaluation_date.isoformat(),
                            evaluation.year,
                            evaluation.month,
                            json.dumps(evaluation.model_dump(mode="json"), ensure_ascii=False),
                            now,
                        ),
                    )

                cur = conn.execute(
                    "UPDATE saves SET name=?, updated_at=?, state_json=? WHERE id=?",
                    (new_state.save_name, now, new_state.model_dump_json(), save_id),
                )
                if cur.rowcount != 1:
                    raise ValueError(f"存档不存在：{save_id}。")
                conn.commit()
            except Exception:
                conn.rollback()
                raise
