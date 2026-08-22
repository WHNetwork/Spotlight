from core.event_definition import EventDefinition
from core.models import CompanyCourse as CC, ConditionSignal as CS, RelationshipSignal as RS
from core.events.common import (
    CONDITIONAL, I, L, MINOR, N, OPPORTUNITY, P, RELATIONSHIP, ROSTER,
    SCHEDULED, STAFF, TEACHER, TRAINEE, all_of, bound_relationship, choice,
    company_course, company_skill_course, company_slot, condition_effect,
    condition_range, relationship_effect, teacher_matches_course,
)


TRAINING_EVENTS = (
    # 001 training_vocal_warmup_settles
    EventDefinition(event_id="training_vocal_warmup_settles", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.20, priority=10, eligibility=company_course(CC.VOCAL), director_brief="The normal warm-up takes longer, then settles."),
    # 002 training_vocal_breathing_clicks
    EventDefinition(event_id="training_vocal_breathing_clicks", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.22, priority=10, eligibility=company_course(CC.VOCAL), effects=(condition_effect(CS.CONFIDENCE_GAIN),), director_brief="A familiar breathing drill feels unusually workable."),
    # 003 training_vocal_phrase_reset
    EventDefinition(event_id="training_vocal_phrase_reset", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.18, priority=10, eligibility=company_course(CC.VOCAL), director_brief="Repeating one phrase after a reset improves consistency."),
    # 004 training_vocal_high_note_strain_check
    EventDefinition(event_id="training_vocal_high_note_strain_check", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.16, priority=10, eligibility=all_of(company_course(CC.VOCAL), condition_range("stress", 35)), effects=(condition_effect(CS.STRESS_RELIEF),), director_brief="The player notices strain and returns to a safer exercise."),
    # 005 training_vocal_pitch_reference_delay
    EventDefinition(event_id="training_vocal_pitch_reference_delay", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.18, priority=10, eligibility=company_course(CC.VOCAL), director_brief="A pitch reference takes several extra repetitions to match."),
    # 006 training_vocal_recording_reassures
    EventDefinition(event_id="training_vocal_recording_reassures", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, eligibility=company_course(CC.VOCAL), effects=(condition_effect(CS.MOOD_LIFT),), director_brief="A short practice playback sounds steadier than expected."),
    # 007 training_vocal_consonant_focus
    EventDefinition(event_id="training_vocal_consonant_focus", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.17, priority=10, eligibility=company_course(CC.VOCAL), director_brief="The session spends extra time on consonant clarity."),
    # 008 training_vocal_room_dryness
    EventDefinition(event_id="training_vocal_room_dryness", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.12, priority=10, eligibility=company_course(CC.VOCAL), effects=(condition_effect(CS.STRESS_INCREASE),), director_brief="Dry air makes the player pace vocal repetitions more carefully."),
    # 009 training_dance_mirror_lineup
    EventDefinition(event_id="training_dance_mirror_lineup", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.18, priority=10, eligibility=company_course(CC.DANCE), director_brief="The completed dance class reveals spacing through the mirror lineup."),
    # 010 training_dance_count_recovery
    EventDefinition(event_id="training_dance_count_recovery", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.20, priority=10, eligibility=company_course(CC.DANCE), effects=(condition_effect(CS.CONFIDENCE_GAIN),), director_brief="The player loses counts briefly and rejoins without stopping."),
    # 011 training_dance_floor_markers
    EventDefinition(event_id="training_dance_floor_markers", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.16, priority=10, eligibility=company_course(CC.DANCE), director_brief="Temporary floor markers change how the combination is spaced."),
    # 012 training_dance_tempo_frustration
    EventDefinition(event_id="training_dance_tempo_frustration", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, eligibility=all_of(company_course(CC.DANCE), condition_range("mood", 0, 69)), effects=(condition_effect(CS.MOOD_HIT),), director_brief="A faster tempo repeatedly catches the player late."),
    # 013 training_dance_left_right_asymmetry
    EventDefinition(event_id="training_dance_left_right_asymmetry", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.18, priority=10, eligibility=company_course(CC.DANCE), director_brief="The same movement feels less coordinated on one side."),
    # 014 training_dance_clean_transition
    EventDefinition(event_id="training_dance_clean_transition", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.17, priority=10, eligibility=company_course(CC.DANCE), effects=(condition_effect(CS.MOOD_LIFT),), director_brief="A previously awkward transition becomes clean for several runs."),
    # 015 training_dance_shared_music_delay
    EventDefinition(event_id="training_dance_shared_music_delay", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.13, priority=10, eligibility=company_course(CC.DANCE), director_brief="A delay restarting the music breaks the repetition rhythm."),
    # 016 training_dance_front_row_pressure
    EventDefinition(event_id="training_dance_front_row_pressure", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.12, priority=10, eligibility=all_of(company_course(CC.DANCE), condition_range("stress", 0, 94)), effects=(condition_effect(CS.STRESS_INCREASE),), director_brief="A routine rotation places the player at the front for a run."),
    # 017 training_dance_silent_run
    EventDefinition(event_id="training_dance_silent_run", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.15, priority=10, eligibility=company_course(CC.DANCE), director_brief="The group marks the combination once without music."),
    # 018 training_dance_endurance_pacing
    EventDefinition(event_id="training_dance_endurance_pacing", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, eligibility=all_of(company_course(CC.DANCE), condition_range("stress", 35)), effects=(condition_effect(CS.STRESS_RELIEF),), director_brief="The player deliberately paces the final repetitions instead of rushing."),
    # 019 training_rap_metronome_entry
    EventDefinition(event_id="training_rap_metronome_entry", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.18, priority=10, eligibility=company_course(CC.RAP), director_brief="The metronome makes an early entry obvious."),
    # 020 training_rap_breath_map_confidence
    EventDefinition(event_id="training_rap_breath_map_confidence", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.18, priority=10, eligibility=company_course(CC.RAP), effects=(condition_effect(CS.CONFIDENCE_GAIN),), director_brief="Adding breath marks makes one practice verse manageable."),
    # 021 training_rap_word_substitution
    EventDefinition(event_id="training_rap_word_substitution", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.15, priority=10, eligibility=company_course(CC.RAP), director_brief="A difficult practice word is temporarily substituted to preserve flow."),
    # 022 training_rap_rhythm_slip_annoys
    EventDefinition(event_id="training_rap_rhythm_slip_annoys", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, eligibility=company_course(CC.RAP), effects=(condition_effect(CS.MOOD_HIT),), director_brief="The same rhythm slip repeats across several takes."),
    # 023 training_rap_low_volume_run
    EventDefinition(event_id="training_rap_low_volume_run", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.16, priority=10, eligibility=company_course(CC.RAP), director_brief="A low-volume run makes articulation easier to inspect."),
    # 024 training_rap_memory_hold
    EventDefinition(event_id="training_rap_memory_hold", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, eligibility=company_course(CC.RAP), effects=(condition_effect(CS.MOOD_LIFT),), director_brief="One full practice section stays in memory without a prompt."),
    # 025 training_stage_entry_marks
    EventDefinition(event_id="training_stage_entry_marks", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.16, priority=10, eligibility=company_course(CC.STAGE), director_brief="Stage class temporarily establishes entry and exit marks."),
    # 026 training_stage_eye_line_confidence
    EventDefinition(event_id="training_stage_eye_line_confidence", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.17, priority=10, cooldown_days=2, eligibility=company_course(CC.STAGE), effects=(condition_effect(CS.CONFIDENCE_GAIN),), director_brief="A changed eye line makes the run feel more deliberate."),
    # 027 training_stage_prop_handoff
    EventDefinition(event_id="training_stage_prop_handoff", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.13, priority=10, cooldown_days=2, eligibility=company_course(CC.STAGE), director_brief="A simple practice prop handoff requires an extra reset."),
    # 028 training_stage_empty_room_nerves
    EventDefinition(event_id="training_stage_empty_room_nerves", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.13, priority=10, cooldown_days=3, eligibility=all_of(company_course(CC.STAGE), condition_range("confidence", 0, 69)), effects=(condition_effect(CS.CONFIDENCE_HIT),), director_brief="Even an empty-room stage run feels unexpectedly exposing."),
    # 029 training_stage_position_swap
    EventDefinition(event_id="training_stage_position_swap", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.16, priority=10, cooldown_days=2, eligibility=company_course(CC.STAGE), director_brief="A routine position swap changes what the player must track."),
    # 030 training_stage_finish_pose_relief
    EventDefinition(event_id="training_stage_finish_pose_relief", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.15, priority=10, cooldown_days=2, eligibility=company_course(CC.STAGE), effects=(condition_effect(CS.STRESS_RELIEF),), director_brief="The finish pose holds cleanly after several unstable attempts."),
    # 031 training_stage_cue_wait
    EventDefinition(event_id="training_stage_cue_wait", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.12, priority=10, cooldown_days=3, eligibility=company_course(CC.STAGE), director_brief="The player waits through a longer-than-usual cue before entering."),
    # 032 training_stage_expression_flat
    EventDefinition(event_id="training_stage_expression_flat", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, cooldown_days=3, eligibility=company_course(CC.STAGE), effects=(condition_effect(CS.CONFIDENCE_HIT),), director_brief="A practice run reads flatter than the player intended."),
    # 033 training_stage_group_reset
    EventDefinition(event_id="training_stage_group_reset", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.18, priority=10, cooldown_days=2, eligibility=company_course(CC.STAGE), director_brief="The whole practice group resets after a cue becomes unclear."),
    # 034 training_camera_lens_check
    EventDefinition(event_id="training_camera_lens_check", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.18, priority=10, cooldown_days=2, eligibility=company_course(CC.CAMERA), effects=(condition_effect(CS.CONFIDENCE_GAIN),), director_brief="A lens check establishes where the player should look."),
    # 035 training_camera_playback_posture
    EventDefinition(event_id="training_camera_playback_posture", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.17, priority=10, cooldown_days=3, eligibility=company_course(CC.CAMERA), director_brief="Playback reveals a small posture habit during introductions."),
    # 036 training_camera_intro_stumble
    EventDefinition(event_id="training_camera_intro_stumble", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, cooldown_days=3, eligibility=company_course(CC.CAMERA), effects=(condition_effect(CS.MOOD_HIT),), director_brief="A practice introduction comes out more awkwardly than expected."),
    # 037 training_camera_mark_missed
    EventDefinition(event_id="training_camera_mark_missed", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.16, priority=10, cooldown_days=2, eligibility=company_course(CC.CAMERA), director_brief="The player steps just past a camera floor mark and resets."),
    # 038 training_camera_second_take_eases
    EventDefinition(event_id="training_camera_second_take_eases", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.16, priority=10, cooldown_days=2, eligibility=company_course(CC.CAMERA), effects=(condition_effect(CS.STRESS_RELIEF),), director_brief="A second internal take feels less stiff than the first."),
    # 039 training_camera_background_wait
    EventDefinition(event_id="training_camera_background_wait", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.13, priority=10, cooldown_days=2, eligibility=company_course(CC.CAMERA), director_brief="Another trainee records first while the player waits off mark."),
    # 040 training_camera_audio_restart
    EventDefinition(event_id="training_camera_audio_restart", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.11, priority=10, cooldown_days=3, eligibility=company_course(CC.CAMERA), effects=(condition_effect(CS.STRESS_INCREASE),), director_brief="A minor audio issue requires the internal take to restart."),
    # 041 training_camera_neutral_expression
    EventDefinition(event_id="training_camera_neutral_expression", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.14, priority=10, cooldown_days=3, eligibility=company_course(CC.CAMERA), director_brief="A neutral-expression drill feels less natural than smiling."),
    # 042 training_language_script_distribution
    EventDefinition(event_id="training_language_script_distribution", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.16, priority=10, cooldown_days=3, eligibility=company_course(CC.LANGUAGE), director_brief="A new short language-practice script is distributed."),
    # 043 training_language_pronunciation_pair
    EventDefinition(event_id="training_language_pronunciation_pair", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.18, priority=10, cooldown_days=3, eligibility=company_course(CC.LANGUAGE), director_brief="Two similar sounds require repeated contrast practice."),
    # 044 training_language_fast_prompt
    EventDefinition(event_id="training_language_fast_prompt", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.13, priority=10, cooldown_days=3, eligibility=company_course(CC.LANGUAGE), director_brief="A faster prompt briefly outpaces the player's recall."),
    # 045 training_language_self_correction
    EventDefinition(event_id="training_language_self_correction", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.16, priority=10, cooldown_days=2, eligibility=company_course(CC.LANGUAGE), director_brief="The player catches and corrects a word-order error mid-drill."),
    # 046 training_language_caption_compare
    EventDefinition(event_id="training_language_caption_compare", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.12, priority=10, cooldown_days=4, eligibility=company_course(CC.LANGUAGE), director_brief="Comparing two short captions clarifies a usage difference."),
    # 047 training_language_name_intonation
    EventDefinition(event_id="training_language_name_intonation", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.15, priority=10, cooldown_days=3, eligibility=company_course(CC.LANGUAGE), director_brief="The class practices neutral intonation for self-introductions."),
    # 048 training_fitness_cooldown_required
    EventDefinition(event_id="training_fitness_cooldown_required", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.17, priority=10, cooldown_days=2, eligibility=company_course(CC.FITNESS), director_brief="The completed fitness block uses a longer cooldown than usual."),
    # 049 training_fitness_balance_station
    EventDefinition(event_id="training_fitness_balance_station", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.16, priority=10, cooldown_days=3, eligibility=company_course(CC.FITNESS), director_brief="One balance station feels noticeably less stable on one side."),
    # 050 training_fitness_pace_group
    EventDefinition(event_id="training_fitness_pace_group", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.17, priority=10, cooldown_days=2, eligibility=company_course(CC.FITNESS), director_brief="The group's pace changes between exercise rounds."),
    # 051 training_fitness_form_reset
    EventDefinition(event_id="training_fitness_form_reset", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.15, priority=10, cooldown_days=3, eligibility=company_course(CC.FITNESS), director_brief="The player pauses to reset form before continuing a basic exercise."),
    # 052 training_crossdiscipline_material_switch
    EventDefinition(event_id="training_crossdiscipline_material_switch", category=SCHEDULED, trigger_mode=P, tier=MINOR, interaction_mode=N, base_probability=.15, priority=10, cooldown_days=3, eligibility=company_slot, director_brief="The instructor switches to a different prepared exercise midway."),
    # 053 training_crossdiscipline_extra_run_choice
    EventDefinition(event_id="training_crossdiscipline_extra_run_choice", category=OPPORTUNITY, trigger_mode=L, tier=MINOR, interaction_mode=I, base_probability=.45, priority=20, cooldown_days=5, context_npc_source=ROSTER, context_npc_role=TEACHER, eligibility=all_of(company_slot, teacher_matches_course), director_brief="The selected teacher offers one optional final run.", choices=(choice("do_final_run", "最后再练一遍"), choice("stop_with_class", "按原计划结束这节课"))),
    # 054 training_crossdiscipline_show_first_choice
    EventDefinition(event_id="training_crossdiscipline_show_first_choice", category=OPPORTUNITY, trigger_mode=L, tier=MINOR, interaction_mode=I, base_probability=.40, priority=20, cooldown_days=7, context_npc_source=ROSTER, context_npc_role=TEACHER, eligibility=all_of(company_slot, teacher_matches_course), director_brief="The selected teacher asks for a volunteer to demonstrate the drill.", choices=(choice("volunteer", "主动上去示范", condition_effect(CS.CONFIDENCE_GAIN)), choice("let_another_demonstrate", "让其他练习生来示范"))),
    # 055 training_crossdiscipline_repeat_or_note
    EventDefinition(event_id="training_crossdiscipline_repeat_or_note", category=CONDITIONAL, trigger_mode=L, tier=MINOR, interaction_mode=I, base_probability=.48, priority=20, cooldown_days=4, eligibility=company_slot, director_brief="Only a few minutes remain for individual review.", choices=(choice("repeat_physically", "再完整做一遍"), choice("write_correction_notes", "把需要改的地方记下来"))),
    # 056 training_crossdiscipline_group_offer
    EventDefinition(event_id="training_crossdiscipline_group_offer", category=RELATIONSHIP, trigger_mode=L, tier=MINOR, interaction_mode=I, base_probability=.40, priority=20, cooldown_days=6, context_npc_source=ROSTER, context_npc_role=TRAINEE, eligibility=all_of(company_skill_course, bound_relationship(tension_max=69)), director_brief="The selected trainee offers one shared run before leaving.", choices=(choice("join_shared_run", "加入这次共同练习"), choice("continue_own_review", "继续自己复习"))),
    # 057 training_crossdiscipline_feedback_request
    EventDefinition(event_id="training_crossdiscipline_feedback_request", category=OPPORTUNITY, trigger_mode=L, tier=MINOR, interaction_mode=I, base_probability=.38, priority=20, cooldown_days=7, context_npc_source=ROSTER, context_npc_role=TEACHER, eligibility=all_of(company_slot, teacher_matches_course), director_brief="The selected teacher leaves time for one brief question.", choices=(choice("ask_sticking_point", "问一个自己卡住的问题", condition_effect(CS.STRESS_RELIEF)), choice("keep_question_for_later", "把问题留到以后再问"))),
    # 058 training_crossdiscipline_record_or_repeat
    EventDefinition(event_id="training_crossdiscipline_record_or_repeat", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=I, base_probability=.16, priority=20, cooldown_days=4, eligibility=company_slot, director_brief="One final minute is available for individual review.", choices=(choice("record_reference_clip", "录一段参考视频"), choice("repeat_unrecorded", "不录像，再练一遍"))),
    # 059 training_crossdiscipline_front_or_back
    EventDefinition(event_id="training_crossdiscipline_front_or_back", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=I, base_probability=.13, priority=20, cooldown_days=5, eligibility=company_course(CC.DANCE, CC.STAGE, CC.CAMERA), director_brief="Open practice positions remain for the next run.", choices=(choice("take_visible_position", "选一个更显眼的位置", condition_effect(CS.CONFIDENCE_GAIN)), choice("choose_quieter_position", "选一个不那么显眼的位置", condition_effect(CS.STRESS_RELIEF)))),
    # 060 training_crossdiscipline_break_or_mark
    EventDefinition(event_id="training_crossdiscipline_break_or_mark", category=CONDITIONAL, trigger_mode=P, tier=MINOR, interaction_mode=I, base_probability=.18, priority=20, cooldown_days=3, eligibility=company_slot, director_brief="A short gap remains before the room must be cleared.", choices=(choice("use_gap_to_rest", "利用这点空档休息", condition_effect(CS.STRESS_RELIEF)), choice("mark_sequence", "安静地把动作顺一遍"))),
)
