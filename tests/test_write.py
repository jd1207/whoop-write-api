import pytest
import httpx
from whoop.write import WhoopWriteAPI
from whoop.models import WorkoutWrite, ExerciseWrite
from whoop.exceptions import WhoopAPIError

@pytest.mark.asyncio
async def test_create_workout(mock_api, fake_token):
    mock_api.post("/activities-service/v0/workouts").mock(
        return_value=httpx.Response(200, json={
            "id": 42,
            "sport_id": 1,
            "start": "2026-03-16T14:00:00.000Z",
            "end": "2026-03-16T15:00:00.000Z",
        })
    )
    api = WhoopWriteAPI(token=fake_token)
    workout = WorkoutWrite(
        sport_id=1,
        start="2026-03-16T14:00:00.000Z",
        end="2026-03-16T15:00:00.000Z",
        exercises=[
            ExerciseWrite(name="Bench Press", sets=5, reps=3, weight=235),
        ],
    )
    result = await api.create_workout(workout)
    assert result["id"] == 42

@pytest.mark.asyncio
async def test_link_exercises(mock_api, fake_token):
    mock_api.post("/weightlifting-service/v2/weightlifting-workout/link-cardio-workout").mock(
        return_value=httpx.Response(200, json={"status": "linked"})
    )
    api = WhoopWriteAPI(token=fake_token)
    exercises = [
        ExerciseWrite(name="Bench Press", sets=5, reps=3, weight=235),
        ExerciseWrite(name="Rows", sets=4, reps=8, weight=135),
    ]
    result = await api.link_exercises(workout_id=42, exercises=exercises)
    assert result["status"] == "linked"

@pytest.mark.asyncio
async def test_create_workout_failure(mock_api, fake_token):
    mock_api.post("/activities-service/v0/workouts").mock(
        return_value=httpx.Response(500, json={"error": "server error"})
    )
    api = WhoopWriteAPI(token=fake_token)
    workout = WorkoutWrite(
        sport_id=1,
        start="2026-03-16T14:00:00.000Z",
        end="2026-03-16T15:00:00.000Z",
        exercises=[],
    )
    with pytest.raises(WhoopAPIError):
        await api.create_workout(workout)

@pytest.mark.asyncio
async def test_log_full_workout(mock_api, fake_token):
    mock_api.post("/activities-service/v0/workouts").mock(
        return_value=httpx.Response(200, json={
            "id": 99,
            "sport_id": 1,
            "start": "2026-03-16T14:00:00.000Z",
            "end": "2026-03-16T15:00:00.000Z",
        })
    )
    mock_api.post("/weightlifting-service/v2/weightlifting-workout/link-cardio-workout").mock(
        return_value=httpx.Response(200, json={"status": "linked"})
    )
    api = WhoopWriteAPI(token=fake_token)
    workout = WorkoutWrite(
        sport_id=1,
        start="2026-03-16T14:00:00.000Z",
        end="2026-03-16T15:00:00.000Z",
        exercises=[
            ExerciseWrite(name="Bench Press", sets=5, reps=3, weight=235),
        ],
    )
    result = await api.log_workout(workout)
    assert result["activity_id"] == 99
    assert result["exercises_linked"] is True
