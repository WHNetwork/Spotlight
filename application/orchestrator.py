from __future__ import annotations

from dataclasses import replace
from typing import Optional, Sequence

from core.day_settlement import resolve_day_settlement
from core.event_lifecycle import (
    finalize_post_slot_event_phase,
    prepare_post_slot_event_phase,
    resolve_pending_event_choice,
)
from core.event_models import EventSoftJudgment
from core.event_definition import EventDefinition
from core.event_triggers import EVENT_DEFINITIONS
from core.events.registry import build_event_definition_lookup
from core.free_actions import assign_free_action
from core.llm import BaseProvider
from core.models import (
    DailyWritingArtifactType,
    FreeAction,
    GameState,
    SlotKind,
    SlotResolutionResult,
)
from core.slot_resolution import resolve_current_slot
from core.storage import SaveStorage
from orchestration.daily_context import build_daily_writing_context
from orchestration.daily_narrative import (
    DailyNarrativeGenerationResult,
    generate_daily_narrative,
)
from orchestration.diary import DiaryGenerationResult, generate_diary_entry
from orchestration.event_director import (
    EventDirectorCallResult,
    EventDirectorStatus,
    build_event_director_context,
    run_event_director,
)
from orchestration.event_scene import build_event_scene_context, generate_event_scene
from orchestration.writing_context_models import PlayerTextGenerationStatus

from application.models import (
    DayApplicationResult,
    PendingChoiceApplicationResult,
    PendingEventChoiceView,
    PendingEventView,
    SlotApplicationResult,
)


class ApplicationOrchestratorError(ValueError):
    """Invalid application command ordering or persisted-state inconsistency."""


def perform_slot(
    save_id: int,
    free_action_intent: Optional[FreeAction] = None,
    event_scene_provider_name: Optional[str] = None,
    event_scene_provider: Optional[BaseProvider] = None,
    event_director_provider: Optional[BaseProvider] = None,
    event_definitions: Sequence[EventDefinition] = EVENT_DEFINITIONS,
) -> SlotApplicationResult:
    """Resolve one slot, its complete post-slot event phase, then checkpoint it."""
    storage = SaveStorage()
    state = _load_state(storage, save_id)

    if state.pending_event is not None:
        raise ApplicationOrchestratorError(
            "The save has a pending event; resolve_pending_choice() must run before another slot."
        )
    if state.day.is_day_complete:
        raise ApplicationOrchestratorError(
            "All eight slots are complete; finish_day() must run before another slot."
        )
    current_index = state.day.current_slot
    if current_index is None:
        raise ApplicationOrchestratorError("The persisted day has no current pending slot.")
    current_slot = state.day.slots[current_index]

    if current_slot.kind == SlotKind.FREE:
        if free_action_intent is None:
            raise ApplicationOrchestratorError("The current FREE slot requires a FreeAction intent.")
        assign_free_action(
            state.day,
            state.skills,
            free_action_intent,
            state.npcs,
        )
    elif free_action_intent is not None:
        raise ApplicationOrchestratorError(
            f"The current {current_slot.kind.value} slot does not accept a FreeAction intent."
        )

    post_slot_state, slot_result = resolve_current_slot(state)
    history = storage.build_event_history_snapshot(save_id, post_slot_state.time.current_date)
    preparation = prepare_post_slot_event_phase(
        post_slot_state,
        slot_result,
        event_definitions,
        history,
    )

    director_result: Optional[EventDirectorCallResult] = None
    soft_judgment = None
    if preparation.evaluation.llm_assisted:
        recent_events = storage.load_event_results(save_id)
        director_context = build_event_director_context(
            post_slot_state,
            slot_result,
            preparation.evaluation.llm_assisted,
            recent_events,
        )
        director_result = run_event_director(
            director_context,
            provider=event_director_provider,
        )
        if director_result.status in (
            EventDirectorStatus.SUCCESS,
            EventDirectorStatus.REPAIRED_SUCCESS,
        ) and director_result.judgment is not None:
            soft_judgment = director_result.judgment
        else:
            # Event Director is a soft judgment. External/format failure closes only
            # the assisted path; deterministic and probabilistic candidates still
            # go through Core finalization below.
            soft_judgment = EventSoftJudgment(should_trigger_any=False, scores=[])

    final_state, event_outcome = finalize_post_slot_event_phase(
        post_slot_state,
        preparation,
        event_definitions,
        soft_judgment,
    )
    storage.save_slot_checkpoint(final_state, slot_result, event_outcome)

    durable_state = _load_state(storage, save_id)
    pending_view = None
    if event_outcome.pending_event is not None:
        pending_view = _build_pending_event_view(
            storage=storage,
            save_id=save_id,
            durable_state=durable_state,
            event_definitions=event_definitions,
            provider_name=event_scene_provider_name,
            provider=event_scene_provider,
        )
    elif durable_state.pending_event is not None:
        raise ApplicationOrchestratorError(
            "Durable state contains a PendingEvent inconsistent with the slot event outcome."
        )
    event_results = (
        [event_outcome.event_result]
        if event_outcome.event_result is not None
        else []
    )
    return SlotApplicationResult(
        state=durable_state,
        slot_result=slot_result,
        event_results=event_results,
        event_director_result=director_result,
        pending_event_view=pending_view,
        day_completed=durable_state.day.is_day_complete,
        day_ready_to_finish=_day_ready_to_finish(durable_state),
    )


