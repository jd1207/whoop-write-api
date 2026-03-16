# General Activity Logging Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the write API to support logging any Whoop activity type (sauna, ice bath, meditation, etc.) with optional exercise linking, partial failure recovery, and open source readiness.

**Architecture:** Add a `SportType` IntEnum (80+ sports) as a convenience namespace. Make exercises optional on `WorkoutWrite`. Return typed `WorkoutResult` from `log_workout()` with partial failure handling. Compute timezone offsets per-call using `zoneinfo` for DST correctness. Add `get_sport_types()` for dynamic lookups. Ship open source files (CONTRIBUTING, CHANGELOG, py.typed).

**Tech Stack:** Python 3.11+, httpx, zoneinfo (stdlib), pytest + pytest-asyncio + respx

**Spec:** `docs/superpowers/specs/2026-03-16-general-activity-logging-design.md`

---

## Chunk 1: Sport Type Enum

### Task 1: Create SportType IntEnum

**Files:**
- Create: `src/whoop/sport_types.py`
- Create: `tests/test_sport_types.py`

- [ ] **Step 1: Write the test file**

```python
# tests/test_sport_types.py
from whoop.sport_types import SportType


def test_sport_type_values():
    assert SportType.SAUNA == 233
    assert SportType.WEIGHTLIFTING == 45
    assert SportType.ICE_BATH == 88
    assert SportType.MEDITATION == 70
    assert SportType.RUNNING == 0
    assert SportType.GENERAL_ACTIVITY == -1


def test_sport_type_is_int():
    assert isinstance(SportType.SAUNA, int)
    assert SportType.SAUNA + 0 == 233


def test_sport_type_unique_values():
    values = [member.value for member in SportType]
    assert len(values) == len(set(values))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/deck/whoop-write-api && python -m pytest tests/test_sport_types.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'whoop.sport_types'`

- [ ] **Step 3: Write the SportType enum**

