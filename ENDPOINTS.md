# Whoop API Endpoints Reference

## Official Read API (api.prod.whoop.com)

Documented at [developer.whoop.com](https://developer.whoop.com). OAuth2 required.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /developer/v2/recovery | Recovery scores (HRV, RHR, SpO2) |
| GET | /developer/v2/activity/sleep | Sleep stages, performance, efficiency |
| GET | /developer/v2/activity/workout | Workout strain, HR data |
| GET | /developer/v2/cycle | Daily strain cycles |
| GET | /developer/v2/user/body_measurement | Height, weight, max HR |
| GET | /developer/v2/user/profile/basic | User profile |

All collection endpoints support pagination: `start`, `end` (ISO 8601), `limit` (max 25), `nextToken`.

Rate limits: 100 req/min, 10,000 req/day.

## Unofficial Write API (api.prod.whoop.com)

**These endpoints are reverse-engineered and may change without notice.**

Source: traffic analysis of the Whoop mobile app. See `scripts/find_endpoints.py` for discovery tools.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /activities-service/v0/workouts | Create a workout activity |
| POST | /weightlifting-service/v2/weightlifting-workout/link-cardio-workout | Link exercises to a workout |
| POST | /weightlifting-service/v3/workout-template | Create a workout template |
| GET | /weightlifting-service/v2/workout-library/ | Get workout templates |
| GET | /activities-service/v1/sports/history | Get sports/activity history |
| GET | /activities-service/v2/activity-types | Get all activity types |

### Required Headers (write endpoints)

```
Authorization: Bearer <token>
Content-Type: application/json
x-whoop-device-platform: API
locale: en_US
x-whoop-time-zone: America/Los_Angeles
```

### Create Workout Payload

```json
{
  "gpsEnabled": false,
  "timezoneOffset": "+0000",
  "sportId": 1,
  "source": "user",
  "during": {
    "lower": "2026-03-16T14:00:00.000Z",
    "upper": "2026-03-16T15:00:00.000Z",
    "bounds": "[)"
  }
}
```

### Link Exercises Payload

```json
{
  "cardio_workout_id": 42,
  "exercises": [
    {"name": "Bench Press", "sets": 5, "reps": 3, "weight": 235, "weight_unit": "lbs"}
  ]
}
```

## Endpoint Discovery

If endpoints change, use mitmproxy or Charles Proxy to capture traffic from the Whoop mobile app:

1. Set up proxy on your phone pointing to your computer
2. Install the proxy's CA certificate on the phone
3. Open the Whoop app and perform the action you want to capture
4. Inspect the captured requests for the new endpoint paths
