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

**These are undocumented internal endpoints and may change without notice.** Users authenticate with their own Whoop credentials to manage their own data.

Source: Whoop iOS app v5.43.0 (March 2026).

### Required Headers

```
Authorization: Bearer <token>
Content-Type: application/json
x-whoop-device-platform: API
x-whoop-time-zone: America/New_York
```

---

### Activities

#### Create Activity (non-GPS)

Use for sauna, stretching, meditation, ice bath, yoga, weightlifting, and other non-GPS activities.

```
POST /activities-service/v2/activities
```

```json
{
  "during": "['2026-03-18T21:02:54.336Z','2026-03-18T21:03:11.048Z')",
  "source": "user",
  "type": "sauna",
  "timezone": "America/New_York"
}
```

The `during` field uses PostgreSQL range syntax: `['start','end')`.

The `type` field uses string names. Known values:

| Type String | Activity |
|-------------|----------|
| `running` | Running |
| `cycling` | Cycling |
| `weightlifting` | Weightlifting |
| `sauna` | Dry Sauna |
| `ice_bath` | Ice Bath |
| `meditation` | Meditation |
| `yoga` | Yoga |
| `stretching` | Stretching |
| `walking` | Walking |
| `hiking` | Hiking |
| `swimming` | Swimming |

Response (200):

```json
{
  "id": "68f455f4-b2fe-45ad-91c4-2f613fb7ed74",
  "cycle_id": 1374850090,
  "user_id": 23759045,
  "during": "['2026-03-18T21:02:54.336Z','2026-03-18T21:03:11.048Z')",
  "timezone": "America/New_York",
  "source": "user",
  "score_state": "pending",
  "score_type": "RECOVERY",
  "type": "sauna",
  "translated_type": "Dry Sauna",
  "timezone_offset_from_model": "-04:00"
}
```

Note: `id` is a UUID string, not an integer. `score_type` is `"RECOVERY"` for recovery activities (sauna, stretching, meditation) and `"CARDIO"` for cardio/strength.

#### Create Activity (GPS)

Use for running and other GPS-tracked activities.

```
POST /core-details-bff/v0/create-activity
```

```json
{
  "sport_id": 0,
  "start_time": "2026-03-18T21:02:29.968Z",
  "end_time": "2026-03-18T21:02:36.375Z",
  "gps_enabled": true
}
```

Uses integer `sport_id` (see SportType enum). Response format same as non-GPS but `score_type` is `"CARDIO"`.

#### Delete Cardio/Strength Activity

```
DELETE /core-details-bff/v1/cardio-details?activityId={uuid}
```

Response: 204 No Content

#### Delete Recovery Activity

For sauna, stretching, meditation, ice bath, etc.

```
DELETE /core-details-bff/v1/recovery-details?recoveryActivityId={uuid}
```

Response: 204 No Content

---

### Strength Training / Exercises

#### Get Exercise Library

Fetches the complete Whoop exercise catalog (310 exercises) with equipment types, muscle groups, movement patterns, instructions, and image/video URLs.

```
GET /weightlifting-service/v2/exercise
```

Response (200):

```json
{
  "exercises": [
    {
      "exercise_id": "BENCHPRESS_BARBELL",
      "name": "Bench Press - Barbell",
      "equipment": "BARBELL",
      "muscle_groups": ["CHEST"],
      "movement_pattern": "HORIZONTAL_PRESS",
      "exercise_type": "STRENGTH",
      "volume_input_format": "REPS",
      "laterality": "BILATERAL",
      "trackable": true,
      "instructions": ["Lie on the bench with your back and head resting on it..."],
      "image_url": "https://dh6o7n168ts9.cloudfront.net/exercises/BENCHPRESS_BARBELL.jpg",
      "video_url": "https://dh6o7n168ts9.cloudfront.net/exercise-videos-temp/BENCHPRESS_BARBELL.mp4"
    }
  ],
  "filter_options": {
    "equipment": [{"internal_value": "BARBELL"}, {"internal_value": "BODY"}, ...],
    "muscle_groups": [{"internal_value": "CHEST"}, {"internal_value": "LEGS"}, ...],
    "movement_patterns": [{"internal_value": "SQUAT"}, {"internal_value": "HINGE"}, ...]
  }
}
```

