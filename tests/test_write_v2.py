import pytest
import httpx
from whoop.write import WhoopWriteAPI, RECOVERY_TYPES
from whoop.write_models import (
    ActivityResult, DetailedExercise, ExerciseSet,
    JournalInput, JournalBehavior,
)
from whoop.exceptions import WhoopAPIError


@pytest.mark.asyncio
async def test_create_activity(mock_api, fake_token):
    mock_api.post("/activities-service/v2/activities").mock(
        return_value=httpx.Response(200, json={
            "id": "68f455f4-abcd-1234-5678-abcdef012345",
            "type": "sauna",
            "score_type": "RECOVERY",
            "score_state": "pending",
            "translated_type": "Dry Sauna",
        })
    )
    api = WhoopWriteAPI(token=fake_token, timezone="America/New_York")
    result = await api.create_activity(
        activity_type="sauna",
        start="2026-03-18T21:02:54.336Z",
        end="2026-03-18T21:03:11.048Z",
    )
    assert isinstance(result, ActivityResult)
    assert result.id == "68f455f4-abcd-1234-5678-abcdef012345"
    assert result.type == "sauna"
    assert result.score_type == "RECOVERY"
    assert result.score_state == "pending"


@pytest.mark.asyncio
async def test_create_activity_payload_format(mock_api, fake_token):
    route = mock_api.post("/activities-service/v2/activities").mock(
        return_value=httpx.Response(200, json={
            "id": "abc123",
            "type": "running",
            "score_type": "CARDIO",
            "score_state": "pending",
        })
    )
    api = WhoopWriteAPI(token=fake_token, timezone="America/New_York")
    await api.create_activity(
        activity_type="running",
        start="2026-03-18T14:00:00.000Z",
        end="2026-03-18T15:00:00.000Z",
    )
    request = route.calls.last.request
    import json
    body = json.loads(request.content)
    assert body["source"] == "user"
    assert body["type"] == "running"
    assert body["timezone"] == "America/New_York"
    assert "2026-03-18T14:00:00.000Z" in body["during"]
    assert "2026-03-18T15:00:00.000Z" in body["during"]


@pytest.mark.asyncio
async def test_delete_activity_cardio(mock_api, fake_token):
    route = mock_api.delete(
        url__regex=r"/core-details-bff/v1/cardio-details.*",
    ).mock(return_value=httpx.Response(204))
    api = WhoopWriteAPI(token=fake_token)
    await api.delete_activity("abc-123", is_recovery=False)
    assert route.call_count == 1


@pytest.mark.asyncio
async def test_delete_activity_recovery(mock_api, fake_token):
    route = mock_api.delete(
        url__regex=r"/core-details-bff/v1/recovery-details.*",
    ).mock(return_value=httpx.Response(204))
    api = WhoopWriteAPI(token=fake_token)
    await api.delete_activity("abc-456", is_recovery=True)
    assert route.call_count == 1


@pytest.mark.asyncio
async def test_delete_activity_failure(mock_api, fake_token):
    mock_api.delete(
        url__regex=r"/core-details-bff/v1/cardio-details.*",
    ).mock(return_value=httpx.Response(404, json={"error": "not found"}))
    api = WhoopWriteAPI(token=fake_token)
    with pytest.raises(WhoopAPIError):
        await api.delete_activity("bad-id")


@pytest.mark.asyncio
async def test_link_exercises_detailed(mock_api, fake_token):
    route = mock_api.post(
        "/weightlifting-service/v2/weightlifting-workout/link-cardio-workout",
    ).mock(return_value=httpx.Response(200, json={"status": "linked"}))
    api = WhoopWriteAPI(token=fake_token)
    exercises = [
        DetailedExercise(
            exercise_id="BENCHPRESS_BARBELL",
            name="Bench Press - Barbell",
            sets=[
                ExerciseSet(reps=5, weight=225),
                ExerciseSet(reps=5, weight=225),
            ],
        ),
        DetailedExercise(
            exercise_id="PLANK",
            name="Plank",
            exercise_type="STRENGTH",
            volume_format="TIME",
            sets=[
                ExerciseSet(reps=0, weight=0, time_seconds=60),
            ],
        ),
    ]
    result = await api.link_exercises_detailed("activity-uuid", exercises)
    assert result["status"] == "linked"
    import json
    body = json.loads(route.calls.last.request.content)
    assert body["cardio_workout_id"] == "activity-uuid"
    groups = body["template"]["workout_groups"]
    assert len(groups) == 1
    workout_exercises = groups[0]["workout_exercises"]
    assert len(workout_exercises) == 2
    assert workout_exercises[0]["exercise_details"]["exercise_id"] == "BENCHPRESS_BARBELL"
    assert len(workout_exercises[0]["sets"]) == 2
    assert workout_exercises[1]["sets"][0]["time_in_seconds"] == 60


