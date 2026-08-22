from core.event_definition import EventDefinition
from core.models import ConditionSignal as CS, ExplorationDomain as ED, SkillId as SK
from core.events.common import (
    CHAIN, CONDITIONAL, D, I, L, MINOR, N, P, all_of, choice,
    condition_effect, free_explore, free_train, skill_locked, skill_unlocked,
)


ACTING_EXPLORE = all_of(free_explore(ED.ACTING), skill_locked(SK.ACTING))
ACTING_TRAIN = all_of(free_train(SK.ACTING), skill_unlocked(SK.ACTING))
CREATION_EXPLORE = all_of(free_explore(ED.CREATION), skill_locked(SK.CREATION))
CREATION_TRAIN = all_of(free_train(SK.CREATION), skill_unlocked(SK.CREATION))


ACTING_CREATION_EVENTS = (
    # 256 explore_acting_first_observation
    EventDefinition(event_id="explore_acting_first_observation", category=CHAIN, trigger_mode=D, tier=MINOR, interaction_mode=N, priority=30, once=True, eligibility=ACTING_EXPLORE, director_brief="The player's acting exploration begins with deliberate observation of a short performance exercise."),
    # 257 explore_acting_script_marking_seen
    EventDefinition(event_id="explore_acting_script_marking_seen", category=CHAIN, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.20, priority=10, once=True, eligibility=ACTING_EXPLORE, director_brief="The player encounters a simple example of marking beats in a short script."),
    # 258 explore_acting_reaction_exercise_seen
    EventDefinition(event_id="explore_acting_reaction_exercise_seen", category=CHAIN, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.18, priority=10, once=True, eligibility=ACTING_EXPLORE, director_brief="The player observes how a basic reaction exercise is structured."),
    # 259 explore_acting_self_conscious_try
    EventDefinition(event_id="explore_acting_self_conscious_try", category=CHAIN, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.17, priority=10, eligibility=ACTING_EXPLORE, effects=(condition_effect(CS.CONFIDENCE_HIT),), director_brief="A very small private acting try feels more self-conscious than expected."),
    # 260 training_acting_first_unlocked_routine
    EventDefinition(event_id="training_acting_first_unlocked_routine", category=CHAIN, trigger_mode=D, tier=MINOR, interaction_mode=N, priority=30, once=True, eligibility=ACTING_TRAIN, director_brief="The first ordinary acting-training routine after unlock feels unfamiliar but concrete."),
    # 261 training_acting_objective_note
    EventDefinition(event_id="training_acting_objective_note", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.17, priority=10, cooldown_days=4, eligibility=ACTING_TRAIN, director_brief="The player writes a simple objective for a short practice scene."),
    # 262 training_acting_neutral_read
    EventDefinition(event_id="training_acting_neutral_read", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.18, priority=10, eligibility=ACTING_TRAIN, director_brief="A short script is read neutrally before adding interpretation."),
    # 263 training_acting_reaction_playback
    EventDefinition(event_id="training_acting_reaction_playback", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, cooldown_days=5, eligibility=ACTING_TRAIN, director_brief="The player reviews one brief acting reaction on internal playback."),
    # 264 explore_creation_first_structure
    EventDefinition(event_id="explore_creation_first_structure", category=CHAIN, trigger_mode=D, tier=MINOR, interaction_mode=N, priority=30, once=True, eligibility=CREATION_EXPLORE, director_brief="Creation exploration begins with identifying sections in a simple practice track."),
    # 265 explore_creation_demo_layers
    EventDefinition(event_id="explore_creation_demo_layers", category=CHAIN, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.18, priority=10, once=True, eligibility=CREATION_EXPLORE, director_brief="The player notices how a rough demo separates rhythm, guide, and main line."),
    # 266 explore_creation_lyric_or_rhythm_choice
    EventDefinition(event_id="explore_creation_lyric_or_rhythm_choice", category=CHAIN, trigger_mode=L, tier=MINOR, interaction_mode=I, base_probability=.46, priority=20, once=True, eligibility=CREATION_EXPLORE, director_brief="A short demo can be examined through words or rhythm.", choices=(choice("follow_lyric_structure", "从歌词结构入手"), choice("follow_rhythmic_structure", "从节奏结构入手"))),
    # 267 training_creation_first_unlocked_note
    EventDefinition(event_id="training_creation_first_unlocked_note", category=CHAIN, trigger_mode=L, tier=MINOR, interaction_mode=I, base_probability=.50, priority=20, once=True, eligibility=CREATION_TRAIN, director_brief="The first unlocked creation practice offers two basic note-taking approaches.", choices=(choice("note_structure_changes", "记录结构变化"), choice("note_melodic_repetitions", "记录旋律重复"))),
    # 268 training_creation_keep_or_discard_fragment
    EventDefinition(event_id="training_creation_keep_or_discard_fragment", category=CONDITIONAL, trigger_mode=L, tier=MINOR, interaction_mode=I, base_probability=.42, priority=20, cooldown_days=6, eligibility=CREATION_TRAIN, director_brief="A rough practice fragment is usable but unpolished.", choices=(choice("keep_fragment", "把这个片段留到以后", condition_effect(CS.CONFIDENCE_GAIN)), choice("discard_fragment", "删掉这个片段，重新开始", condition_effect(CS.STRESS_RELIEF)))),
    # 269 training_creation_reference_choice
    EventDefinition(event_id="training_creation_reference_choice", category=CONDITIONAL, trigger_mode=L, tier=MINOR, interaction_mode=I, base_probability=.44, priority=20, cooldown_days=5, eligibility=CREATION_TRAIN, director_brief="A practice reference can be examined from two technical angles.", choices=(choice("study_arrangement", "分析编排结构"), choice("study_phrasing", "分析乐句走向"))),
    # 270 training_creation_finish_or_leave_open
    EventDefinition(event_id="training_creation_finish_or_leave_open", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=I, base_probability=.15, priority=20, cooldown_days=5, eligibility=CREATION_TRAIN, director_brief="A small practice fragment reaches a reasonable stopping point.", choices=(choice("mark_endpoint", "先在这里告一段落", condition_effect(CS.CONFIDENCE_GAIN)), choice("leave_fragment_open", "先不收尾，之后再继续", condition_effect(CS.STRESS_RELIEF)))),
)
