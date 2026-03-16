import pytest
import httpx
from whoop.write import WhoopWriteAPI
from whoop.models import WorkoutWrite, ExerciseWrite, WorkoutResult, SportTypeInfo
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
    )
    with pytest.raises(WhoopAPIError):
        await api.create_workout(workout)


@pytest.mark.asyncio
async def test_log_workout_with_exercises(mock_api, fake_token):
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
    assert isinstance(result, WorkoutResult)
    assert result.activity_id == 99
    assert result.exercises_linked is True
    assert result.error is None


@pytest.mark.asyncio
async def test_log_workout_no_exercises(mock_api, fake_token):
    mock_api.post("/activities-service/v0/workouts").mock(
        return_value=httpx.Response(200, json={
            "id": 50,
            "sport_id": 233,
            "start": "2026-03-16T18:00:00.000Z",
            "end": "2026-03-16T18:20:00.000Z",
        })
    )
    api = WhoopWriteAPI(token=fake_token)
    workout = WorkoutWrite(
        sport_id=233,
        start="2026-03-16T18:00:00.000Z",
        end="2026-03-16T18:20:00.000Z",
    )
    result = await api.log_workout(workout)
    assert isinstance(result, WorkoutResult)
    assert result.activity_id == 50
    assert result.exercises_linked is False
    assert result.error is None


@pytest.mark.asyncio
async def test_log_workout_empty_exercises(mock_api, fake_token):
    mock_api.post("/activities-service/v0/workouts").mock(
        return_value=httpx.Response(200, json={
            "id": 51,
            "sport_id": 70,
            "start": "2026-03-16T08:00:00.000Z",
            "end": "2026-03-16T08:15:00.000Z",
        })
    )
    api = WhoopWriteAPI(token=fake_token)
    workout = WorkoutWrite(
        sport_id=70,
        start="2026-03-16T08:00:00.000Z",
        end="2026-03-16T08:15:00.000Z",
        exercises=[],
    )
    result = await api.log_workout(workout)
    assert result.activity_id == 51
    assert result.exercises_linked is False


@pytest.mark.asyncio
async def test_log_workout_partial_failure(mock_api, fake_token):
    mock_api.post("/activities-service/v0/workouts").mock(
        return_value=httpx.Response(200, json={
            "id": 60,
            "sport_id": 45,
            "start": "2026-03-16T14:00:00.000Z",
            "end": "2026-03-16T15:00:00.000Z",
        })
    )
    mock_api.post("/weightlifting-service/v2/weightlifting-workout/link-cardio-workout").mock(
        return_value=httpx.Response(500, json={"error": "internal"})
    )
    api = WhoopWriteAPI(token=fake_token)
    workout = WorkoutWrite(
        sport_id=45,
        start="2026-03-16T14:00:00.000Z",
        end="2026-03-16T15:00:00.000Z",
        exercises=[
            ExerciseWrite(name="Bench Press", sets=5, reps=3, weight=235),
        ],
    )
    result = await api.log_workout(workout)
    assert result.activity_id == 60
    assert result.exercises_linked is False
    assert result.error is not None


def test_offset_for_utc():
    api = WhoopWriteAPI(token="fake", timezone="UTC")
    assert api._offset_for("2026-03-16T14:00:00.000Z") == "+0000"


def test_offset_for_la_winter():
    api = WhoopWriteAPI(token="fake", timezone="America/Los_Angeles")
    assert api._offset_for("2026-01-15T14:00:00.000Z") == "-0800"


def test_offset_for_la_summer():
    api = WhoopWriteAPI(token="fake", timezone="America/Los_Angeles")
    assert api._offset_for("2026-07-15T14:00:00.000Z") == "-0700"


def test_offset_for_z_suffix():
    api = WhoopWriteAPI(token="fake", timezone="America/New_York")
    result = api._offset_for("2026-01-15T14:00:00Z")
    assert result == "-0500"


def test_invalid_timezone():
    with pytest.raises(ValueError, match="invalid timezone"):
        WhoopWriteAPI(token="fake", timezone="Not/A/Timezone")


@pytest.mark.asyncio
async def test_get_sport_types(mock_api, fake_token):
    mock_api.get("/activities-service/v2/activity-types").mock(
        return_value=httpx.Response(200, json=[
            {"id": 233, "name": "Sauna"},
            {"id": 45, "name": "Weightlifting"},
        ])
    )
    api = WhoopWriteAPI(token=fake_token)
    result = await api.get_sport_types()
    assert len(result) == 2
    assert isinstance(result[0], SportTypeInfo)
    assert result[0].id == 233
    assert result[0].name == "Sauna"


@pytest.mark.asyncio
async def test_get_sport_types_cached(mock_api, fake_token):
    route = mock_api.get("/activities-service/v2/activity-types").mock(
        return_value=httpx.Response(200, json=[
            {"id": 233, "name": "Sauna"},
        ])
    )
    api = WhoopWriteAPI(token=fake_token)
    await api.get_sport_types()
    await api.get_sport_types()
    assert route.call_count == 1


@pytest.mark.asyncio
async def test_get_sport_types_error(mock_api, fake_token):
    mock_api.get("/activities-service/v2/activity-types").mock(
        return_value=httpx.Response(500, json={"error": "server error"})
    )
    api = WhoopWriteAPI(token=fake_token)
    with pytest.raises(WhoopAPIError):
        await api.get_sport_types()
