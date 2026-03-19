# whoop-write-api

Unofficial Python client for the Whoop API — official read endpoints plus unofficial write endpoints for managing your own Whoop data.

## Why?

The official Whoop API is read-only. This library adds write support so you can programmatically log activities, track workouts with full exercise details, manage journal entries, update your weight, and more — all through your own Whoop account using your own credentials.

> **Note:** This is an unofficial client library and is not affiliated with or endorsed by Whoop. Write endpoints use Whoop's internal API, which is undocumented and may change without notice. Users authenticate with their own Whoop credentials to manage their own data. Use at your own discretion.

## Install

```bash
pip install whoop-write-api
```

## Quick Start

```python
import asyncio
from whoop import CognitoAuth, WhoopClient, SportType

async def main():
    # log in with your whoop email/password (one time)
    auth = CognitoAuth()
    tokens = await auth.login("your@email.com", "your-password")

    async with WhoopClient(token_set=tokens) as client:
        # read recovery
        recoveries = await client.get_recovery()
        print(f"Recovery: {recoveries[0].recovery_score}%")

        # log a sauna session
        result = await client.create_activity(
            "sauna",
            start="2026-03-18T18:00:00.000Z",
            end="2026-03-18T18:20:00.000Z",
        )
        print(f"Logged sauna {result.id}")

        # set alarm
        await client.set_alarm("07:00:00")

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

### Cognito auth — read + write APIs (recommended)

Log in with your Whoop email/password. Tokens auto-refresh — no manual intervention needed.

```python
from whoop import CognitoAuth, WhoopClient, TokenSet, WhoopAuthExpiredError

# first time: log in and save tokens
auth = CognitoAuth()
tokens = await auth.login("your@email.com", "your-password")
# save tokens.access_token, tokens.refresh_token, tokens.expires_at to your DB

# every time after: load tokens and go
async def on_refresh(new_tokens: TokenSet):
    db.save(new_tokens)  # persist refreshed tokens

async with WhoopClient(
    token_set=tokens,
    on_token_refresh=on_refresh,
) as client:
    recovery = await client.get_recovery()
    await client.create_activity("sauna", start, end)
```

Tokens refresh automatically before expiry. If the refresh token expires (weeks/months), `WhoopAuthExpiredError` is raised so you can prompt re-auth.

**Works with:** everything — all read endpoints, activity creation, exercise linking, journal entries, weight updates, activity deletion.

You can also pass a raw bearer token if you have one:
```python
client = WhoopClient(token="cognito-bearer-token")
```

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

## Write API

Requires Cognito auth (login with your Whoop email/password). See [Authentication](#authentication) above.

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

- [ ] Synchronous client wrapper

See ENDPOINTS.md for the full endpoint reference.

## License

MIT