```python
# src/whoop/sport_types.py
from enum import IntEnum, unique


@unique
class SportType(IntEnum):
    """known whoop sport IDs - sourced from developer.whoop.com, 2026-03-16"""
    GENERAL_ACTIVITY = -1
    RUNNING = 0
    CYCLING = 1
    BASEBALL = 16
    BASKETBALL = 17
    ROWING = 18
    FENCING = 19
    FIELD_HOCKEY = 20
    FOOTBALL = 21
    GOLF = 22
    ICE_HOCKEY = 24
    LACROSSE = 25
    RUGBY = 27
    SAILING = 28
    SKIING = 29
    SOCCER = 30
    SOFTBALL = 31
    SQUASH = 32
    SWIMMING = 33
    TENNIS = 34
    TRACK_AND_FIELD = 35
    VOLLEYBALL = 36
    WATER_POLO = 37
    WRESTLING = 38
    BOXING = 39
    DANCE = 42
    PILATES = 43
    YOGA = 44
    WEIGHTLIFTING = 45
    CROSS_COUNTRY_SKIING = 47
    FUNCTIONAL_FITNESS = 48
    DUATHLON = 49
    GYMNASTICS = 51
    HIKING = 52
    HORSEBACK_RIDING = 53
    KAYAKING = 55
    MARTIAL_ARTS = 56
    MOUNTAIN_BIKING = 57
    POWERLIFTING = 59
    ROCK_CLIMBING = 60
    PADDLEBOARDING = 61
    TRIATHLON = 62
    WALKING = 63
    SURFING = 64
    ELLIPTICAL = 65
    STAIRMASTER = 66
    MEDITATION = 70
    OTHER = 71
    DIVING = 73
    OPERATIONS_TACTICAL = 74
    OPERATIONS_MEDICAL = 75
    OPERATIONS_FLYING = 76
    OPERATIONS_WATER = 77
    ULTIMATE = 82
    CLIMBER = 83
    JUMPING_ROPE = 84
    AUSTRALIAN_FOOTBALL = 85
    SKATEBOARDING = 86
    COACHING = 87
    ICE_BATH = 88
    COMMUTING = 89
    GAMING = 90
    SNOWBOARDING = 91
    MOTOCROSS = 92
    CADDYING = 93
    OBSTACLE_COURSE_RACING = 94
    MOTOR_RACING = 95
    HIIT = 96
    SPIN = 97
    JIU_JITSU = 98
    MANUAL_LABOR = 99
    CRICKET = 100
    PICKLEBALL = 101
    INLINE_SKATING = 102
    BOX_FITNESS = 103
    SPIKEBALL = 104
    WHEELCHAIR_PUSHING = 105
    PADDLE_TENNIS = 106
    BARRE = 107
    STAGE_PERFORMANCE = 108
    HIGH_STRESS_WORK = 109
    PARKOUR = 110
    GAELIC_FOOTBALL = 111
    HURLING = 112
    CIRCUS_ARTS = 113
    MASSAGE_THERAPY = 121
    STRENGTH_TRAINER = 123
    WATCHING_SPORTS = 125
    ASSAULT_BIKE = 126
    KICKBOXING = 127
    STRETCHING = 128
    TABLE_TENNIS = 230
    BADMINTON = 231
    NETBALL = 232
    SAUNA = 233
    DISC_GOLF = 234
    YARD_WORK = 235
    AIR_COMPRESSION = 236
    PERCUSSIVE_MASSAGE = 237
    PAINTBALL = 238
    ICE_SKATING = 239
    HANDBALL = 240
    F45_TRAINING = 248
    PADEL = 249
    BARRYS = 250
    DEDICATED_PARENTING = 251
    STROLLER_WALKING = 252
    STROLLER_JOGGING = 253
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/deck/whoop-write-api && python -m pytest tests/test_sport_types.py -v`
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/whoop/sport_types.py tests/test_sport_types.py
git commit -m "feat: add SportType IntEnum with all 80+ whoop sport IDs"
```

---

## Chunk 2: Models + Write API (atomic change)

These must land together: making exercises optional in models without updating write.py would crash `log_workout(exercises=None)`.

### Task 2: Update ExerciseWrite with to_dict()

**Files:**
- Modify: `src/whoop/models.py:125-131`
- Modify: `tests/test_write_models.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_write_models.py`:

```python
def test_exercise_write_to_dict():
    ex = ExerciseWrite(name="Bench Press", sets=5, reps=3, weight=235, weight_unit="lbs")
    d = ex.to_dict()
    assert d == {
        "name": "Bench Press",
        "sets": 5,
        "reps": 3,
        "weight": 235,
        "weight_unit": "lbs",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/deck/whoop-write-api && python -m pytest tests/test_write_models.py::test_exercise_write_to_dict -v`
Expected: FAIL with `AttributeError: 'ExerciseWrite' object has no attribute 'to_dict'`

- [ ] **Step 3: Add to_dict() to ExerciseWrite**

In `src/whoop/models.py`, replace lines 125-131:

```python
@dataclass
class ExerciseWrite:
    name: str
    sets: int
    reps: int
    weight: float
    weight_unit: str = "lbs"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "sets": self.sets,
            "reps": self.reps,
            "weight": self.weight,
            "weight_unit": self.weight_unit,
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/deck/whoop-write-api && python -m pytest tests/test_write_models.py -v`
Expected: all tests PASS

### Task 3: Update WorkoutWrite (optional exercises, timezone, to_exercises_payload)

**Files:**
- Modify: `src/whoop/models.py:134-164`
- Modify: `tests/test_write_models.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_write_models.py`:

```python
from whoop.sport_types import SportType


def test_workout_write_no_exercises():
    workout = WorkoutWrite(
        sport_id=SportType.SAUNA,
        start="2026-03-16T18:00:00.000Z",
        end="2026-03-16T18:20:00.000Z",
    )
    assert workout.exercises is None
    payload = workout.to_activity_payload()
    assert payload["sportId"] == 233


def test_workout_write_exercises_payload_none():
    workout = WorkoutWrite(
        sport_id=1,
        start="2026-03-16T14:00:00.000Z",
        end="2026-03-16T15:00:00.000Z",
    )
    assert workout.to_exercises_payload() == []


def test_workout_write_exercises_payload_empty():
    workout = WorkoutWrite(
        sport_id=1,
        start="2026-03-16T14:00:00.000Z",
        end="2026-03-16T15:00:00.000Z",
        exercises=[],
    )
    assert workout.to_exercises_payload() == []


def test_workout_write_timezone_offset():
    workout = WorkoutWrite(
        sport_id=1,
        start="2026-03-16T14:00:00.000Z",
        end="2026-03-16T15:00:00.000Z",
    )
    payload = workout.to_activity_payload(timezone_offset="-0700")
    assert payload["timezoneOffset"] == "-0700"


def test_workout_write_exercises_payload_uses_to_dict():
    workout = WorkoutWrite(
        sport_id=1,
        start="2026-03-16T14:00:00.000Z",
        end="2026-03-16T15:00:00.000Z",
        exercises=[
            ExerciseWrite(name="Bench Press", sets=5, reps=3, weight=235),
        ],
    )
    payload = workout.to_exercises_payload()
    assert payload[0] == ExerciseWrite(name="Bench Press", sets=5, reps=3, weight=235).to_dict()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/deck/whoop-write-api && python -m pytest tests/test_write_models.py -v`
Expected: new tests FAIL (exercises is required, to_activity_payload takes no args)

- [ ] **Step 3: Update WorkoutWrite in models.py**

Replace `WorkoutWrite` class (lines 134-164) in `src/whoop/models.py`:

```python
@dataclass
class WorkoutWrite:
    sport_id: int
    start: str
    end: str
    exercises: list[ExerciseWrite] | None = None

    def to_activity_payload(self, timezone_offset: str = "+0000") -> dict:
        return {
            "gpsEnabled": False,
            "timezoneOffset": timezone_offset,
            "sportId": self.sport_id,
            "source": "user",
            "during": {
                "lower": self.start,
                "upper": self.end,
                "bounds": "[)",
            },
        }

    def to_exercises_payload(self) -> list[dict]:
        if not self.exercises:
            return []
        return [ex.to_dict() for ex in self.exercises]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/deck/whoop-write-api && python -m pytest tests/test_write_models.py -v`
Expected: all tests PASS

### Task 4: Add SportTypeInfo and WorkoutResult models

**Files:**
- Modify: `src/whoop/models.py` (append after WorkoutWrite)
- Modify: `tests/test_models.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_models.py`:

```python
from whoop.models import SportTypeInfo, WorkoutResult


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/deck/whoop-write-api && python -m pytest tests/test_models.py -v`
Expected: FAIL with `ImportError: cannot import name 'SportTypeInfo'`

- [ ] **Step 3: Add models to models.py**

Append to `src/whoop/models.py` after the `WorkoutWrite` class:

```python
@dataclass
class SportTypeInfo:
    id: int
    name: str

    @classmethod
    def from_api(cls, data: dict) -> SportTypeInfo:
        return cls(id=data["id"], name=data["name"])


@dataclass
class WorkoutResult:
    activity_id: int
    exercises_linked: bool
    error: str | None = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/deck/whoop-write-api && python -m pytest tests/test_models.py -v`
Expected: all tests PASS

### Task 5: Update write.py (timezone, optional exercises, partial failure, _get, get_sport_types)

**Files:**
- Modify: `src/whoop/write.py` (full rewrite — 72 lines currently, will be ~95)
- Modify: `tests/test_write.py`

- [ ] **Step 1: Write failing tests for timezone and optional exercises**

Replace entire `tests/test_write.py` with:

```python
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
    route = mock_api.post("/activities-service/v0/workouts").mock(
        return_value=httpx.Response(200, json={
            "id": 50,
            "sport_id": 233,
            "start": "2026-03-16T18:00:00.000Z",
            "end": "2026-03-16T18:20:00.000Z",
        })
    )
    link_route = mock_api.post(
        "/weightlifting-service/v2/weightlifting-workout/link-cardio-workout"
    ).mock(return_value=httpx.Response(200, json={"status": "linked"}))

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
    assert link_route.call_count == 0


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
    link_route = mock_api.post(
        "/weightlifting-service/v2/weightlifting-workout/link-cardio-workout"
    ).mock(return_value=httpx.Response(200, json={"status": "linked"}))

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
    assert link_route.call_count == 0


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
    # january = PST = UTC-8
    assert api._offset_for("2026-01-15T14:00:00.000Z") == "-0800"


def test_offset_for_la_summer():
    api = WhoopWriteAPI(token="fake", timezone="America/Los_Angeles")
    # july = PDT = UTC-7
    assert api._offset_for("2026-07-15T14:00:00.000Z") == "-0700"


def test_offset_for_z_suffix():
    api = WhoopWriteAPI(token="fake", timezone="America/New_York")
    # january = EST = UTC-5
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/deck/whoop-write-api && python -m pytest tests/test_write.py -v`
Expected: multiple failures (WorkoutResult not returned, _offset_for doesn't exist, etc.)

- [ ] **Step 3: Rewrite write.py**

Replace entire `src/whoop/write.py`:

```python
from __future__ import annotations
from datetime import datetime
from zoneinfo import ZoneInfo
import httpx
from whoop.models import WorkoutWrite, ExerciseWrite, WorkoutResult, SportTypeInfo
from whoop.exceptions import WhoopAPIError

BASE_URL = "https://api.prod.whoop.com"

WRITE_HEADERS_EXTRA = {
    "x-whoop-device-platform": "API",
    "locale": "en_US",
}


class WhoopWriteAPI:
    def __init__(self, token: str, timezone: str = "America/Los_Angeles"):
        self.token = token
        self.timezone = timezone
        self._sport_types_cache: list[SportTypeInfo] | None = None
        try:
            ZoneInfo(timezone)
        except KeyError:
            raise ValueError(f"invalid timezone: {timezone}")

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "x-whoop-time-zone": self.timezone,
            **WRITE_HEADERS_EXTRA,
        }

    def _offset_for(self, iso_timestamp: str) -> str:
        """compute UTC offset string for a given ISO 8601 timestamp"""
        dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        local = dt.astimezone(ZoneInfo(self.timezone))
        offset = local.utcoffset()
        total_seconds = int(offset.total_seconds())
        sign = "+" if total_seconds >= 0 else "-"
        hours, remainder = divmod(abs(total_seconds), 3600)
        minutes = remainder // 60
        return f"{sign}{hours:02d}{minutes:02d}"

    async def _post(self, path: str, json: dict) -> dict:
        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            resp = await client.post(path, headers=self._headers, json=json)
        if resp.status_code not in (200, 201):
            raise WhoopAPIError(
                f"POST {path} failed: {resp.text}",
                status_code=resp.status_code,
                response_body=resp.text,
            )
        return resp.json()

    async def _get(self, path: str) -> dict | list:
        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            resp = await client.get(path, headers=self._headers)
        if resp.status_code != 200:
            raise WhoopAPIError(
                f"GET {path} failed: {resp.text}",
                status_code=resp.status_code,
                response_body=resp.text,
            )
        return resp.json()

    async def create_workout(self, workout: WorkoutWrite) -> dict:
        offset = self._offset_for(workout.start)
        return await self._post(
            "/activities-service/v0/workouts",
            workout.to_activity_payload(timezone_offset=offset),
        )

    async def link_exercises(self, workout_id: int, exercises: list[ExerciseWrite]) -> dict:
        payload = {
            "cardio_workout_id": workout_id,
            "exercises": [ex.to_dict() for ex in exercises],
        }
        return await self._post(
            "/weightlifting-service/v2/weightlifting-workout/link-cardio-workout",
            payload,
        )

    async def log_workout(self, workout: WorkoutWrite) -> WorkoutResult:
        activity = await self.create_workout(workout)
        activity_id = activity["id"]

        if not workout.exercises:
            return WorkoutResult(activity_id=activity_id, exercises_linked=False)

        try:
            exercises_result = await self.link_exercises(activity_id, workout.exercises)
            linked = exercises_result.get("status") == "linked"
            return WorkoutResult(activity_id=activity_id, exercises_linked=linked)
        except WhoopAPIError as exc:
            return WorkoutResult(
                activity_id=activity_id,
                exercises_linked=False,
                error=str(exc),
            )

    async def get_sport_types(self) -> list[SportTypeInfo]:
        if self._sport_types_cache is not None:
            return self._sport_types_cache
        data = await self._get("/activities-service/v2/activity-types")
        self._sport_types_cache = [SportTypeInfo.from_api(item) for item in data]
        return self._sport_types_cache
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/deck/whoop-write-api && python -m pytest tests/test_write.py tests/test_write_models.py tests/test_models.py -v`
Expected: all tests PASS

- [ ] **Step 5: Run full test suite to check for regressions**

Run: `cd /home/deck/whoop-write-api && python -m pytest -v`
Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/whoop/models.py src/whoop/write.py tests/test_write.py tests/test_write_models.py tests/test_models.py
git commit -m "feat: general activity logging with optional exercises and partial failure handling

- ExerciseWrite.to_dict() as single serialization source
- WorkoutWrite.exercises now optional (None or [])
- WorkoutResult typed return from log_workout()
- Partial failure: returns activity_id even if exercise linking fails
- Per-call timezone offset via zoneinfo (DST-correct)
- _get() helper and get_sport_types() with caching
- SportTypeInfo and WorkoutResult models"
```

