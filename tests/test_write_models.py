from whoop.models import WorkoutWrite, ExerciseWrite

def test_exercise_write():
    ex = ExerciseWrite(name="Bench Press", sets=5, reps=3, weight=235, weight_unit="lbs")
    assert ex.name == "Bench Press"
    assert ex.weight_unit == "lbs"

def test_workout_write_activity_payload():
    workout = WorkoutWrite(
        sport_id=1,
        start="2026-03-16T14:00:00.000Z",
        end="2026-03-16T15:00:00.000Z",
        exercises=[
            ExerciseWrite(name="Bench Press", sets=5, reps=3, weight=235),
        ],
    )
    payload = workout.to_activity_payload()
    assert payload["sportId"] == 1
    assert payload["during"]["lower"] == "2026-03-16T14:00:00.000Z"
    assert payload["during"]["upper"] == "2026-03-16T15:00:00.000Z"

def test_workout_write_exercises_payload():
    workout = WorkoutWrite(
        sport_id=1,
        start="2026-03-16T14:00:00.000Z",
        end="2026-03-16T15:00:00.000Z",
        exercises=[
            ExerciseWrite(name="Bench Press", sets=5, reps=3, weight=235),
            ExerciseWrite(name="Rows", sets=4, reps=8, weight=135),
        ],
    )
    payload = workout.to_exercises_payload()
    assert len(payload) == 2
    assert payload[0]["name"] == "Bench Press"
