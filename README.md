# whoop-write-api

Python client for the Whoop API — both official read endpoints and reverse-engineered write endpoints.

## Why?

The official Whoop API is read-only. This library adds write support so you can programmatically log workouts with full exercise details (sets, reps, weights) to Whoop's Strength Trainer.

> **Disclaimer:** Write endpoints are reverse-engineered from Whoop's internal API and may break without notice. Read endpoints use the official documented API.

## Install

```bash
pip install whoop-write-api
```

## Quick Start

```python
import asyncio
from whoop import WhoopClient, WorkoutWrite, ExerciseWrite

async def main():
    client = WhoopClient(token="your-bearer-token")

    # read recovery
    recoveries = await client.get_recovery()
    print(f"Recovery: {recoveries[0].recovery_score}%")

    # log a workout
    workout = WorkoutWrite(
        sport_id=1,  # strength training
        start="2026-03-16T14:00:00.000Z",
        end="2026-03-16T15:00:00.000Z",
        exercises=[
            ExerciseWrite(name="Bench Press", sets=5, reps=3, weight=235),
            ExerciseWrite(name="Incline DB Press", sets=3, reps=10, weight=60),
        ],
    )
    result = await client.log_workout(workout)
    print(f"Logged workout {result['activity_id']}")

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

- `client.log_workout(WorkoutWrite)` — creates activity + links exercises

## License

MIT