---

## Chunk 3: Client, Exports, Auth

### Task 6: Update WhoopClient

**Files:**
- Modify: `src/whoop/client.py`
- Modify: `tests/test_client.py`

- [ ] **Step 1: Write failing tests**

Replace entire `tests/test_client.py`:

```python
import pytest
import httpx
from whoop.client import WhoopClient
from whoop.models import WorkoutWrite, ExerciseWrite, WorkoutResult, SportTypeInfo


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
    assert isinstance(result, WorkoutResult)
    assert result.activity_id == 77


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
```

- [ ] **Step 2: Run tests to verify new tests fail**

Run: `cd /home/deck/whoop-write-api && python -m pytest tests/test_client.py -v`
Expected: `test_client_log_workout` fails (returns dict not WorkoutResult), `test_client_get_sport_types` fails (no method)

- [ ] **Step 3: Update client.py**

Replace `src/whoop/client.py`:

```python
from __future__ import annotations
from whoop.auth import WhoopAuth
from whoop.read import WhoopReadAPI
from whoop.write import WhoopWriteAPI
from whoop.models import (
    Recovery, Sleep, Workout, Cycle, BodyMeasurement,
    WorkoutWrite, WorkoutResult, SportTypeInfo,
)


class WhoopClient:
    def __init__(
        self,
        token: str | None = None,
        auth: WhoopAuth | None = None,
        timezone: str = "America/Los_Angeles",
    ):
        if token:
            self._token = token
        elif auth and auth.access_token:
            self._token = auth.access_token
        else:
            raise ValueError("provide either token or authenticated WhoopAuth")
        self._read = WhoopReadAPI(token=self._token)
        self._write = WhoopWriteAPI(token=self._token, timezone=timezone)
        self._auth = auth

    async def get_recovery(self, start: str | None = None, end: str | None = None) -> list[Recovery]:
        return await self._read.get_recovery(start, end)

    async def get_sleep(self, start: str | None = None, end: str | None = None) -> list[Sleep]:
        return await self._read.get_sleep(start, end)

    async def get_workouts(self, start: str | None = None, end: str | None = None) -> list[Workout]:
        return await self._read.get_workouts(start, end)

    async def get_cycles(self, start: str | None = None, end: str | None = None) -> list[Cycle]:
        return await self._read.get_cycles(start, end)

    async def get_body_measurement(self) -> BodyMeasurement:
        return await self._read.get_body_measurement()

    async def log_workout(self, workout: WorkoutWrite) -> WorkoutResult:
        return await self._write.log_workout(workout)

    async def get_sport_types(self) -> list[SportTypeInfo]:
        return await self._write.get_sport_types()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/deck/whoop-write-api && python -m pytest tests/test_client.py -v`
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/whoop/client.py tests/test_client.py
git commit -m "feat: expose get_sport_types() and WorkoutResult on WhoopClient"
```

### Task 7: Update exports and add __version__

**Files:**
- Modify: `src/whoop/__init__.py`

- [ ] **Step 1: Update __init__.py**

Replace `src/whoop/__init__.py`:

```python
from importlib.metadata import version, PackageNotFoundError

