import pytest
import httpx
from whoop.read import WhoopReadAPI
from whoop.models import Recovery, Sleep, Workout, Cycle, BodyMeasurement
from whoop.exceptions import WhoopRateLimitError

@pytest.mark.asyncio
async def test_get_recovery(mock_api, fake_token):
    mock_api.get("/developer/v2/recovery").mock(
        return_value=httpx.Response(200, json={
            "records": [{
                "cycle_id": 1,
                "sleep_id": 2,
                "user_id": 3,
                "score": {
                    "recovery_score": 75.0,
                    "resting_heart_rate": 55.0,
                    "hrv_rmssd_milli": 50.2,
                    "spo2_percentage": 98.0,
                    "skin_temp_celsius": 33.0,
                },
                "created_at": "2026-03-16T07:00:00.000Z",
                "updated_at": "2026-03-16T07:00:00.000Z",
            }],
            "next_token": None,
        })
    )
    api = WhoopReadAPI(token=fake_token)
    recoveries = await api.get_recovery()
    assert len(recoveries) == 1
    assert recoveries[0].recovery_score == 75.0

@pytest.mark.asyncio
async def test_get_sleep(mock_api, fake_token):
    mock_api.get("/developer/v2/activity/sleep").mock(
        return_value=httpx.Response(200, json={
            "records": [{
                "id": 1,
                "user_id": 3,
                "score": {
                    "sleep_performance_percentage": 90.0,
                    "sleep_efficiency_percentage": 95.0,
                    "respiratory_rate": 14.5,
                    "stage_summary": {
                        "total_light_sleep_time_milli": 14400000,
                        "total_slow_wave_sleep_time_milli": 7200000,
                        "total_rem_sleep_time_milli": 5400000,
                        "total_awake_time_milli": 1800000,
                        "total_in_bed_time_milli": 28800000,
                    },
                },
                "created_at": "2026-03-16T07:00:00.000Z",
                "updated_at": "2026-03-16T07:00:00.000Z",
            }],
            "next_token": None,
        })
    )
    api = WhoopReadAPI(token=fake_token)
    sleeps = await api.get_sleep()
    assert len(sleeps) == 1
    assert sleeps[0].performance == 90.0

@pytest.mark.asyncio
async def test_rate_limit_handling(mock_api, fake_token):
    mock_api.get("/developer/v2/recovery").mock(
        return_value=httpx.Response(429, headers={"X-RateLimit-Reset": "60"})
    )
    api = WhoopReadAPI(token=fake_token)
    with pytest.raises(WhoopRateLimitError) as exc_info:
        await api.get_recovery()
    assert exc_info.value.retry_after == 60
