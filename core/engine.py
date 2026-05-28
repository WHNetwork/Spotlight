from __future__ import annotations

from datetime import datetime
from typing import Dict, Any

from core.config import AppConfig
from core.llm import get_llm_provider, parse_turn_response
from core.models import GameState, TurnResponse, Choice, RouteInfo, SystemEvent
from core.prompts import build_messages
from core.rules import base_diff_for_action, apply_diff, sanitize_suggested_diff
from core.storage import SaveStorage
from core.systems import classify_turn, evaluate_all_systems
from core.talents import apply_talent_modifiers
from core.action_validator import validate_action, ActionValidationResult
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
from core.schedule_system import ensure_schedule_state, evaluate_schedule_system
from core.progression_system import ensure_progression_state, convert_growth_diff_to_progression
from core.skill_decay_system import ensure_skill_decay_state, evaluate_skill_decay_system
from core.debut_system import ensure_debut_state, evaluate_debut_system
from core.ending_system import ensure_ending_state, evaluate_ending_system


class TurnEngine:
    def __init__(self, storage: SaveStorage, config: AppConfig) -> None:
        self.storage = storage
        self.config = config
        self.provider = get_llm_provider(config)

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
        ensure_schedule_state(state)
        ensure_progression_state(state)
        ensure_skill_decay_state(state)
        ensure_debut_state(state)
        ensure_ending_state(state)

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

    def run_turn(
        self,
        save_id: int,
        state: GameState,
        player_action: str,
    ) -> tuple[GameState, TurnResponse, Dict[str, Any], RouteInfo, list[SystemEvent], ActionValidationResult]:
        """Run one turn using the selected LLM provider.

        This method works on a deep copy of the state until DeepSeek has returned
        valid JSON. If the API call fails, the caller's current state is not
        mutated and the save file is not updated.
        """
        validation = validate_action(state, player_action)
        action = validation.normalized_action

        working_state = state.model_copy(deep=True)

        route_info = classify_turn(action, working_state)
        actual_model = self.config.model_for_tier(route_info.model_tier)
        route_info.actual_model = actual_model

        time_events, time_diff, turn_duration_days = advance_time(working_state, route_info, action)
        advance_period(working_state, days=turn_duration_days)

        schedule_events, schedule_diff = evaluate_schedule_system(working_state, action, route_info)

        base_diff = base_diff_for_action(action, working_state)
        base_diff = apply_talent_modifiers(working_state, action, base_diff)
        for key, value in ability_passive_diff(working_state, action).items():
            base_diff[key] = base_diff.get(key, 0) + value

        base_diff, progression_events, progression_diff = convert_growth_diff_to_progression(
            working_state, action, base_diff, source="python"
        )
        skill_decay_events, skill_decay_diff = evaluate_skill_decay_system(working_state, action)
        debut_events, debut_diff = evaluate_debut_system(working_state, action)
        ending_events, ending_diff = evaluate_ending_system(working_state, action)

        system_events, system_diff = evaluate_all_systems(working_state, action)
        period_events, period_diff = evaluate_period_system(working_state, action)
        inner_events, inner_diff = evaluate_inner_life(working_state, action)
        relationship_events, relationship_diff = evaluate_relationship_system(working_state, action)
        school_events, school_diff = evaluate_school_family(working_state, action)
        social_events, social_diff = evaluate_social_context(working_state, action)
        safety_events, safety_diff = evaluate_safety_boundary(working_state, action)
        hierarchy_events, hierarchy_diff = evaluate_hierarchy_system(working_state, action)

        for extra_diff in [
            time_diff,
            schedule_diff,
            progression_diff,
            skill_decay_diff,
            debut_diff,
            ending_diff,
            period_diff,
            inner_diff,
            relationship_diff,
            school_diff,
            social_diff,
            safety_diff,
            hierarchy_diff,
        ]:
            for key, value in extra_diff.items():
                system_diff[key] = system_diff.get(key, 0) + value

        system_events = (
            validation.system_events
            + time_events
            + schedule_events
            + progression_events
            + skill_decay_events
            + debut_events
            + ending_events
            + system_events
            + period_events
            + inner_events
            + relationship_events
            + school_events
            + social_events
            + safety_events
            + hierarchy_events
        )

        crisis_events, crisis_diff = update_crises(working_state, action, system_events)
        system_events.extend(crisis_events)
        for key, value in crisis_diff.items():
            system_diff[key] = system_diff.get(key, 0) + value

        messages = build_messages(working_state, action, base_diff, system_diff, system_events, route_info, validation)
        raw = self.provider.generate(messages, model=actual_model)
        response = parse_turn_response(raw)

        suggested = sanitize_suggested_diff(working_state, response.suggested_diff, action)
        suggested, suggested_progression_events, suggested_progression_diff = convert_growth_diff_to_progression(
            working_state, action, suggested, source="model"
        )
        system_events.extend(suggested_progression_events)
        for key, value in suggested_progression_diff.items():
            system_diff[key] = system_diff.get(key, 0) + value

        merged_diff = dict(base_diff)
        for key, value in system_diff.items():
            if isinstance(value, int):
                merged_diff[key] = merged_diff.get(key, 0) + value
        for key, value in suggested.items():
            if isinstance(value, int):
                merged_diff[key] = merged_diff.get(key, 0) + value

        max_delta = 12 if route_info.turn_kind in {"crisis", "mainline"} else 8
        applied = apply_diff(working_state, merged_diff, max_abs_delta=max_delta)

        for key, (old, new) in applied.items():
            if new != old:
                working_state.growth_history.append(
                    f"Turn {working_state.turn + 1}: {key} {old}→{new}，来源行动：{action}"
                )

        ability_events = update_abilities(working_state)
        system_events.extend(ability_events)

        for event in system_events:
            if event.code not in [e.code for e in working_state.system_events]:
                working_state.system_events.append(event)
            for flag in event.new_flags:
                if flag and flag not in working_state.flags:
                    working_state.flags.append(flag)

        for warning in validation.warnings:
            flag = f"行动被阶段门控修正：{warning}"
            if flag not in working_state.flags:
                working_state.flags.append(flag)

        for flag in response.new_flags:
            if flag and flag not in working_state.flags:
                working_state.flags.append(flag)

        for flag in response.resolved_flags:
            if flag and flag not in working_state.resolved_flags:
                working_state.resolved_flags.append(flag)
            if flag in working_state.flags:
                working_state.flags.remove(flag)

        if response.public_summary:
            working_state.last_public_summary = response.public_summary
            if response.public_summary not in working_state.major_events:
                working_state.major_events.append(response.public_summary)

        if response.private_notes:
            working_state.last_private_notes = response.private_notes
            working_state.hidden_notes.append(response.private_notes)

        working_state.current_choices = response.choices
        working_state.turn += 1
        working_state.updated_at = datetime.now().isoformat(timespec="seconds")
        working_state.next_milestone = "等待玩家选择下一步行动"
        working_state.route_history.append(route_info)

        self.storage.update_save(save_id, working_state)
        self.storage.add_turn(
            save_id,
            working_state.turn,
            player_action,
            response,
            applied,
            route_info,
            system_events,
            validation.model_dump_json(),
        )

        return working_state, response, applied, route_info, system_events, validation
