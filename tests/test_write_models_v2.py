from whoop.write_models import (
    ExerciseSet, DetailedExercise, ActivityResult,
    JournalInput, JournalBehavior, ExerciseWrite,
)


def test_exercise_set_to_dict():
    s = ExerciseSet(reps=5, weight=225)
    d = s.to_dict()
    assert d == {"number_of_reps": 5, "weight": 225}
    assert "time_in_seconds" not in d


def test_exercise_set_timed():
    s = ExerciseSet(reps=0, weight=0, time_seconds=60)
    d = s.to_dict()
    assert d["time_in_seconds"] == 60
    assert d["number_of_reps"] == 0


def test_detailed_exercise_to_dict():
    ex = DetailedExercise(
        exercise_id="BENCHPRESS_BARBELL",
        name="Bench Press - Barbell",
        sets=[
            ExerciseSet(reps=5, weight=225),
            ExerciseSet(reps=3, weight=245),
        ],
    )
    d = ex.to_dict()
    assert d["exercise_details"]["exercise_id"] == "BENCHPRESS_BARBELL"
    assert d["exercise_details"]["name"] == "Bench Press - Barbell"
    assert d["exercise_details"]["exercise_type"] == "STRENGTH"
    assert d["exercise_details"]["volume_input_format"] == "REPS"
    assert len(d["sets"]) == 2
    assert d["sets"][0]["number_of_reps"] == 5
    assert d["sets"][1]["weight"] == 245


def test_activity_result_from_api():
    data = {
        "id": "68f455f4-abcd",
        "type": "sauna",
        "score_type": "RECOVERY",
        "score_state": "pending",
    }
    result = ActivityResult.from_api(data)
    assert result.id == "68f455f4-abcd"
    assert result.type == "sauna"
    assert result.score_type == "RECOVERY"


def test_journal_input_boolean():
    inp = JournalInput(behavior_tracker_id=1, answered_yes=False)
    d = inp.to_dict()
    assert d == {"behavior_tracker_id": 1, "answered_yes": False}
    assert "magnitude_input_value" not in d


def test_journal_input_with_magnitude():
    inp = JournalInput(behavior_tracker_id=2, answered_yes=True, magnitude_input_value=3)
    d = inp.to_dict()
    assert d["magnitude_input_value"] == 3
    assert d["magnitude_input_label"] == "3"
    assert d["answered_yes"] is True


def test_journal_behavior_from_api():
    data = {
        "id": 5,
        "title": "Caffeine",
        "internal_name": "caffeine",
        "behavior_type": "BOOLEAN",
        "question_text": "Did you have caffeine?",
    }
    b = JournalBehavior.from_api(data)
    assert b.id == 5
    assert b.title == "Caffeine"
    assert b.internal_name == "caffeine"


def test_exercise_write_to_detailed_dict():
    ex = ExerciseWrite(
        name="Bench Press",
        sets=3,
        reps=5,
        weight=225,
        exercise_id="BENCHPRESS_BARBELL",
    )
    d = ex.to_detailed_dict()
    assert d["exercise_details"]["exercise_id"] == "BENCHPRESS_BARBELL"
    assert len(d["sets"]) == 3
    assert d["sets"][0]["number_of_reps"] == 5
    assert d["sets"][0]["weight"] == 225


def test_exercise_write_to_detailed_dict_auto_id():
    ex = ExerciseWrite(name="Bench Press", sets=2, reps=5, weight=135)
    d = ex.to_detailed_dict()
    assert d["exercise_details"]["exercise_id"] == "BENCH_PRESS"


def test_exercise_write_backward_compat():
    ex = ExerciseWrite(name="Bench Press", sets=5, reps=3, weight=235, weight_unit="lbs")
    d = ex.to_dict()
    assert d == {
        "name": "Bench Press",
        "sets": 5,
        "reps": 3,
        "weight": 235,
        "weight_unit": "lbs",
    }