from whoop.client import WhoopClient
from whoop.models import (
    Recovery, Sleep, Workout, Cycle, BodyMeasurement,
    WorkoutWrite, ExerciseWrite, SportTypeInfo, WorkoutResult,
)
from whoop.sport_types import SportType
from whoop.exceptions import WhoopAuthError, WhoopAPIError, WhoopRateLimitError

try:
    __version__ = version("whoop-write-api")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"

__all__ = [
    "WhoopClient",
    "Recovery", "Sleep", "Workout", "Cycle", "BodyMeasurement",
    "WorkoutWrite", "ExerciseWrite", "SportTypeInfo", "WorkoutResult",
    "SportType",
    "WhoopAuthError", "WhoopAPIError", "WhoopRateLimitError",
    "__version__",
]
```

- [ ] **Step 2: Verify imports work**

Run: `cd /home/deck/whoop-write-api && python -c "from whoop import SportType, SportTypeInfo, WorkoutResult, __version__; print(f'SportType.SAUNA={SportType.SAUNA}'); print(f'version={__version__}')"`
Expected: `SportType.SAUNA=233` and version output

- [ ] **Step 3: Run full test suite**

Run: `cd /home/deck/whoop-write-api && python -m pytest -v`
Expected: all tests PASS

- [ ] **Step 4: Commit**

```bash
git add src/whoop/__init__.py
git commit -m "feat: export SportType, SportTypeInfo, WorkoutResult, __version__"
```

### Task 8: Parameterize client_id in auth

**Files:**
- Modify: `src/whoop/auth.py:68`

- [ ] **Step 1: Update login_password signature**

In `src/whoop/auth.py`, change line 68 from:

```python
    async def login_password(self, username: str, password: str) -> str:
