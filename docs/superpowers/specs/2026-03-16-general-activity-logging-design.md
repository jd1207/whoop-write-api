# General Activity Logging & Open Source Readiness

**Date:** 2026-03-16
**Status:** Draft
**Version:** v0.2.0

## Problem

The write API only supports weightlifting workouts. It requires exercises on every workout, uses raw `sport_id` integers with no mapping, and `log_workout()` crashes if exercise linking fails after the workout is already created. The library also lacks open source essentials (CONTRIBUTING.md, CHANGELOG.md, py.typed, proper pyproject.toml metadata).

## Goals

1. Support logging any Whoop activity type (sauna, ice bath, meditation, running, etc.)
2. Provide a `SportType` enum for all 80+ Whoop sport IDs with IDE autocomplete
3. Make exercise linking optional (skip for non-weightlifting activities)
4. Handle partial failures gracefully (return activity_id even if exercise linking fails)
5. Ship open source hygiene files for eventual PyPI distribution
6. Create a SpotMe integration guide (in the SpotMe repo) so the SpotMe agent can leverage this update

## Non-Goals

- Journal write support (needs mitmproxy endpoint capture first)
- Body measurement write support (needs mitmproxy endpoint capture first)
- Workout notes/annotations (needs mitmproxy endpoint capture first)
- Workout deletion (needs mitmproxy endpoint capture first)
- `async with` context manager / connection pooling (v0.3+)
- Sync client wrapper (v0.3+)
- `datetime` objects for start/end (v0.3+)
- CI / GitHub Actions (separate task)
- Docstrings on all public methods (separate task)

## Design

### 1. Sport Type Enum

**New file: `src/whoop/sport_types.py`**

```python
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

**Design decisions:**
- `IntEnum` so `SportType.SAUNA == 233` is `True` and it passes directly as an int
- `@unique` prevents accidental duplicate values
- `sport_id` stays typed as `int` everywhere in models and methods — SportType is a convenience namespace, not a type constraint. Unknown sport IDs pass through without crashing.
- `GENERAL_ACTIVITY = -1` — this is a real Whoop API sport ID (documented at developer.whoop.com), not a library sentinel. Renamed from `ACTIVITY` for clarity since every sport type is technically an activity.

### 2. Model Changes

**File: `src/whoop/models.py`**

#### WorkoutWrite (modified)

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
        return [
            {
                "name": ex.name,
                "sets": ex.sets,
                "reps": ex.reps,
                "weight": ex.weight,
                "weight_unit": ex.weight_unit,
            }
            for ex in self.exercises
        ]
```

Changes:
- `exercises` defaults to `None`. Both `None` and `[]` are treated as "no exercises" — both skip exercise linking in `log_workout()`.
- `to_activity_payload()` accepts `timezone_offset` parameter instead of hardcoding `"+0000"`
- `to_exercises_payload()` guards against `None` exercises

#### ExerciseWrite (modified)

Add `to_dict()` as the single source of truth for exercise serialization:

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

Both `to_exercises_payload()` on `WorkoutWrite` and `link_exercises()` on `WhoopWriteAPI` use `ex.to_dict()` instead of rebuilding the dict inline. This eliminates the duplicate serialization that currently exists between `models.py` and `write.py`.

`to_exercises_payload()` becomes:

```python
def to_exercises_payload(self) -> list[dict]:
    if not self.exercises:
        return []
    return [ex.to_dict() for ex in self.exercises]
```

#### SportTypeInfo (new)

```python
@dataclass
class SportTypeInfo:
    id: int
    name: str

    @classmethod
    def from_api(cls, data: dict) -> SportTypeInfo:
        return cls(id=data["id"], name=data["name"])
```

For dynamic sport type lookup from `/activities-service/v2/activity-types`.

#### WorkoutResult (new)

```python
@dataclass
class WorkoutResult:
    activity_id: int
    exercises_linked: bool
    error: str | None = None
```

Typed return from `log_workout()` instead of raw dict.

### 3. Write API Changes

**File: `src/whoop/write.py`**

#### log_workout() (modified)

```python
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
```

Changes:
- Returns `WorkoutResult` instead of `dict`
- Skips exercise linking when `exercises` is `None` or empty
- Catches exercise linking failures and returns `activity_id` + error (partial failure recovery)

#### create_workout() (modified)

Pass timezone offset computed from the workout's start timestamp:

```python
async def create_workout(self, workout: WorkoutWrite) -> dict:
    offset = self._offset_for(workout.start)
    return await self._post(
        "/activities-service/v0/workouts",
        workout.to_activity_payload(timezone_offset=offset),
    )
```

#### Timezone offset computation (new)

The offset is computed **per-call** from the workout's start timestamp, not cached at init. This correctly handles DST transitions (e.g., "America/Los_Angeles" is -0800 in winter, -0700 in summer).

