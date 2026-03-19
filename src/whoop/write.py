from __future__ import annotations
from datetime import datetime
from zoneinfo import ZoneInfo
import httpx
from whoop.token_holder import TokenHolder
from whoop.write_models import (
    WorkoutWrite, ExerciseWrite, WorkoutResult, SportTypeInfo,
    ActivityResult, DetailedExercise, JournalInput, JournalBehavior,
)
from whoop.write_exercises import ExerciseCatalog
from whoop.exceptions import WhoopAPIError
from whoop import write_journal

BASE_URL = "https://api.prod.whoop.com"
WRITE_HEADERS_EXTRA = {"x-whoop-device-platform": "API", "locale": "en_US"}
RECOVERY_TYPES = {"sauna", "stretching", "meditation", "ice_bath", "yoga"}


class WhoopWriteAPI:
    def __init__(self, token: str | TokenHolder = "", timezone: str = "America/Los_Angeles"):
        if isinstance(token, TokenHolder):
            self._token_holder = token
        else:
            self._token_holder = TokenHolder(token)
        self.timezone = timezone
        self._sport_types_cache: list[SportTypeInfo] | None = None
        self._exercises_cache: ExerciseCatalog | None = None
        try:
            ZoneInfo(timezone)
        except KeyError:
            raise ValueError(f"invalid timezone: {timezone}")

    @property
    def token(self) -> str:
        return self._token_holder.token

    @token.setter
    def token(self, value: str) -> None:
        self._token_holder.token = value

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token_holder.token}",
            "Content-Type": "application/json",
            "x-whoop-time-zone": self.timezone, **WRITE_HEADERS_EXTRA,
        }

    def _offset_for(self, iso_timestamp: str) -> str:
        """compute UTC offset string for a given ISO 8601 timestamp"""
        dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        local = dt.astimezone(ZoneInfo(self.timezone))
        total_seconds = int(local.utcoffset().total_seconds())
        sign = "+" if total_seconds >= 0 else "-"
        hours, remainder = divmod(abs(total_seconds), 3600)
        return f"{sign}{hours:02d}{remainder // 60:02d}"

    async def _request(self, method: str, path: str, client: httpx.AsyncClient | None = None, **kwargs):
        """send an HTTP request using the shared client or a temporary one"""
        if client:
            resp = await getattr(client, method)(path, headers=self._headers, **kwargs)
        else:
            async with httpx.AsyncClient(base_url=BASE_URL) as c:
                resp = await getattr(c, method)(path, headers=self._headers, **kwargs)
        return resp

    async def _post(self, path: str, json: dict, client: httpx.AsyncClient | None = None) -> dict:
        resp = await self._request("post", path, client, json=json)
        if resp.status_code not in (200, 201):
            raise WhoopAPIError(f"POST {path} failed: {resp.text}", status_code=resp.status_code, response_body=resp.text)
        return resp.json()

    async def _get(self, path: str, client: httpx.AsyncClient | None = None) -> dict | list:
        resp = await self._request("get", path, client)
        if resp.status_code != 200:
            raise WhoopAPIError(f"GET {path} failed: {resp.text}", status_code=resp.status_code, response_body=resp.text)
        return resp.json()

    async def _put(self, path: str, json: dict, client: httpx.AsyncClient | None = None) -> httpx.Response:
        resp = await self._request("put", path, client, json=json)
        if resp.status_code not in (200, 204):
            raise WhoopAPIError(f"PUT {path} failed: {resp.text}", status_code=resp.status_code, response_body=resp.text)
        return resp

    async def _delete(self, path: str, client: httpx.AsyncClient | None = None) -> None:
        resp = await self._request("delete", path, client)
        if resp.status_code != 204:
            raise WhoopAPIError(f"DELETE {path} failed: {resp.text}", status_code=resp.status_code, response_body=resp.text)

    async def create_workout(self, workout: WorkoutWrite, client: httpx.AsyncClient | None = None) -> dict:
        offset = self._offset_for(workout.start)
        return await self._post(
            "/activities-service/v0/workouts",
            workout.to_activity_payload(timezone_offset=offset), client=client,
        )

    async def link_exercises(self, workout_id: int, exercises: list[ExerciseWrite], client: httpx.AsyncClient | None = None) -> dict:
        payload = {"cardio_workout_id": workout_id, "exercises": [ex.to_dict() for ex in exercises]}
        return await self._post(
            "/weightlifting-service/v2/weightlifting-workout/link-cardio-workout", payload, client=client,
        )

    async def log_workout(self, workout: WorkoutWrite, client: httpx.AsyncClient | None = None) -> WorkoutResult:
        activity = await self.create_workout(workout, client=client)
        activity_id = activity["id"]
        if not workout.exercises:
            return WorkoutResult(activity_id=activity_id, exercises_linked=False)
        try:
            result = await self.link_exercises(activity_id, workout.exercises, client=client)
            return WorkoutResult(activity_id=activity_id, exercises_linked=result.get("status") == "linked")
        except WhoopAPIError as exc:
            return WorkoutResult(activity_id=activity_id, exercises_linked=False, error=str(exc))

    async def get_sport_types(self, client: httpx.AsyncClient | None = None) -> list[SportTypeInfo]:
        if self._sport_types_cache is not None:
            return self._sport_types_cache
        data = await self._get("/activities-service/v2/activity-types", client=client)
        self._sport_types_cache = [SportTypeInfo.from_api(item) for item in data]
        return self._sport_types_cache

    async def get_exercises(self, client: httpx.AsyncClient | None = None) -> ExerciseCatalog:
        if self._exercises_cache is not None:
            return self._exercises_cache
        data = await self._get("/weightlifting-service/v2/exercise", client=client)
        self._exercises_cache = ExerciseCatalog.from_api(data)
        return self._exercises_cache

    async def create_activity(self, activity_type: str, start: str, end: str, client: httpx.AsyncClient | None = None) -> ActivityResult:
        """create activity via v2 endpoint (sauna, stretching, running, etc.)"""
        payload = {"during": f"['{start}','{end}')", "source": "user", "type": activity_type, "timezone": self.timezone}
        return ActivityResult.from_api(await self._post("/activities-service/v2/activities", payload, client=client))

    async def delete_activity(self, activity_id: str, is_recovery: bool = False, client: httpx.AsyncClient | None = None) -> None:
        """delete an activity by uuid, routing to the correct endpoint"""
        if is_recovery:
            path = f"/core-details-bff/v1/recovery-details?recoveryActivityId={activity_id}"
        else:
            path = f"/core-details-bff/v1/cardio-details?activityId={activity_id}"
        await self._delete(path, client=client)

    async def link_exercises_detailed(self, activity_id: str, exercises: list[DetailedExercise], client: httpx.AsyncClient | None = None) -> dict:
        """link exercises using the full whoop workout format"""
        payload = {
            "cardio_workout_id": activity_id,
            "template": {"workout_groups": [{"workout_exercises": [ex.to_dict() for ex in exercises]}]},
        }
        return await self._post(
            "/weightlifting-service/v2/weightlifting-workout/link-cardio-workout", payload, client=client,
        )

    async def log_journal(self, date: str, inputs: list[JournalInput], notes: str = "", client: httpx.AsyncClient | None = None) -> None:
        await write_journal.log_journal(self, date, inputs, notes, client=client)

    async def get_journal_behaviors(self, date: str, client: httpx.AsyncClient | None = None) -> list[JournalBehavior]:
        return await write_journal.get_journal_behaviors(self, date, client=client)

    async def update_weight(self, weight_kg: float, client: httpx.AsyncClient | None = None) -> bool:
        return await write_journal.update_weight(self, weight_kg, client=client)

    async def set_alarm(self, time: str, enabled: bool = True, timezone_offset: str = "-0400", client: httpx.AsyncClient | None = None) -> dict:
        return await write_journal.set_alarm(self, time, enabled, timezone_offset, client=client)
