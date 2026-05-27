from __future__ import annotations

import tempfile
from pathlib import Path

from core.config import AppConfig
from core.storage import SaveStorage
from core.engine import TurnEngine
from core.character_validator import validate_character_input


def make_character():
    return validate_character_input({
        "艺名": "Luna",
        "本名": "林娜",
        "年龄": "18",
        "身高": "166",
        "国籍": "中国",
        "身份": "海外追梦练习生",
        "时间线": "练习生阶段",
        "生理周期系统": "简化",
        "特长": "舞蹈",
        "弱项": "声乐",
        "家庭状况": "父母支持但担心学业",
        "出身来源标签": ["校园舞蹈社"],
    }).data


if __name__ == "__main__":
    config = AppConfig()
    if not config.get_api_key_fallback():
        print("[SKIP] 没有 DeepSeek API Key，跳过真实 API 集成测试。")
        raise SystemExit(0)

    tmp = tempfile.TemporaryDirectory()
    storage = SaveStorage(Path(tmp.name) / "saves.db")
    engine = TurnEngine(storage, config)
    state = engine.create_initial_state(make_character())
    save_id = storage.create_save(state)

    state, response, applied, route, events, validation = engine.run_turn(
        save_id,
        state,
        "我先观察练习室和同期练习生的氛围。",
    )

    assert state.turn == 1
    assert response.narrative
    assert route.actual_model
    print("[PASS] DeepSeek API 真实回合调用成功。")
