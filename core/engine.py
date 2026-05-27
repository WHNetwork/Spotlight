from __future__ import annotations

from datetime import datetime
from typing import Dict, Any

from core.config import AppConfig
from core.llm import BaseProvider, DeepSeekProvider, MockProvider, parse_turn_response
from core.models import GameState, TurnResponse, Choice, RouteInfo, SystemEvent
from core.prompts import build_messages
from core.rules import base_diff_for_action, apply_diff, sanitize_suggested_diff
from core.storage import SaveStorage
from core.systems import classify_turn, evaluate_all_systems
from core.talents import generate_talents, apply_talent_modifiers
from core.action_validator import validate_action, ActionBlockedError, ActionValidationResult
from core.crisis import update_crises


class TurnEngine:
    def __init__(self, storage: SaveStorage, config: AppConfig, use_mock: bool = False) -> None:
        self.storage = storage
        self.config = config
        self.provider: BaseProvider = MockProvider() if use_mock else DeepSeekProvider(config)
        self.use_mock = use_mock

    def create_initial_state(self, character: Dict[str, Any]) -> GameState:
        state = GameState()
        state.save_name = character.get("艺名") or character.get("本名") or "KPOP 女团存档"
        state.character = character
        state.talents = generate_talents(character)
        state.current_stage = character.get("时间线", "练习生阶段")
        state.current_mainline = "初入公司"
        state.current_schedule = "第一天报到"
        state.next_milestone = "完成第一回合"

        identity = character.get("身份", "")
        if "运动员" in identity:
            state.body["体力"] = 88
            state.body["旧伤负担"] = 15
            state.career["舞蹈实力"] += 5
            state.mind["精神压力"] += 5
            state.market["话题度"] += 8
            state.flags.append("前运动员转型身份")
        if "海外" in identity:
            state.career["语言能力"] = 45
            state.mind["孤独感"] += 10
            state.flags.append("海外练习生身份")
        if "顶流" in identity or "妹妹" in identity or "亲属" in identity:
            state.market["话题度"] += 15
            state.fans["黑粉活跃度"] += 8
            state.flags.append("顶流亲属比较压力")
        if "选秀" in identity:
            state.fans["个人粉丝数"] += 3000
            state.fans["黑粉活跃度"] += 5
            state.flags.append("选秀淘汰者再挑战")
        if "再出道" in identity or "小公司" in identity:
            state.career["舞台感染力"] += 5
            state.mind["职业倦怠"] += 8
            state.flags.append("再出道压力")

        state.current_choices = [
            Choice(id="A", text="先观察公司和练习室氛围。"),
            Choice(id="B", text="主动向同期练习生打招呼。"),
            Choice(id="C", text="找经纪人了解训练安排。"),
            Choice(id="D", text="直接开始基础训练。"),
            Choice(id="E", text="自定义行动。"),
        ]
        return state

    def run_turn(self, save_id: int, state: GameState, player_action: str) -> tuple[GameState, TurnResponse, Dict[str, Any], RouteInfo, list[SystemEvent], ActionValidationResult]:
        validation = validate_action(state, player_action)
        action = validation.normalized_action

        route_info = classify_turn(action, state)
        actual_model = self.config.model_for_tier(route_info.model_tier)
        route_info.actual_model = "mock" if self.use_mock else actual_model

        base_diff = base_diff_for_action(action, state)
        base_diff = apply_talent_modifiers(state, action, base_diff)

        system_events, system_diff = evaluate_all_systems(state, action)
        system_events = validation.system_events + system_events

        crisis_events, crisis_diff = update_crises(state, action, system_events)
        system_events.extend(crisis_events)
        for key, value in crisis_diff.items():
            system_diff[key] = system_diff.get(key, 0) + value

        messages = build_messages(state, action, base_diff, system_diff, system_events, route_info, validation)
        raw = self.provider.generate(messages, model=actual_model)
        response = parse_turn_response(raw)

        suggested = sanitize_suggested_diff(state, response.suggested_diff, action)

        merged_diff = dict(base_diff)
        for key, value in system_diff.items():
            if isinstance(value, int):
                merged_diff[key] = merged_diff.get(key, 0) + value
        for key, value in suggested.items():
            if isinstance(value, int):
                merged_diff[key] = merged_diff.get(key, 0) + value

        max_delta = 12 if route_info.turn_kind in {"crisis", "mainline"} else 8
        applied = apply_diff(state, merged_diff, max_abs_delta=max_delta)

        for event in system_events:
            if event.code not in [e.code for e in state.system_events]:
                state.system_events.append(event)
            for flag in event.new_flags:
                if flag and flag not in state.flags:
                    state.flags.append(flag)

        for warning in validation.warnings:
            flag = f"行动被阶段门控修正：{warning}"
            if flag not in state.flags:
                state.flags.append(flag)

        for flag in response.new_flags:
            if flag and flag not in state.flags:
                state.flags.append(flag)

        for flag in response.resolved_flags:
            if flag and flag not in state.resolved_flags:
                state.resolved_flags.append(flag)
            if flag in state.flags:
                state.flags.remove(flag)

        if response.public_summary:
            state.last_public_summary = response.public_summary
            if response.public_summary not in state.major_events:
                state.major_events.append(response.public_summary)

        if response.private_notes:
            state.last_private_notes = response.private_notes
            state.hidden_notes.append(response.private_notes)

        state.current_choices = response.choices
        state.turn += 1
        state.updated_at = datetime.now().isoformat(timespec="seconds")
        state.next_milestone = "等待玩家选择下一步行动"
        state.route_history.append(route_info)

        self.storage.update_save(save_id, state)
        self.storage.add_turn(save_id, state.turn, player_action, response, applied, route_info, system_events, validation.model_dump_json())

        return state, response, applied, route_info, system_events, validation
