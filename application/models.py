from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field

from core.day_settlement import DaySettlementResult
from core.evaluation import MonthlyEvaluationResult
from core.models import EventResult, GameState, SlotResolutionResult
from orchestration.event_director import EventDirectorCallResult
from orchestration.writing_context_models import PlayerTextGenerationStatus


class PendingEventChoiceView(BaseModel):
    """Player-visible choice metadata; mechanical effects stay server-side."""

    choice_id: str
    brief: str


class PendingEventView(BaseModel):
    """Transient presentation view of the currently durable PendingEvent."""

    event_instance_id: str
    event_id: str
    scene_text: Optional[str] = None
    scene_status: Optional[PlayerTextGenerationStatus] = None
    choices: List[PendingEventChoiceView] = Field(default_factory=list)


class SlotApplicationResult(BaseModel):
    state: GameState
    slot_result: SlotResolutionResult
    event_results: List[EventResult] = Field(default_factory=list)
    event_director_result: Optional[EventDirectorCallResult] = None
    pending_event_view: Optional[PendingEventView] = None
    day_completed: bool
    day_ready_to_finish: bool


class PendingChoiceApplicationResult(BaseModel):
    state: GameState
    event_result: EventResult
    day_completed: bool
    day_ready_to_finish: bool


class DayApplicationResult(BaseModel):
    state: GameState
    settlement_result: DaySettlementResult
    narrative_status: PlayerTextGenerationStatus
    narrative_text: Optional[str] = None
    diary_status: PlayerTextGenerationStatus
    diary_text: Optional[str] = None
    monthly_evaluation: Optional[MonthlyEvaluationResult] = None
    completed_game_date: date
    next_game_date: date
