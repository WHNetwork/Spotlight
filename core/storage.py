from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from core.models import GameState, TurnResponse, RouteInfo, SystemEvent

DB_PATH = Path(__file__).resolve().parent.parent / "storage" / "saves.db"

class SaveStorage:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
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
        state.created_at = now
        state.updated_at = now
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO saves (name, created_at, updated_at, state_json) VALUES (?, ?, ?, ?)",
                (state.save_name, state.created_at, state.updated_at, state.model_dump_json()),
            )
            conn.commit()
            return int(cur.lastrowid)

    def update_save(self, save_id: int, state: GameState) -> None:
        state.updated_at = datetime.now().isoformat(timespec="seconds")
        with self.connect() as conn:
            conn.execute("UPDATE saves SET name=?, updated_at=?, state_json=? WHERE id=?", (state.save_name, state.updated_at, state.model_dump_json(), save_id))
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