def get_pending_event_view(
    save_id: int,
    event_scene_provider_name: Optional[str] = None,
    event_scene_provider: Optional[BaseProvider] = None,
    event_definitions: Sequence[EventDefinition] = EVENT_DEFINITIONS,
) -> PendingEventView:
    """Recover the current durable PendingEvent, its Scene, and official choices."""
    storage = SaveStorage()
    durable_state = _load_state(storage, save_id)
    if durable_state.pending_event is None:
        raise ApplicationOrchestratorError(
            "The save has no pending event to recover."
        )
    return _build_pending_event_view(
        storage=storage,
        save_id=save_id,
        durable_state=durable_state,
        event_definitions=event_definitions,
        provider_name=event_scene_provider_name,
        provider=event_scene_provider,
    )


def resolve_pending_choice(
    save_id: int,
    choice_id: str,
    event_definitions: Sequence[EventDefinition] = EVENT_DEFINITIONS,
) -> PendingChoiceApplicationResult:
    """Resolve the durable PendingEvent choice and atomically persist its result."""
    storage = SaveStorage()
    state = _load_state(storage, save_id)
    if state.pending_event is None:
        raise ApplicationOrchestratorError("The save has no pending event to resolve.")

    new_state, event_result = resolve_pending_event_choice(
        state,
        event_definitions,
        choice_id,
    )
    storage.save_event_resolution_checkpoint(new_state, event_result)
    durable_state = _load_state(storage, save_id)
    return PendingChoiceApplicationResult(
        state=durable_state,
        event_result=event_result,
        day_completed=durable_state.day.is_day_complete,
        day_ready_to_finish=_day_ready_to_finish(durable_state),
    )


def finish_day(
    save_id: int,
    narrative_provider_name: str,
    diary_provider_name: str,
    narrative_provider: Optional[BaseProvider] = None,
    diary_provider: Optional[BaseProvider] = None,
    event_definitions: Sequence[EventDefinition] = EVENT_DEFINITIONS,
) -> DayApplicationResult:
    """Create/reuse daily writing artifacts and settle one completed day."""
    storage = SaveStorage()
    completed_day_state = _load_state(storage, save_id)
    if not completed_day_state.day.is_day_complete:
        raise ApplicationOrchestratorError(
            "The persisted day is not complete; all eight slots must finish first."
        )
    if completed_day_state.pending_event is not None:
        raise ApplicationOrchestratorError(
            "The persisted day has a pending event; its choice must be resolved first."
        )

    completed_game_date = completed_day_state.time.current_date
    slot_results = storage.load_slot_results(save_id, completed_game_date)
    _validate_complete_slot_history(completed_day_state, slot_results)
    event_results = storage.load_event_results(save_id, completed_game_date)

    next_state, settlement_result = resolve_day_settlement(completed_day_state)
    daily_context = build_daily_writing_context(
        completed_day_state,
        slot_results,
        event_results,
        settlement_result,
        event_definition_by_id=build_event_definition_lookup(event_definitions),
    )

    narrative_result = _load_or_generate_narrative(
        storage,
        save_id,
        completed_game_date,
        daily_context,
        narrative_provider_name,
        narrative_provider,
    )
    diary_result = _load_or_generate_diary(
        storage,
        save_id,
        completed_game_date,
        daily_context,
        diary_provider_name,
        diary_provider,
    )

    # Generation and artifact writes above use their own short DB operations.
    # The mechanical settlement is a separate atomic checkpoint with no LLM call
    # inside its transaction.
    storage.save_day_settlement_checkpoint(next_state, settlement_result)
    durable_next_state = _load_state(storage, save_id)
    return DayApplicationResult(
        state=durable_next_state,
        settlement_result=settlement_result,
        narrative_status=narrative_result.status,
        narrative_text=narrative_result.text,
        diary_status=diary_result.status,
        diary_text=diary_result.text,
        monthly_evaluation=settlement_result.monthly_evaluation,
        completed_game_date=completed_game_date,
        next_game_date=durable_next_state.time.current_date,
    )


