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