Equipment types: `BARBELL`, `BODY`, `DUMBBELL`, `KETTLEBELL`, `MACHINE`, `MEDICINE_BALL`, `OTHER`, `PLYO_BOX`, `PULL_UP_BAR`, `STABILITY_BALL`

Muscle groups: `ARMS`, `BACK`, `CHEST`, `CORE`, `FULL_BODY`, `LEGS`, `OTHER`, `SHOULDERS`

Movement patterns: `HINGE`, `HORIZONTAL_PRESS`, `HORIZONTAL_PULL`, `JUMP`, `LUNGE`, `OLY_LIFT`, `OTHER`, `SQUAT`, `VERTICAL_PRESS`, `VERTICAL_PULL`

Volume input formats: `REPS` (count), `WEIGHT` (weight + reps), `TIME` (seconds)

#### Link Exercises to a Workout

After creating a weightlifting activity, link exercises with full set/rep/weight data.

```
POST /weightlifting-service/v2/weightlifting-workout/link-cardio-workout
```

```json
{
  "template": {
    "workout_groups": [
      {
        "workout_exercises": [
          {
            "exercise_details": {
              "exercise_id": "BENCHPRESS_BARBELL",
              "name": "Bench Press - Barbell",
              "equipment": "BARBELL",
              "muscle_groups": ["CHEST"],
              "exercise_type": "STRENGTH",
              "volume_input_format": "REPS",
              "laterality": "BILATERAL",
              "movement_pattern": "HORIZONTAL_PRESS"
            },
            "sets": [
              {"number_of_reps": 3, "weight": 225},
              {"number_of_reps": 4, "weight": 225},
              {"number_of_reps": 5, "weight": 225}
            ]
          }
        ]
      },
      {
        "workout_exercises": [
          {
            "exercise_details": {
              "exercise_id": "FRONTPLANKELBOW",
              "name": "Front Plank",
              "equipment": "BODY",
              "muscle_groups": ["CORE"],
              "exercise_type": "STRENGTH",
              "volume_input_format": "REPS"
            },
            "sets": [
              {"number_of_reps": 0, "weight": 0, "time_in_seconds": 60},
              {"number_of_reps": 0, "weight": 0, "time_in_seconds": 60}
            ]
          }
        ]
      }
    ]
  }
}
```

Key details:
- Each exercise group in `workout_groups` contains one exercise with multiple sets
- `exercise_id` is a string identifier from Whoop's exercise library (e.g., `BENCHPRESS_BARBELL`)
- `weight` is in pounds (matches unit_system in user profile)
- Timed exercises (planks, holds) use `time_in_seconds` instead of `number_of_reps`
- The `exercise_details` fields `equipment`, `muscle_groups`, `movement_pattern` are optional but improve Whoop's strain calculations

Response (200):

```json
{
  "original_activity_id": "e4f1d7cf-0eb4-4ba1-a595-39d186ec4166",
  "original_activity_type": "weightlifting",
  "workout_metadata": {
    "id": "e4f1d7cf-...",
    "score_state": "complete",
    "type": "weightlifting",
    "weightlifting_workout_id": "e93efcf9-...",
    "workout_template_id": 9435983,
    "total_effective_volume_kg": 3309.854,
    "raw_msk_strain_score": 0.034
  }
}
```

#### Save Workout Template

Save a workout as a reusable template.

```
POST /weightlifting-service/v3/workout-template
```

Same payload structure as the `workout_groups` in link-cardio-workout. Returns `workout_template_key` for future use.

#### Known Exercise IDs