```

to:

```python
    async def login_password(self, username: str, password: str, client_id: str = "whoop-recruiting-prod") -> str:
```

And change line 76 from:

```python
                    "client_id": "whoop-recruiting-prod",
```

to:

```python
                    "client_id": client_id,
```

- [ ] **Step 2: Run auth tests to verify no regression**

Run: `cd /home/deck/whoop-write-api && python -m pytest tests/test_auth.py -v`
Expected: all tests PASS (default value preserves existing behavior)

- [ ] **Step 3: Commit**

```bash
git add src/whoop/auth.py
git commit -m "feat: parameterize client_id in login_password()"
```

---

## Chunk 4: Open Source Files, README, SpotMe Guide

### Task 9: Add py.typed marker

**Files:**
- Create: `src/whoop/py.typed`

- [ ] **Step 1: Create empty marker file**

```bash
touch src/whoop/py.typed
```

- [ ] **Step 2: Commit**

```bash
git add src/whoop/py.typed
git commit -m "feat: add py.typed marker for type checker support"
```

### Task 10: Update pyproject.toml

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Update pyproject.toml**

Replace `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "whoop-write-api"
version = "0.2.0"
description = "Python client for Whoop API — official read + unofficial write endpoints"
readme = "README.md"
license = "MIT"
requires-python = ">=3.11"
authors = [{ name = "jd1207" }]
keywords = ["whoop", "fitness", "api", "workout", "health"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Typing :: Typed",
    "Framework :: AsyncIO",
]
dependencies = [
    "httpx>=0.27",
]