```python
from datetime import datetime
from zoneinfo import ZoneInfo

class WhoopWriteAPI:
    def __init__(self, token: str, timezone: str = "America/Los_Angeles"):
        self.token = token
        self.timezone = timezone
        self._sport_types_cache: list[SportTypeInfo] | None = None
        # validate timezone at init - fail fast on bad names
        try:
            ZoneInfo(timezone)
        except KeyError:
            raise ValueError(f"invalid timezone: {timezone}")

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
```

For a workout spanning a DST transition, the offset is based on the start time (Whoop's `timezoneOffset` is a single value, not a range).

#### link_exercises() (modified)

Uses `ExerciseWrite.to_dict()` for serialization (single source of truth):

```python
async def link_exercises(self, workout_id: int, exercises: list[ExerciseWrite]) -> dict:
    payload = {
        "cardio_workout_id": workout_id,
        "exercises": [ex.to_dict() for ex in exercises],
    }
    return await self._post(
        "/weightlifting-service/v2/weightlifting-workout/link-cardio-workout",
        payload,
    )
```

`log_workout()` calls `self.link_exercises(activity_id, workout.exercises)` directly. `to_exercises_payload()` stays on `WorkoutWrite` for consumers who want to inspect the payload before sending — both use `ex.to_dict()` so there's no duplication.

#### _get() (new helper)

Add a `_get` method to `WhoopWriteAPI` mirroring the pattern in `WhoopReadAPI`, so `get_sport_types()` uses standardized HTTP handling instead of one-off client creation:

```python
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
```

#### get_sport_types() (new)

```python
async def get_sport_types(self) -> list[SportTypeInfo]:
    if self._sport_types_cache is not None:
        return self._sport_types_cache

    data = await self._get("/activities-service/v2/activity-types")
    self._sport_types_cache = [SportTypeInfo.from_api(item) for item in data]
    return self._sport_types_cache
```

- Cached per client instance (sport types rarely change — cache is intentionally never invalidated for v0.2.0)
- Returns typed `SportTypeInfo` list, consistent with other read methods
- Uses new `_get` helper for standardized error handling

### 4. Client Changes

**File: `src/whoop/client.py`**

Add passthrough:

```python
async def get_sport_types(self) -> list[SportTypeInfo]:
    return await self._write.get_sport_types()
```

### 5. Exports

**File: `src/whoop/__init__.py`**

Add to exports:
- `SportType` (from `sport_types`)
- `SportTypeInfo` (from `models`)
- `WorkoutResult` (from `models`)
- `__version__` via `importlib.metadata.version("whoop-write-api")` — single source of truth from `pyproject.toml`, no hardcoded version string to keep in sync

### 6. Auth Change

**File: `src/whoop/auth.py`**

Parameterize the hardcoded client_id in `login_password()`:

```python
async def login_password(
    self, username: str, password: str, client_id: str = "whoop-recruiting-prod"
) -> str:
```

Note: parameter stays named `username` (not renamed to `email`) to avoid breaking callers using keyword arguments. Default `client_id` preserved for backwards compat, but users can override.

### 7. Open Source Files

#### CONTRIBUTING.md (new)

```markdown
# Contributing

## Setup

    python -m venv venv
    source venv/bin/activate
    pip install -e ".[dev]"

## Tests

    pytest

## Lint

    ruff check .
    ruff format --check .

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

#### CHANGELOG.md (new)

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

#### py.typed (new)

Empty file at `src/whoop/py.typed`.

### 8. pyproject.toml Changes

- Remove `python-dotenv` from `dependencies`
- Add classifiers (Alpha, MIT, Python 3.11+, AsyncIO, Typed)
- Add `authors`, `keywords`, `urls`
- Add `[tool.ruff]` section with target-version and line-length
- Bump version to `0.2.0`

### 9. README Changes

Add usage example for non-weightlifting activities:

```python
from whoop import WhoopClient, WorkoutWrite, SportType

client = WhoopClient(token="your-token")

# log a sauna session (no exercises needed)
sauna = WorkoutWrite(
    sport_id=SportType.SAUNA,
    start="2026-03-16T18:00:00.000Z",
    end="2026-03-16T18:20:00.000Z",
)
result = await client.log_workout(sauna)
print(result.activity_id)
```

Add roadmap section:

```markdown
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
```

### 10. SpotMe Integration Guide

**File: `/home/deck/spotme/docs/whoop-write-api-v0.2.md`** (in SpotMe repo, not this repo)

Contents will cover:
- `SportType` enum is available — use `SportType.WEIGHTLIFTING` instead of `sport_id=45`
- `exercises` is now optional on `WorkoutWrite` — can log any activity
- `log_workout()` returns `WorkoutResult` dataclass instead of dict
  - `result.activity_id` (always present)
  - `result.exercises_linked` (bool)
  - `result.error` (str or None — present on partial failure)
- `get_sport_types()` available for dynamic lookup
- Backwards compat: existing SpotMe code passing `sport_id=int` still works
- Update `whoop_service.py` to handle `WorkoutResult` instead of dict
- Future: journal, notes, body measurements coming in v0.3

### 11. LICENSE Fix

Add copyright holder name to the LICENSE file.

## Testing Strategy

### New tests needed

1. **sport_types tests** (`tests/test_sport_types.py`):
   - All enum members have unique values
   - Key sport IDs match expected values (SAUNA=233, WEIGHTLIFTING=45, etc.)
   - IntEnum int compatibility (`SportType.SAUNA == 233`)
   - `SportType` used as `sport_id` in `WorkoutWrite` works seamlessly

2. **model tests** (`tests/test_models.py` and `tests/test_write_models.py`):
   - `WorkoutWrite` with `exercises=None` produces correct activity payload
   - `WorkoutWrite` with `exercises=[]` produces correct activity payload
   - `to_exercises_payload()` returns `[]` when exercises is `None`
   - `to_exercises_payload()` returns `[]` when exercises is `[]`
   - `to_activity_payload(timezone_offset="-0700")` produces `"timezoneOffset": "-0700"` in payload
   - `ExerciseWrite.to_dict()` produces correct dict
   - `SportTypeInfo.from_api()` parses correctly
   - `WorkoutResult` fields accessible

3. **write API tests** (`tests/test_write.py`):
   - `log_workout()` with `exercises=None` skips link call (assert link endpoint mock NOT called), returns `WorkoutResult`
   - `log_workout()` with `exercises=[]` skips link call, returns `WorkoutResult`
   - `log_workout()` with exercises calls link, returns `WorkoutResult`
   - `log_workout()` partial failure (link raises `WhoopAPIError`) returns `activity_id` + error string
   - `_offset_for()` returns correct offset for known timezone + timestamp
   - `_offset_for()` handles DST correctly (winter vs summer timestamp for same timezone)
   - `_offset_for()` handles `Z` suffix timestamps
   - `__init__` raises `ValueError` for invalid timezone name
   - `get_sport_types()` fetches and returns `list[SportTypeInfo]`
   - `get_sport_types()` returns cached result on second call (assert HTTP called once)
   - `get_sport_types()` handles API errors

4. **client tests** (`tests/test_client.py`):
   - `get_sport_types()` passthrough works

### Existing tests to update

- `test_write.py`: update `log_workout` tests for `WorkoutResult` return type (`.activity_id` not `["activity_id"]`)
- `test_write_models.py`: update for optional exercises, add `ExerciseWrite.to_dict()` tests
- `test_client.py`: update for `WorkoutResult` return type
- `test_models.py`: add `SportTypeInfo` and `WorkoutResult` tests

## Implementation Order

Safe order that avoids broken intermediate states:

1. `src/whoop/sport_types.py` (new, no dependencies)
2. `src/whoop/models.py` (add `ExerciseWrite.to_dict()`, `SportTypeInfo`, `WorkoutResult`, modify `WorkoutWrite`) **AND** `src/whoop/write.py` (modify `log_workout`, `create_workout`, `link_exercises`, add `_get`, `_offset_for`, `get_sport_types`) — **these must land together** since making `exercises` optional in models without updating write.py would crash `log_workout(exercises=None)`
3. `tests/test_sport_types.py` + `tests/test_write_models.py` + `tests/test_write.py` + `tests/test_models.py` updates — verify everything works
4. `src/whoop/client.py` (add `get_sport_types` passthrough)
5. `tests/test_client.py` updates
6. `src/whoop/__init__.py` (add exports + `__version__`)
7. `src/whoop/auth.py` (parameterize `client_id` — independent)
8. `src/whoop/py.typed` (empty marker — independent)
9. `pyproject.toml`, `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `LICENSE` (non-code, safe last)
10. `/home/deck/spotme/docs/whoop-write-api-v0.2.md` (separate repo, after everything else)

## File Changes Summary

| File | Action | Lines (est.) |
|------|--------|-------------|
| `src/whoop/sport_types.py` | new | ~100 |
| `src/whoop/models.py` | edit | ~30 changed |
| `src/whoop/write.py` | edit | ~40 changed |
| `src/whoop/client.py` | edit | ~5 added |
| `src/whoop/__init__.py` | edit | ~5 changed |
| `src/whoop/auth.py` | edit | ~3 changed |
| `src/whoop/py.typed` | new | 0 (empty) |
| `README.md` | edit | ~40 added |
| `CONTRIBUTING.md` | new | ~40 |
| `CHANGELOG.md` | new | ~25 |
| `ENDPOINTS.md` | no change | - |
| `LICENSE` | edit | ~1 changed |
| `pyproject.toml` | edit | ~20 changed |
| `tests/test_sport_types.py` | new | ~30 |
| `tests/test_write.py` | edit | ~30 changed |
| `tests/test_write_models.py` | edit | ~20 changed |
| `tests/test_client.py` | edit | ~10 changed |
| `tests/test_models.py` | edit | ~10 added |
| `/home/deck/spotme/docs/whoop-write-api-v0.2.md` | new (spotme repo) | ~50 |