Exercises use string IDs from Whoop's library. Common ones:

| Exercise ID | Name | Equipment | Muscle Groups |
|-------------|------|-----------|---------------|
| `BENCHPRESS_BARBELL` | Bench Press - Barbell | BARBELL | CHEST |
| `SQUAT_BARBELL` | Squat - Barbell | BARBELL | QUADS |
| `DEADLIFT_BARBELL` | Deadlift - Barbell | BARBELL | BACK |
| `FRONTPLANKELBOW` | Front Plank | BODY | CORE |
| `OVERHEADPRESS_BARBELL` | Overhead Press - Barbell | BARBELL | SHOULDERS |

The full exercise library can be browsed in the Whoop app's exercise picker.

---

### Journal

#### Get Journal Behaviors (tracker definitions)

```
GET /journal-service/v2/journals/behaviors/user/{YYYY-MM-DD}
```

Returns all available journal trackers with their IDs, types, and magnitude ranges.

#### Get Journal Draft

```
GET /journal-service/v3/journals/drafts/mobile/{YYYY-MM-DD}
```

Returns any existing journal entries for the date.

#### Log Journal Entry

```
PUT /journal-service/v2/journals/entries/user/date/{YYYY-MM-DD}
```

```json
{
  "tracker_inputs": [
    {
      "behavior_tracker_id": 1,
      "answered_yes": false
    },
    {
      "behavior_tracker_id": 2,
      "answered_yes": true,
      "magnitude_input_value": 1,
      "magnitude_input_label": "1",
      "time_input_value": 1773842400000
    },
    {
      "behavior_tracker_id": 6,
      "answered_yes": false
    }
  ],
  "notes": "Optional free text notes"
}
```

Known behavior tracker IDs:

| ID | Name | Type | Magnitude |
|----|------|------|-----------|
| 1 | Alcohol | YES_NO | 1-20 drinks |
| 2 | Caffeine | YES_NO | 1-10 servings |
| 6 | Late Meal | YES_NO | — |
| 28 | Screentime | YES_NO | — |
| 89 | Protein | YES_NO | 0-1000 grams |

Additional trackers may vary by user configuration. Use the behaviors endpoint to get the current user's full tracker list.

Response: 204 No Content

---

### Profile

#### Update Profile / Weight

```
PUT /profile-service/v1/profile
```

```json
{
  "first_name": "Juan",
  "last_name": "Salazar",
  "email": "user@example.com",
  "birthday": "2000-12-07",
  "gender": "MALE",
  "physiological_baseline": "MALE",
  "height": 1.905,
  "weight": 115.67,
  "unit_system": "imperial",
  "country": "US",
  "state": "NJ"
}
```

All fields are required (send the full profile). `weight` is in kilograms. `height` is in meters.

Response: `true` (200)

---

### Sleep / Alarm

#### Set Smart Alarm

```
PUT /smart-alarm-service/v1/smartalarm/preferences
```

```json
{
  "enabled": true,
  "goal": "EXACT_TIME_OPTIMIZE_SLEEP",
  "upper_time_bound": "08:46:00",
  "time_zone_offset": "-0400",
  "schedule_enabled": false
}
```

Response includes computed alarm bounds and sleep recommendations.

---

### Legacy Endpoints

These older endpoints may still work but the Whoop app has migrated away from them:

| Method | Endpoint | Replacement |
|--------|----------|-------------|
| POST | /activities-service/v0/workouts | /activities-service/v2/activities |
| POST | /core-details-bff/v2/create-activity | /core-details-bff/v0/create-activity (v2 has date parsing issues) |

## Endpoint Discovery

If endpoints change, use mitmproxy or Charles Proxy to capture traffic from the Whoop mobile app:

1. Set up proxy on your phone pointing to your computer
2. Install the proxy's CA certificate on the phone
3. Open the Whoop app and perform the action you want to capture
4. Inspect the captured requests for the new endpoint paths