[project.urls]
Homepage = "https://github.com/jd1207/whoop-write-api"
Issues = "https://github.com/jd1207/whoop-write-api/issues"

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "respx>=0.21",
    "ruff>=0.3",
]

[tool.hatch.build.targets.wheel]
packages = ["src/whoop"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
target-version = "py311"
line-length = 100
```

- [ ] **Step 2: Verify build still works**

Run: `cd /home/deck/whoop-write-api && pip install -e ".[dev]" 2>&1 | tail -3`
Expected: successful install

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: bump to v0.2.0, add classifiers, remove python-dotenv"
```

### Task 11: Fix LICENSE copyright

**Files:**
- Modify: `LICENSE`

- [ ] **Step 1: Update copyright line**

In `LICENSE`, change line 3 from `Copyright (c) 2026` to `Copyright (c) 2026 jd1207`.

- [ ] **Step 2: Commit**

```bash
git add LICENSE
git commit -m "chore: add copyright holder to LICENSE"
```

### Task 12: Add CONTRIBUTING.md and CHANGELOG.md

**Files:**
- Create: `CONTRIBUTING.md`
- Create: `CHANGELOG.md`

- [ ] **Step 1: Write CONTRIBUTING.md**

```markdown
# Contributing

## Setup

```
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

## Tests

```
pytest
```

## Lint

```
ruff check .
ruff format --check .
```

## Code Style

- All lowercase comments
- No emojis in code or logs
- One class per file where practical
- 200-line max per file

## Unofficial Endpoints

The write API uses reverse-engineered endpoints. If you discover new endpoints
via mitmproxy/Charles Proxy, document them in ENDPOINTS.md with the payload
format and any required headers.

## Versioning

This project follows semver. v0.x releases may include breaking changes.
The public API is everything exported from `whoop.__init__`.
```

- [ ] **Step 2: Write CHANGELOG.md**

```markdown
# Changelog

## v0.2.0 (unreleased)

- Add `SportType` IntEnum with all 80+ Whoop activity types
- Make exercises optional on `WorkoutWrite` for non-weightlifting activities
- Add `WorkoutResult` typed return from `log_workout()`
- Handle partial failures in `log_workout()` (return activity_id even if exercise linking fails)
- Add `get_sport_types()` for dynamic sport type lookup
- Add `SportTypeInfo` model
- Fix hardcoded timezone offset in workout payload
- Parameterize client_id in password auth
- Add py.typed marker
- Add CONTRIBUTING.md
- Remove python-dotenv from runtime dependencies

## v0.1.0 (2026-03-16)

- Initial release
- Official read API (recovery, sleep, workouts, cycles, body measurements)
- Unofficial write API (create workout, link exercises)
- OAuth2 and legacy password authentication
```

- [ ] **Step 3: Commit**

```bash
git add CONTRIBUTING.md CHANGELOG.md
git commit -m "docs: add CONTRIBUTING.md and CHANGELOG.md"
```

### Task 13: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README**

Key changes to make:
1. Update the "Why?" section to mention any activity type, not just weightlifting
2. Update quick start example to use `SportType` and `result.activity_id` (not `result['activity_id']`)
3. Add sauna/ice bath example
4. Add `get_sport_types()` to the Write API section
5. Add Roadmap section at the bottom
6. Strengthen the disclaimer about unofficial endpoints and account risk

Full replacement for `README.md`:

```markdown
# whoop-write-api

Python client for the Whoop API — both official read endpoints and reverse-engineered write endpoints.

## Why?

The official Whoop API is read-only. This library adds write support so you can programmatically log any activity — weightlifting with full exercise details, sauna sessions, ice baths, meditation, or any of Whoop's 80+ activity types.

> **Disclaimer:** Write endpoints are reverse-engineered from Whoop's internal API and may break without notice. Using these endpoints may violate Whoop's Terms of Service and could result in account action. Read endpoints use the official documented API. This project is not affiliated with Whoop.

## Install

```bash
pip install whoop-write-api
```

## Quick Start

```python
import asyncio
from whoop import WhoopClient, WorkoutWrite, ExerciseWrite, SportType

async def main():
    client = WhoopClient(token="your-bearer-token")

    # read recovery
    recoveries = await client.get_recovery()
    print(f"Recovery: {recoveries[0].recovery_score}%")

    # log a strength workout
    workout = WorkoutWrite(
        sport_id=SportType.WEIGHTLIFTING,
        start="2026-03-16T14:00:00.000Z",
        end="2026-03-16T15:00:00.000Z",
        exercises=[
            ExerciseWrite(name="Bench Press", sets=5, reps=3, weight=235),
            ExerciseWrite(name="Incline DB Press", sets=3, reps=10, weight=60),
        ],
    )
    result = await client.log_workout(workout)
    print(f"Logged workout {result.activity_id}")

    # log a sauna session (no exercises needed)
    sauna = WorkoutWrite(
        sport_id=SportType.SAUNA,
        start="2026-03-16T18:00:00.000Z",
        end="2026-03-16T18:20:00.000Z",
    )
    result = await client.log_workout(sauna)
    print(f"Logged sauna {result.activity_id}")

asyncio.run(main())
```

## Authentication

### OAuth2 (recommended)

Register an app at [developer.whoop.com](https://developer.whoop.com) to get client credentials.

```python
from whoop.auth import WhoopAuth

auth = WhoopAuth(client_id="your-id", client_secret="your-secret")
token = await auth.exchange_code("auth-code", "http://localhost/callback")
client = WhoopClient(auth=auth)
```

### Legacy password auth

```python
auth = WhoopAuth()
token = await auth.login_password("email@example.com", "password")
client = WhoopClient(auth=auth)
```

## Read API

All official Whoop API endpoints:

- `client.get_recovery(start?, end?)` — recovery scores, HRV, RHR
- `client.get_sleep(start?, end?)` — sleep stages, performance, efficiency
- `client.get_workouts(start?, end?)` — workout strain, HR data
- `client.get_cycles(start?, end?)` — daily strain cycles
- `client.get_body_measurement()` — height, weight, max HR

## Write API (unofficial)

- `client.log_workout(WorkoutWrite)` — log any activity type, optionally with exercises
- `client.get_sport_types()` — fetch all available sport types from Whoop

### Sport Types

Use `SportType` for IDE autocomplete or pass raw ints:

```python
from whoop import SportType

SportType.SAUNA        # 233
SportType.ICE_BATH     # 88
SportType.MEDITATION   # 70
SportType.WEIGHTLIFTING  # 45
SportType.RUNNING      # 0
# ... 80+ more
```

## Roadmap

### v0.3.0 - Write API Expansion

The following features require endpoint discovery via mitmproxy/Charles Proxy
capture from the Whoop mobile app:

- [ ] Journal entries (daily caffeine, alcohol, supplements, stress ratings)
- [ ] Body measurement updates (weight, height)
- [ ] Workout notes and annotations
- [ ] Workout deletion
- [ ] `async with` context manager for connection pooling
- [ ] Synchronous client wrapper

See ENDPOINTS.md for instructions on capturing new endpoints.

## License

MIT
```

- [ ] **Step 2: Run full test suite one final time**

Run: `cd /home/deck/whoop-write-api && python -m pytest -v`
Expected: all tests PASS

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: update README with general activity examples and roadmap"
```

### Task 14: Write SpotMe integration guide

**Files:**
- Create: `/home/deck/spotme/docs/whoop-write-api-v0.2.md` (separate repo)

- [ ] **Step 1: Check spotme repo exists**

Run: `ls /home/deck/spotme/docs/`

- [ ] **Step 2: Write the integration guide**

Create `/home/deck/spotme/docs/whoop-write-api-v0.2.md`:

```markdown
# whoop-write-api v0.2.0 — SpotMe Integration Guide

## What Changed

### SportType enum
Use `SportType.WEIGHTLIFTING` instead of `sport_id=45`. All 80+ Whoop activity types available:

```python
from whoop import SportType

SportType.WEIGHTLIFTING  # 45
SportType.SAUNA          # 233
SportType.ICE_BATH       # 88
SportType.MEDITATION     # 70
SportType.STRETCHING     # 128
```

`sport_id` still accepts raw `int` — existing code passing `sport_id=45` works unchanged.

### Exercises are optional
`WorkoutWrite.exercises` now defaults to `None`. For non-weightlifting activities (sauna, meditation, etc.), omit exercises entirely:

```python
sauna = WorkoutWrite(
    sport_id=SportType.SAUNA,
    start="2026-03-16T18:00:00.000Z",
    end="2026-03-16T18:20:00.000Z",
)
result = await client.log_workout(sauna)
```

### WorkoutResult replaces dict
`log_workout()` now returns a `WorkoutResult` dataclass instead of a dict.

Before (v0.1):
```python
result = await client.log_workout(workout)
activity_id = result["activity_id"]
```

After (v0.2):
```python
result = await client.log_workout(workout)
activity_id = result.activity_id
linked = result.exercises_linked
error = result.error  # None on success, error string on partial failure
```

### Partial failure handling
If the workout is created but exercise linking fails, `log_workout()` now returns the `activity_id` instead of raising. Check `result.error`:

```python
result = await client.log_workout(workout)
if result.error:
    # workout exists on whoop but exercises weren't linked
    queue_retry(result.activity_id, workout.exercises)
```

### Dynamic sport type lookup
```python
types = await client.get_sport_types()
for t in types:
    print(f"{t.name}: {t.id}")
```

## whoop_service.py Changes Needed

1. Replace `result["activity_id"]` with `result.activity_id`
2. Handle `result.error` for the sync queue (partial failures no longer raise)
3. Optionally use `SportType` enum for readability

## Coming in v0.3

- Journal entries (caffeine, alcohol, supplements, stress)
- Body measurement updates (weight)
- Workout notes/annotations
- These require mitmproxy endpoint capture first
```

- [ ] **Step 3: Commit in spotme repo**

```bash
cd /home/deck/spotme && git add docs/whoop-write-api-v0.2.md && git commit -m "docs: add whoop-write-api v0.2 integration guide"
```