@pytest.mark.asyncio
async def test_log_journal(mock_api, fake_token):
    route = mock_api.put(
        url__regex=r"/journal-service/v2/journals/entries/user/date/.*",
    ).mock(return_value=httpx.Response(204))
    api = WhoopWriteAPI(token=fake_token)
    inputs = [
        JournalInput(behavior_tracker_id=1, answered_yes=False),
        JournalInput(behavior_tracker_id=2, answered_yes=True, magnitude_input_value=2),
    ]
    await api.log_journal("2026-03-18", inputs, notes="felt good")
    assert route.call_count == 1
    import json
    body = json.loads(route.calls.last.request.content)
    assert len(body["tracker_inputs"]) == 2
    assert body["notes"] == "felt good"
    assert body["tracker_inputs"][1]["magnitude_input_value"] == 2
    assert body["tracker_inputs"][1]["magnitude_input_label"] == "2"


@pytest.mark.asyncio
async def test_log_journal_no_notes(mock_api, fake_token):
    mock_api.put(
        url__regex=r"/journal-service/v2/journals/entries/user/date/.*",
    ).mock(return_value=httpx.Response(204))
    api = WhoopWriteAPI(token=fake_token)
    inputs = [JournalInput(behavior_tracker_id=1, answered_yes=True)]
    await api.log_journal("2026-03-18", inputs)


@pytest.mark.asyncio
async def test_get_journal_behaviors(mock_api, fake_token):
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
        {
            "id": 2,
            "title": "Stress",
            "internal_name": "stress",
            "behavior_type": "MAGNITUDE",
            "question_text": "How stressed were you?",
        },
    ]))
    api = WhoopWriteAPI(token=fake_token)
    result = await api.get_journal_behaviors("2026-03-18")
    assert len(result) == 2
    assert isinstance(result[0], JournalBehavior)
    assert result[0].title == "Caffeine"
    assert result[1].behavior_type == "MAGNITUDE"


@pytest.mark.asyncio
async def test_update_weight(mock_api, fake_token):
    mock_api.get("/profile-service/v1/profile/bff/edit").mock(
        return_value=httpx.Response(200, json={
            "first_name": "Test",
            "last_name": "User",
            "weight_kilogram": 80.0,
            "height_meter": 1.80,
        })
    )
    mock_api.put("/profile-service/v1/profile").mock(
        return_value=httpx.Response(200, json=True)
    )
    api = WhoopWriteAPI(token=fake_token)
    result = await api.update_weight(85.0)
    assert result is True


@pytest.mark.asyncio
async def test_update_weight_preserves_profile(mock_api, fake_token):
    mock_api.get("/profile-service/v1/profile/bff/edit").mock(
        return_value=httpx.Response(200, json={
            "first_name": "Test",
            "last_name": "User",
            "weight_kilogram": 80.0,
            "height_meter": 1.80,
        })
    )
    route = mock_api.put("/profile-service/v1/profile").mock(
        return_value=httpx.Response(200, json=True)
    )
    api = WhoopWriteAPI(token=fake_token)
    await api.update_weight(85.0)
    import json
    body = json.loads(route.calls.last.request.content)
    assert body["weight_kilogram"] == 85.0
    assert body["first_name"] == "Test"
    assert body["height_meter"] == 1.80


@pytest.mark.asyncio
async def test_set_alarm(mock_api, fake_token):
    mock_api.put("/smart-alarm-service/v1/smartalarm/preferences").mock(
        return_value=httpx.Response(200, json={
            "enabled": True,
            "goal": "EXACT_TIME_OPTIMIZE_SLEEP",
            "upper_time_bound": "08:00:00",
            "time_zone_offset": "-0400",
            "schedule_enabled": False,
        })
    )
    api = WhoopWriteAPI(token=fake_token)
    result = await api.set_alarm("08:00:00", enabled=True, timezone_offset="-0400")
    assert result["enabled"] is True
    assert result["upper_time_bound"] == "08:00:00"


@pytest.mark.asyncio
async def test_set_alarm_disabled(mock_api, fake_token):
    route = mock_api.put("/smart-alarm-service/v1/smartalarm/preferences").mock(
        return_value=httpx.Response(200, json={"enabled": False})
    )
    api = WhoopWriteAPI(token=fake_token)
    result = await api.set_alarm("07:30:00", enabled=False)
    import json
    body = json.loads(route.calls.last.request.content)
    assert body["enabled"] is False


def test_recovery_types_set():
    assert "sauna" in RECOVERY_TYPES
    assert "stretching" in RECOVERY_TYPES
    assert "meditation" in RECOVERY_TYPES
    assert "ice_bath" in RECOVERY_TYPES
    assert "yoga" in RECOVERY_TYPES
    assert "running" not in RECOVERY_TYPES
