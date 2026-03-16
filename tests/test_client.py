import pytest
import httpx
from whoop.client import WhoopClient
from whoop.models import WorkoutWrite, ExerciseWrite, SportTypeInfo

@pytest.mark.asyncio
async def test_client_read_recovery(mock_api, fake_token):
    mock_api.get("/developer/v1/recovery").mock(
        return_value=httpx.Response(200, json={
            "records": [{
                "cycle_id": 1, "sleep_id": 2, "user_id": 3,
                "score": {
                    "recovery_score": 88.0, "resting_heart_rate": 48.0,
                    "hrv_rmssd_milli": 72.0, "spo2_percentage": 98.0,
                    "skin_temp_celsius": 33.0,
                },
                "created_at": "2026-03-16T07:00:00.000Z",
                "updated_at": "2026-03-16T07:00:00.000Z",
            }],
            "next_token": None,
        })
    )
    client = WhoopClient(token=fake_token)
    recoveries = await client.get_recovery()
    assert recoveries[0].recovery_score == 88.0

@pytest.mark.asyncio
async def test_client_log_workout(mock_api, fake_token):
    mock_api.post("/activities-service/v0/workouts").mock(
        return_value=httpx.Response(200, json={
            "id": 77, "sport_id": 1,
            "start": "2026-03-16T14:00:00.000Z",
            "end": "2026-03-16T15:00:00.000Z",
        })
    )
    mock_api.post("/weightlifting-service/v2/weightlifting-workout/link-cardio-workout").mock(
        return_value=httpx.Response(200, json={"status": "linked"})
    )
    client = WhoopClient(token=fake_token)
    workout = WorkoutWrite(
        sport_id=1,
        start="2026-03-16T14:00:00.000Z",
        end="2026-03-16T15:00:00.000Z",
        exercises=[
            ExerciseWrite(name="Squat", sets=5, reps=5, weight=315),
        ],
    )
    result = await client.log_workout(workout)
    assert result.activity_id == 77
    assert result.exercises_linked is True

@pytest.mark.asyncio
async def test_client_get_sport_types(mock_api, fake_token):
    mock_api.get("/activities-service/v2/activity-types").mock(
        return_value=httpx.Response(200, json=[
            {"id": 233, "name": "Sauna"},
        ])
    )
    client = WhoopClient(token=fake_token)
    types = await client.get_sport_types()
    assert len(types) == 1
    assert isinstance(types[0], SportTypeInfo)
    assert types[0].name == "Sauna"
