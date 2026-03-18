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

The read and write APIs use **different auth systems**. Which one you need depends on what you're building.

### Developer OAuth2 — read API only

Register an app at [developer.whoop.com](https://developer.whoop.com). This gives you a `client_id` and `client_secret` scoped to official read endpoints (`/developer/v2/...`).

```python
from whoop.auth import WhoopAuth

auth = WhoopAuth(client_id="your-id", client_secret="your-secret")
token = await auth.exchange_code("auth-code", "http://localhost/callback")
client = WhoopClient(auth=auth)
```

**Works with:** `get_recovery()`, `get_sleep()`, `get_workouts()`, `get_cycles()`, `get_body_measurement()`

**Does NOT work with:** `log_workout()`, journal, weight updates, activity deletion, or any other write endpoint. The developer OAuth token only has access to official read endpoints.

### Cognito auth — read + write APIs

The write API uses the same auth system as the Whoop mobile app (AWS Cognito). Tokens from this flow have access to all internal endpoints including activity creation, exercise linking, journal, and profile updates.

To get a Cognito token, you need to either:

1. **Capture it via mitmproxy** from the Whoop app (see ENDPOINTS.md)
2. **Use the Cognito auth flow directly** with the mobile app's client ID

```python
client = WhoopClient(token="cognito-bearer-token")

# now both read AND write work
recoveries = await client.get_recovery()
result = await client.log_workout(workout)
```

**Works with:** everything — all read endpoints, activity creation, exercise linking, journal entries, weight updates, activity deletion.

### Which do I need?

| Use case | Auth type |
|----------|-----------|
| Read recovery, sleep, strain | Developer OAuth2 |
| Log workouts / activities | Cognito |
| Log journal entries | Cognito |
| Update weight | Cognito |
| Delete activities | Cognito |
| Read + write (full integration) | Cognito |

### Legacy password auth (deprecated)

Whoop has shut down the legacy password endpoint (`api-7.whoop.com`). This method emits a `DeprecationWarning` and will likely fail with a 404.

```python
auth = WhoopAuth()
token = await auth.login_password("email@example.com", "password")  # deprecated
```

## Read API

All official Whoop API endpoints:

- `client.get_recovery(start?, end?)` — recovery scores, HRV, RHR
- `client.get_sleep(start?, end?)` — sleep stages, performance, efficiency
- `client.get_workouts(start?, end?)` — workout strain, HR data
- `client.get_cycles(start?, end?)` — daily strain cycles
- `client.get_body_measurement()` — height, weight, max HR

## Write API (unofficial)

Requires Cognito auth. See [Authentication](#authentication) above.

### Activities

```python
from whoop import WhoopClient

client = WhoopClient(token="cognito-token")

# create any activity using string type names
result = await client.create_activity("sauna", start="2026-03-18T18:00:00.000Z", end="2026-03-18T18:20:00.000Z")
print(result.id)  # UUID string

# delete an activity
await client.delete_activity(result.id, is_recovery=True)  # sauna is a recovery type

# log a workout with exercises (legacy v0 endpoint)
result = await client.log_workout(workout)
```

Activity types: `sauna`, `ice_bath`, `meditation`, `yoga`, `stretching`, `weightlifting`, `running`, `cycling`, `hiking`, `swimming`, `walking`, and more.

Recovery types (sauna, stretching, meditation, ice_bath, yoga) use a different delete endpoint — pass `is_recovery=True`.

### Strength Training with Exercises

```python
from whoop import DetailedExercise, ExerciseSet

exercises = [
    DetailedExercise(
        exercise_id="BENCHPRESS_BARBELL",
        name="Bench Press - Barbell",
        sets=[
            ExerciseSet(reps=5, weight=225),
            ExerciseSet(reps=5, weight=225),
            ExerciseSet(reps=3, weight=245),
        ],
    ),
    DetailedExercise(
        exercise_id="FRONTPLANKELBOW",
        name="Front Plank",
        sets=[ExerciseSet(time_seconds=60), ExerciseSet(time_seconds=60)],
    ),
]

# create the activity first, then link exercises
activity = await client.create_activity("weightlifting", start=start, end=end)
result = await client.link_exercises_detailed(activity.id, exercises)
```

Common exercise IDs: `BENCHPRESS_BARBELL`, `SQUAT_BARBELL`, `DEADLIFT_BARBELL`, `OVERHEADPRESS_BARBELL`, `PULLUP`, `PUSHUP`, `FRONTPLANKELBOW`. Pattern is `EXERCISENAME_EQUIPMENT`.

### Exercise Library

Fetch the complete Whoop exercise catalog (310 exercises) with search and filtering:

```python
catalog = await client.get_exercises()

# search by name
bench_exercises = catalog.search("bench press")

# filter by equipment, muscle group, or movement pattern
barbell_chest = catalog.filter(equipment="BARBELL", muscle_group="CHEST")

# look up by exact ID
ex = catalog.find_by_id("BENCHPRESS_BARBELL")
print(f"{ex.name} — {ex.instructions[0]}")
```

### Journal

```python
from whoop import JournalInput

# log daily behaviors
await client.log_journal("2026-03-18", [
    JournalInput(behavior_tracker_id=1, answered_yes=False),           # no alcohol
    JournalInput(behavior_tracker_id=2, answered_yes=True,
                 magnitude_input_value=2),                             # 2 caffeine servings
    JournalInput(behavior_tracker_id=6, answered_yes=False),           # no late meal
], notes="felt good today")

# get available journal trackers
behaviors = await client.get_journal_behaviors("2026-03-18")
for b in behaviors:
    print(f"{b.id}: {b.title} ({b.internal_name})")
```

Known tracker IDs: 1=Alcohol, 2=Caffeine, 6=Late Meal, 28=Screentime, 89=Protein.

### Weight

```python
# update weight (fetches current profile, updates weight, preserves other fields)
await client.update_weight(115.0)  # kg
```

### Smart Alarm

```python
result = await client.set_alarm("08:00:00", enabled=True, timezone_offset="-0400")
```

### Sport Types

Use `SportType` for IDE autocomplete or pass raw ints:

```python
from whoop import SportType

SportType.SAUNA          # 233
SportType.ICE_BATH       # 88
SportType.MEDITATION     # 70
SportType.WEIGHTLIFTING  # 45
SportType.RUNNING        # 0
# ... 80+ more
```

## Roadmap

### Future

- [ ] `async with` context manager for connection pooling
- [ ] Synchronous client wrapper
- [ ] Cognito auth flow (programmatic login without mitmproxy)

See ENDPOINTS.md for the full endpoint reference.

## License

MIT
