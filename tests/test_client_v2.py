import pytest
import httpx
from whoop.client import WhoopClient
from whoop.write_models import (
    ActivityResult, DetailedExercise, ExerciseSet,
    JournalInput, JournalBehavior,
)


@pytest.mark.asyncio
async def test_client_create_activity(mock_api, fake_token):
    mock_api.post("/activities-service/v2/activities").mock(
        return_value=httpx.Response(200, json={
            "id": "uuid-abc",
            "type": "sauna",
            "score_type": "RECOVERY",
            "score_state": "pending",
        })
    )
    client = WhoopClient(token=fake_token)
    result = await client.create_activity("sauna", "2026-03-18T21:00:00Z", "2026-03-18T21:20:00Z")
    assert isinstance(result, ActivityResult)
    assert result.type == "sauna"


@pytest.mark.asyncio
async def test_client_delete_activity(mock_api, fake_token):
    mock_api.delete(
        url__regex=r"/core-details-bff/v1/recovery-details.*",
    ).mock(return_value=httpx.Response(204))
    client = WhoopClient(token=fake_token)
    await client.delete_activity("uuid-abc", is_recovery=True)


@pytest.mark.asyncio
async def test_client_link_exercises_detailed(mock_api, fake_token):
    mock_api.post(
        "/weightlifting-service/v2/weightlifting-workout/link-cardio-workout",
    ).mock(return_value=httpx.Response(200, json={"status": "linked"}))
    client = WhoopClient(token=fake_token)
    exercises = [
        DetailedExercise(
            exercise_id="SQUAT_BARBELL",
            name="Squat - Barbell",
            sets=[ExerciseSet(reps=5, weight=315)],
        ),
    ]
    result = await client.link_exercises_detailed("activity-uuid", exercises)
    assert result["status"] == "linked"


@pytest.mark.asyncio
async def test_client_log_journal(mock_api, fake_token):
    mock_api.put(
        url__regex=r"/journal-service/v2/journals/entries/user/date/.*",
    ).mock(return_value=httpx.Response(204))
    client = WhoopClient(token=fake_token)
    inputs = [JournalInput(behavior_tracker_id=1, answered_yes=True)]
    await client.log_journal("2026-03-18", inputs)


@pytest.mark.asyncio
async def test_client_get_journal_behaviors(mock_api, fake_token):
    mock_api.get(
        url__regex=r"/journal-service/v2/journals/behaviors/user/.*",
    ).mock(return_value=httpx.Response(200, json=[
        {
            "id": 1,
            "title": "Caffeine",
            "internal_name": "caffeine",
            "behavior_type": "BOOLEAN",
            "question_text": "Did you have caffeine?",
        },
    ]))
    client = WhoopClient(token=fake_token)
    result = await client.get_journal_behaviors("2026-03-18")
    assert len(result) == 1
    assert isinstance(result[0], JournalBehavior)


@pytest.mark.asyncio
async def test_client_update_weight(mock_api, fake_token):
    mock_api.get("/profile-service/v1/profile/bff/edit").mock(
        return_value=httpx.Response(200, json={
            "first_name": "Test",
            "weight_kilogram": 80.0,
            "height_meter": 1.80,
        })
    )
    mock_api.put("/profile-service/v1/profile").mock(
        return_value=httpx.Response(200, json=True)
    )
    client = WhoopClient(token=fake_token)
    result = await client.update_weight(85.0)
    assert result is True


@pytest.mark.asyncio
async def test_client_set_alarm(mock_api, fake_token):
    mock_api.put("/smart-alarm-service/v1/smartalarm/preferences").mock(
        return_value=httpx.Response(200, json={
            "enabled": True,
            "upper_time_bound": "07:30:00",
        })
    )
    client = WhoopClient(token=fake_token)
    result = await client.set_alarm("07:30:00")
    assert result["enabled"] is True
