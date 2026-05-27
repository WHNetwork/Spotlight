from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List
from core.models import GameState, RouteInfo, SystemEvent
from core.rules import threshold_warnings
from core.action_validator import ActionValidationResult

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SYSTEM_PROMPT_PATH = DATA_DIR / "system_prompt.md"
MODULES_DIR = DATA_DIR / "modules"

def _read_md(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()

def load_system_prompt() -> str:
    sections: list[str] = []
    if SYSTEM_PROMPT_PATH.exists():
        sections.append(_read_md(SYSTEM_PROMPT_PATH))
    if MODULES_DIR.exists():
        for path in sorted(MODULES_DIR.glob("*.md")):
            sections.append(f"\n---\n\n<!-- MODULE: {path.name} -->\n\n{_read_md(path)}")
    return "\n\n".join(section for section in sections if section.strip())

def list_prompt_modules() -> List[str]:
    if not MODULES_DIR.exists():
        return []
    return [path.name for path in sorted(MODULES_DIR.glob("*.md"))]

def build_messages(
    state: GameState,
    player_action: str,
    base_diff: Dict[str, int],
    system_diff: Dict[str, int],
    system_events: List[SystemEvent],
    route_info: RouteInfo,
    validation: ActionValidationResult,
) -> List[Dict[str, str]]:
    user_payload = {
        "instruction": "请根据当前 GameState、玩家行动、行动合法性检查、Python 规则事件和 diff 生成下一回合。只返回 JSON。",
        "prompt_mode": "phase2_1_action_gated_systems",
        "loaded_modules": list_prompt_modules(),
        "route_info": route_info.model_dump(),
        "action_validation": validation.model_dump(),
        "player_action_original": validation.original_action,
        "player_action_normalized": validation.normalized_action,
        "base_diff_calculated_by_python": base_diff,
        "system_diff_calculated_by_python": system_diff,
        "system_events": [e.model_dump() for e in system_events],
        "threshold_warnings": threshold_warnings(state),
        "game_state": state.as_prompt_dict(),
    }
    return [
        {"role": "system", "content": load_system_prompt()},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, indent=2)},
    ]
