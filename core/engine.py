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
from core.talents import apply_talent_modifiers
from core.action_validator import validate_action, ActionBlockedError, ActionValidationResult
from core.crisis import update_crises
from core.initial_allocator import allocate_initial_state
from core.abilities import update_abilities, ability_passive_diff
from core.period_system import default_period_state, advance_period, evaluate_period_system
from core.inner_life import default_inner_life, evaluate_inner_life
from core.relationship_system import ensure_default_relationships, evaluate_relationship_system
from core.time_system import default_time_context, compute_age_group, advance_time
from core.social_context import default_social_context, evaluate_social_context
from core.school_family import default_school_context, default_family_context, evaluate_school_family
from core.safety_boundary import default_safety_context, evaluate_safety_boundary
from core.hierarchy_system import default_hierarchy_context, evaluate_hierarchy_system


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
        age = character.get("年龄")
        try:
            age_int = int(age) if age is not None and age != "" else None
        except Exception:
            age_int = None
        state.age_context = compute_age_group(age_int)
        state.time = default_time_context(age_int)
        state.current_stage = character.get("时间线", "练习生阶段")
        state.current_mainline = "初入公司"
        state.current_schedule = "第一天报到"
        state.next_milestone = "完成第一回合"

        allocate_initial_state(state, character)
        state.social_context = default_social_context(character)
        state.school = default_school_context(state.age_context, character)
        state.family = default_family_context(state.age_context, character, state.social_context)
        state.safety = default_safety_context(state.age_context)
        state.hierarchy = default_hierarchy_context(state.social_context)
        mode = str(character.get("生理周期系统", "简化") or "简化")
        state.period = default_period_state(enabled=(mode != "关闭"), mode=mode)
        state.inner_life = default_inner_life()
        ensure_default_relationships(state)
        for tag in state.profile_tags:
            flag = f"身份标签：{tag}"
            if flag not in state.flags:
                state.flags.append(flag)
        ability_events = update_abilities(state)
        for ev in ability_events:
            state.system_events.append(ev)
            for flag in ev.new_flags:
                if flag not in state.flags:
                    state.flags.append(flag)

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

        time_events, time_diff, turn_duration_days = advance_time(state, route_info, action)
        advance_period(state, days=turn_duration_days)

        base_diff = base_diff_for_action(action, state)
        base_diff = apply_talent_modifiers(state, action, base_diff)
        for key, value in ability_passive_diff(state, action).items():
            base_diff[key] = base_diff.get(key, 0) + value

        system_events, system_diff = evaluate_all_systems(state, action)
        period_events, period_diff = evaluate_period_system(state, action)
        inner_events, inner_diff = evaluate_inner_life(state, action)
        relationship_events, relationship_diff = evaluate_relationship_system(state, action)
        school_events, school_diff = evaluate_school_family(state, action)
        social_events, social_diff = evaluate_social_context(state, action)
        safety_events, safety_diff = evaluate_safety_boundary(state, action)
        hierarchy_events, hierarchy_diff = evaluate_hierarchy_system(state, action)

        for extra_diff in [time_diff, period_diff, inner_diff, relationship_diff, school_diff, social_diff, safety_diff, hierarchy_diff]:
            for key, value in extra_diff.items():
                system_diff[key] = system_diff.get(key, 0) + value

        system_events = validation.system_events + time_events + system_events + period_events + inner_events + relationship_events + school_events + social_events + safety_events + hierarchy_events

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

        # Record growth sources.
        for key, (old, new) in applied.items():
            if new != old:
                state.growth_history.append(f"Turn {state.turn + 1}: {key} {old}→{new}，来源行动：{action}")

        ability_events = update_abilities(state)
        system_events.extend(ability_events)

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
