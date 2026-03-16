from __future__ import annotations
import httpx
from whoop.models import WorkoutWrite, ExerciseWrite
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

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "x-whoop-time-zone": self.timezone,
            **WRITE_HEADERS_EXTRA,
        }

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

    async def create_workout(self, workout: WorkoutWrite) -> dict:
        return await self._post(
            "/activities-service/v0/workouts",
            workout.to_activity_payload(),
        )

    async def link_exercises(self, workout_id: int, exercises: list[ExerciseWrite]) -> dict:
        payload = {
            "cardio_workout_id": workout_id,
            "exercises": [
                {
                    "name": ex.name,
                    "sets": ex.sets,
                    "reps": ex.reps,
                    "weight": ex.weight,
                    "weight_unit": ex.weight_unit,
                }
                for ex in exercises
            ],
        }
        return await self._post(
            "/weightlifting-service/v2/weightlifting-workout/link-cardio-workout",
            payload,
        )

    async def log_workout(self, workout: WorkoutWrite) -> dict:
        activity = await self.create_workout(workout)
        activity_id = activity["id"]
        exercises_result = await self.link_exercises(activity_id, workout.exercises)
        return {
            "activity_id": activity_id,
            "exercises_linked": exercises_result.get("status") == "linked",
        }