def _load_state(storage: SaveStorage, save_id: int) -> GameState:
    try:
        state = storage.load_save(save_id)
    except ValueError as exc:
        raise ApplicationOrchestratorError(
            f"Unable to load authoritative save_id={save_id}: {exc}"
        ) from exc
    if state.meta.save_id != save_id:
        raise ApplicationOrchestratorError(
            f"Persisted state save_id mismatch: requested {save_id}, state has {state.meta.save_id}."
        )
    return state


def _find_event_definition(
    definitions: Sequence[EventDefinition],
    event_id: str,
) -> EventDefinition:
    for definition in definitions:
        if definition.event_id == event_id:
            return definition
    raise ApplicationOrchestratorError(
        f"Missing EventDefinition for persisted event_id={event_id}."
    )


def _build_pending_event_view(
    storage: SaveStorage,
    save_id: int,
    durable_state: GameState,
    event_definitions: Sequence[EventDefinition],
    provider_name: Optional[str],
    provider: Optional[BaseProvider],
) -> PendingEventView:
    pending = durable_state.pending_event
    if pending is None:
        raise ApplicationOrchestratorError(
            "The durable state has no pending event to build a view from."
        )

    definition = _find_event_definition(event_definitions, pending.event_id)
    choice_definitions = _ordered_pending_choice_definitions(definition, pending.available_choice_ids)
    choices = [
        PendingEventChoiceView(choice_id=choice.choice_id, brief=choice.director_brief)
        for choice in choice_definitions
    ]

    artifact = storage.load_event_scene_artifact(save_id, pending.event_instance_id)
    scene_text = None
    scene_status = None
    if artifact is not None:
        scene_text = artifact.content
        scene_status = PlayerTextGenerationStatus.SUCCESS
    elif provider_name is not None:
        slot_result = _load_pending_trigger_slot_result(storage, save_id, durable_state)
        # EventSceneContext validates choices against PendingEvent. Use the durable
        # choice list in its original order, while retaining the official choice
        # definitions and all other current EventDefinition metadata.
        scene_definition = replace(definition, choices=tuple(choice_definitions))
        try:
            scene_context = build_event_scene_context(
                durable_state,
                scene_definition,
                slot_result,
            )
        except ValueError as exc:
            raise ApplicationOrchestratorError(
                f"Unable to build Event Scene context for pending event {pending.event_id}: {exc}"
            ) from exc
        scene_result = generate_event_scene(
            scene_context,
            provider_name,
            provider=provider,
        )
        scene_status = scene_result.status
        if (
            scene_result.status == PlayerTextGenerationStatus.SUCCESS
            and scene_result.text is not None
        ):
            scene_text = scene_result.text
            storage.save_event_scene_artifact(
                save_id=save_id,
                event_instance_id=pending.event_instance_id,
                game_date=pending.triggered_date,
                event_id=pending.event_id,
                slot_index=pending.trigger_slot_index,
                content=scene_result.text,
                provider_name=provider_name,
            )

    return PendingEventView(
        event_instance_id=pending.event_instance_id,
        event_id=pending.event_id,
        scene_text=scene_text,
        scene_status=scene_status,
        choices=choices,
    )


def _ordered_pending_choice_definitions(definition, available_choice_ids):
    choices_by_id = {}
    for choice in definition.choices:
        if choice.choice_id in choices_by_id:
            raise ApplicationOrchestratorError(
                f"EventDefinition {definition.event_id} contains duplicate choice_id={choice.choice_id}."
            )
        choices_by_id[choice.choice_id] = choice

    ordered = []
    seen_pending_ids = set()
    for choice_id in available_choice_ids:
        if choice_id in seen_pending_ids:
            raise ApplicationOrchestratorError(
                f"PendingEvent {definition.event_id} contains duplicate choice_id={choice_id}."
            )
        seen_pending_ids.add(choice_id)
        choice = choices_by_id.get(choice_id)
        if choice is None:
            raise ApplicationOrchestratorError(
                f"PendingEvent choice_id={choice_id} is missing from EventDefinition {definition.event_id}."
            )
        ordered.append(choice)
    return ordered


