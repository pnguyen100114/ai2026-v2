from __future__ import annotations

from backend.learning import (
    ERROR_TAGS,
    concept_state,
    grade_answer,
    parse_generated_question,
    reference_time_seconds,
    target_difficulty,
)

CONCEPT = 'toan8.bien-doi-dai-so'


def question(*, correct='A', difficulty=2, errors=None, tags=None):
    options = ['A', 'B', 'C']
    return {
        'subject': 'Toán',
        'concept_id': CONCEPT,
        'concept': 'Biến đổi đại số',
        'difficulty': difficulty,
        'answer': correct,
        'hint': 'Xét từng bước biến đổi.',
        'explanation': 'Kiểm tra lại quy tắc biến đổi.',
        'misconceptions': errors or {},
        'error_tags': tags or {},
    }


def grade(profile, answer='A', **kwargs):
    return grade_answer(question(), answer, profile, **kwargs)


def test_one_unassisted_correct_answer_counts_but_keeps_low_confidence():
    result = grade({}, time_spent_seconds=25)
    assert result['is_correct']
    assert result['assessment']['confidence'] == 'low'
    assert 0.35 < result['mastery'] < 0.60


def test_correct_after_hints_is_recognized_with_lower_independence_signal():
    without_hint = grade({})
    with_hints = grade({}, hints_used=3)
    assert with_hints['is_correct']
    assert with_hints['mastery'] < without_hint['mastery']
    assert with_hints['mastery'] > 0.35


def test_correct_streak_after_hint_does_not_raise_difficulty():
    profile = {'concepts': {CONCEPT: {'mastery': 0.72, 'attempts': 5, 'streak': 2}}}
    result = grade_answer(question(difficulty=3), 'A', profile, hints_used=1)
    assert result['next_action'] == 'independent_practice'
    assert result['next_difficulty'] <= 3
    unaided = grade_answer(question(difficulty=3), 'A', profile)
    assert unaided['next_action'] == 'progression'
    assert unaided['next_difficulty'] == 4


def test_quiz_prompt_reports_how_often_hints_were_needed():
    from backend.learning import build_quiz_prompt
    profile = {}
    for hints in (1, 1, 0):
        grade(profile, hints_used=hints)
    state = concept_state(profile, CONCEPT)
    prompt = build_quiz_prompt(subject='Toán', grade=8, lesson='', topic='Biến đổi đại số', difficulty=2,
                               state=state, goal='', context_text='', recent_questions=[])
    assert 'phải xem gợi ý ở 2/3 câu gần nhất' in prompt
    assert 'bước trung gian' in prompt


def test_one_wrong_answer_does_not_crash_mastery_and_does_not_invent_error_tag():
    result = grade({}, answer='B')
    assert result['mastery'] > 0.20
    assert result['error_tags'] == []
    assert result['assessment']['recurring_errors'] == []


def test_repeated_verified_sign_errors_prioritize_targeted_practice():
    profile = {}
    q = question(errors={'B': 'đổi dấu sai'}, tags={'B': 'sign_error'})
    first = grade_answer(q, 'B', profile)
    second = grade_answer(q, 'B', profile)
    assert first['assessment']['recurring_errors'] == []
    assert second['assessment']['recurring_errors'] == ['sign_error']
    assert second['next_action'] == 'targeted_practice'
    assert second['recommendation']['action']['error_tag'] == 'sign_error'
    assert ERROR_TAGS['Toán']['sign_error'].lower() in second['recommendation']['reason']


def test_distinct_error_tags_are_kept_and_prioritized_by_repetition():
    profile = {}
    q = question(
        errors={'B': 'sai dấu', 'C': 'nhầm công thức'},
        tags={'B': 'sign_error', 'C': 'formula_confusion'},
    )
    grade_answer(q, 'B', profile)
    grade_answer(q, 'C', profile)
    grade_answer(q, 'C', profile)
    state = profile['concepts'][CONCEPT]
    assert 'formula_confusion' in concept_state(profile, CONCEPT)['priority_error_tags']
    assert state['error_counts']['sign_error'] < state['error_counts']['formula_confusion']


def test_success_on_harder_questions_increases_mastery_and_recommended_level():
    profile = {'concepts': {CONCEPT: {'mastery': 0.72, 'attempts': 5, 'streak': 2}}}
    results = [
        grade_answer(question(difficulty=4), 'A', profile)
        for _ in range(4)
    ]
    assert all(result['is_correct'] for result in results)
    assert results[-1]['mastery'] > 0.72
    assert results[-1]['next_difficulty'] >= 4


def test_unusually_fast_correct_answer_is_low_weight_and_not_used_as_time_reference():
    profile = {}
    result = grade_answer(
        question(), 'A', profile, time_spent_seconds=1, expected_time_seconds=30,
    )
    evidence = profile['concepts'][CONCEPT]['evidence'][-1]
    assert result['is_correct']
    assert not result['time_reliable']
    assert evidence['weight'] == 0.35
    assert reference_time_seconds(profile, CONCEPT, 2) is None


def test_long_correct_time_is_not_penalized():
    result = grade_answer(
        question(), 'A', {}, time_spent_seconds=300, expected_time_seconds=30,
    )
    assert result['time_reliable']
    assert result['mastery'] > 0.35


def test_missing_zero_negative_and_out_of_range_times_are_not_used():
    for value in (None, 0, -4, 7201):
        profile = {}
        result = grade_answer(question(), 'A', profile, time_spent_seconds=value)
        assert result['time_spent_seconds'] is None
        assert result['time_reliable']
        assert profile['concepts'][CONCEPT]['evidence'][-1]['time_spent_seconds'] is None


def test_three_valid_same_difficulty_attempts_establish_a_personal_time_reference():
    profile = {}
    for seconds in (20, 31, 40):
        grade_answer(question(), 'A', profile, time_spent_seconds=seconds)
    assert reference_time_seconds(profile, CONCEPT, 2) == 31


def test_old_error_priority_decays_after_repeated_success():
    profile = {}
    q = question(errors={'B': 'đổi dấu sai'}, tags={'B': 'sign_error'})
    grade_answer(q, 'B', profile)
    grade_answer(q, 'B', profile)
    assert concept_state(profile, CONCEPT)['priority_error_tags'] == ['sign_error']
    grade_answer(q, 'A', profile)
    assert concept_state(profile, CONCEPT)['priority_error_tags'] == ['sign_error']
    for _ in range(8):
        grade_answer(q, 'A', profile)
    assert concept_state(profile, CONCEPT)['priority_error_tags'] == []


def test_unknown_or_wrong_subject_error_tags_are_discarded():
    parsed = parse_generated_question(
        '{"question":"Q?","options":["A","B","C"],"answer":"A",'
        '"error_tags":{"B":"sign_error","C":"invented_tag"}}',
        subject='Ngữ văn', concept_id='ngu-van8.doc-hieu', concept='Đọc hiểu', difficulty=2,
    )
    assert parsed['error_tags'] == {}


def test_malformed_old_profile_and_hints_are_safely_bounded():
    profile = {'concepts': {CONCEPT: {'mastery': 'bad', 'attempts': -5, 'evidence': 'bad'}}}
    result = grade_answer(question(), 'A', profile, hints_used=99, time_spent_seconds=15)
    state = profile['concepts'][CONCEPT]
    assert state['mastery'] <= 1.0
    assert state['attempts'] == 1
    assert state['evidence'][-1]['hints_used'] == 3
    assert target_difficulty(2.0) == 5
    assert target_difficulty(-1.0) == 1
