from __future__ import annotations
import httpx
from whoop.models import Recovery, Sleep, Workout, Cycle, BodyMeasurement
from whoop.exceptions import WhoopAPIError, WhoopRateLimitError

BASE_URL = "https://api.prod.whoop.com"


class WhoopReadAPI:
    def __init__(self, token: str):
        self.token = token

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def _get(self, path: str, params: dict | None = None) -> dict:
        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            resp = await client.get(path, headers=self._headers, params=params)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("X-RateLimit-Reset", "60"))
            raise WhoopRateLimitError(retry_after=retry_after)
        if resp.status_code != 200:
            raise WhoopAPIError(f"GET {path} failed: {resp.text}", status_code=resp.status_code, response_body=resp.text)
        return resp.json()

    async def _get_paginated(self, path: str, start: str | None = None, end: str | None = None) -> list[dict]:
        params: dict = {}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        all_records = []
        while True:
            data = await self._get(path, params)
            all_records.extend(data.get("records", []))
            next_token = data.get("next_token")
            if not next_token:
                break
            params["nextToken"] = next_token
        return all_records

    async def get_recovery(self, start: str | None = None, end: str | None = None) -> list[Recovery]:
        records = await self._get_paginated("/developer/v1/recovery", start, end)
        return [Recovery.from_api(r) for r in records]

    async def get_sleep(self, start: str | None = None, end: str | None = None) -> list[Sleep]:
        records = await self._get_paginated("/developer/v1/activity/sleep", start, end)
        return [Sleep.from_api(r) for r in records]

    async def get_workouts(self, start: str | None = None, end: str | None = None) -> list[Workout]:
        records = await self._get_paginated("/developer/v1/activity/workout", start, end)
        return [Workout.from_api(r) for r in records]

    async def get_cycles(self, start: str | None = None, end: str | None = None) -> list[Cycle]:
        records = await self._get_paginated("/developer/v1/cycle", start, end)
        return [Cycle.from_api(r) for r in records]

    async def get_body_measurement(self) -> BodyMeasurement:
        data = await self._get("/developer/v1/user/body_measurement")
        return BodyMeasurement.from_api(data)