def _load_pending_trigger_slot_result(
    storage: SaveStorage,
    save_id: int,
    durable_state: GameState,
) -> SlotResolutionResult:
    pending = durable_state.pending_event
    if pending is None:
        raise ApplicationOrchestratorError(
            "The durable state has no pending event with a trigger SlotResult."
        )
    if pending.triggered_date > durable_state.time.current_date:
        raise ApplicationOrchestratorError(
            f"PendingEvent triggered_date={pending.triggered_date} is later than the persisted "
            f"current_date={durable_state.time.current_date}."
        )
    try:
        results = storage.load_slot_results(save_id, pending.triggered_date)
    except ValueError as exc:
        raise ApplicationOrchestratorError(
            f"Unable to load trigger slot history for pending event {pending.event_id}: {exc}"
        ) from exc
    matches = [
        result
        for result in results
        if result.slot_index == pending.trigger_slot_index
    ]
    if len(matches) != 1:
        raise ApplicationOrchestratorError(
            f"PendingEvent {pending.event_id} requires exactly one SlotResult for "
            f"date={pending.triggered_date}, slot_index={pending.trigger_slot_index}; "
            f"found {len(matches)}."
        )
    return matches[0]


def _validate_complete_slot_history(completed_day_state, slot_results) -> None:
    if len(slot_results) != 8:
        raise ApplicationOrchestratorError(
            f"Completed-day slot history must contain exactly 8 rows; found {len(slot_results)}."
        )
    indexes = [result.slot_index for result in slot_results]
    if indexes != list(range(8)):
        raise ApplicationOrchestratorError(
            f"Completed-day slot history must be ordered and unique from 0 through 7; found {indexes}."
        )
    for result in slot_results:
        if not result.completed:
            raise ApplicationOrchestratorError(
                f"Slot history row {result.slot_index} is not completed."
            )
        slot = completed_day_state.day.slots[result.slot_index]
        if (
            result.slot_kind != slot.kind
            or result.company_course != slot.company_course
            or result.free_action != slot.free_action
        ):
            raise ApplicationOrchestratorError(
                f"Slot history row {result.slot_index} does not match the persisted completed day."
            )


def _load_or_generate_narrative(
    storage,
    save_id,
    game_date,
    context,
    provider_name,
    provider,
) -> DailyNarrativeGenerationResult:
    existing = storage.load_daily_writing_artifact(
        save_id,
        game_date,
        DailyWritingArtifactType.DAILY_NARRATIVE,
    )
    if existing is not None:
        return DailyNarrativeGenerationResult(
            status=PlayerTextGenerationStatus.SUCCESS,
            text=existing.content,
            provider_name=existing.provider_name,
        )
    result = generate_daily_narrative(context, provider_name, provider=provider)
    if result.status == PlayerTextGenerationStatus.SUCCESS and result.text is not None:
        storage.save_daily_writing_artifact(
            save_id,
            game_date,
            DailyWritingArtifactType.DAILY_NARRATIVE,
            result.text,
            provider_name,
        )
    return result


def _load_or_generate_diary(
    storage,
    save_id,
    game_date,
    context,
    provider_name,
    provider,
) -> DiaryGenerationResult:
    existing = storage.load_daily_writing_artifact(
        save_id,
        game_date,
        DailyWritingArtifactType.DIARY,
    )
    if existing is not None:
        return DiaryGenerationResult(
            status=PlayerTextGenerationStatus.SUCCESS,
            text=existing.content,
            provider_name=existing.provider_name,
        )
    result = generate_diary_entry(context, provider_name, provider=provider)
    if result.status == PlayerTextGenerationStatus.SUCCESS and result.text is not None:
        storage.save_daily_writing_artifact(
            save_id,
            game_date,
            DailyWritingArtifactType.DIARY,
            result.text,
            provider_name,
        )
    return result


def _day_ready_to_finish(state: GameState) -> bool:
    return state.day.is_day_complete and state.pending_event is None
