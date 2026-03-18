# Changelog

## v0.3.0 (unreleased)

- Add `create_activity()` via v2 endpoint — uses string type names ("sauna", "weightlifting")
- Add `delete_activity()` — supports both cardio and recovery activity types
- Add `link_exercises_detailed()` — full Whoop exercise format with exercise IDs and per-set data
- Add `DetailedExercise` and `ExerciseSet` models for rich exercise data
- Add `log_journal()` — log daily journal entries (caffeine, alcohol, supplements, etc.)
- Add `get_journal_behaviors()` — fetch available journal trackers for a date
- Add `JournalInput` and `JournalBehavior` models
- Add `ActivityResult` model for v2 activity creation responses (UUID IDs)
- Add `update_weight()` — update weight on Whoop profile (auto-preserves other fields)
- Add `set_alarm()` — configure smart alarm preferences
- Add `ExerciseWrite.exercise_id` field for Whoop exercise library integration
- Split write models into `write_models.py` for better file organization
- Migrate read API from v1 to v2 endpoints (v1 returns 404 since Oct 2025)
- Fix `exchange_code()` crash when OAuth response missing refresh_token
- Deprecate `login_password()` — legacy endpoint is dead
- Document auth requirements: Developer OAuth2 (read only) vs Cognito (read + write)
- Complete unofficial endpoint reference in ENDPOINTS.md

## v0.2.0 (2026-03-16)

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
