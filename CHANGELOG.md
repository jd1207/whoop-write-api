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
