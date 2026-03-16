from whoop.models import Recovery, Sleep, Workout, Cycle, BodyMeasurement, SportTypeInfo, WorkoutResult

def test_recovery_from_api():
    data = {
        "cycle_id": 123,
        "sleep_id": 456,
        "user_id": 789,
        "score": {
            "recovery_score": 82.0,
            "resting_heart_rate": 52.0,
            "hrv_rmssd_milli": 65.3,
            "spo2_percentage": 97.0,
            "skin_temp_celsius": 33.5,
        },
        "created_at": "2026-03-16T07:00:00.000Z",
        "updated_at": "2026-03-16T07:00:00.000Z",
    }
    recovery = Recovery.from_api(data)
    assert recovery.recovery_score == 82.0
    assert recovery.hrv == 65.3
    assert recovery.resting_hr == 52.0

def test_sleep_from_api():
    data = {
        "id": 1,
        "user_id": 789,
        "score": {
            "sleep_performance_percentage": 85.0,
            "sleep_efficiency_percentage": 92.0,
            "respiratory_rate": 15.2,
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
    }
    sleep = Sleep.from_api(data)
    assert sleep.performance == 85.0
    assert sleep.efficiency == 92.0
    assert sleep.total_in_bed_hours == 8.0

def test_sport_type_info_from_api():
    data = {"id": 233, "name": "Sauna"}
    info = SportTypeInfo.from_api(data)
    assert info.id == 233
    assert info.name == "Sauna"

def test_workout_result_success():
    result = WorkoutResult(activity_id=42, exercises_linked=True)
    assert result.activity_id == 42
    assert result.exercises_linked is True
    assert result.error is None

def test_workout_result_partial_failure():
    result = WorkoutResult(activity_id=42, exercises_linked=False, error="link failed")
    assert result.activity_id == 42
    assert result.exercises_linked is False
    assert result.error == "link failed"
