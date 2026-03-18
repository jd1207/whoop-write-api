from __future__ import annotations
import httpx
from whoop.token_holder import TokenHolder
from whoop.models import Recovery, Sleep, Workout, Cycle, BodyMeasurement
from whoop.exceptions import WhoopAPIError, WhoopRateLimitError

BASE_URL = "https://api.prod.whoop.com"


class WhoopReadAPI:
    def __init__(self, token: str | TokenHolder = ""):
        if isinstance(token, TokenHolder):
            self._token_holder = token
        else:
            self._token_holder = TokenHolder(token)

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
        }

    async def _get(
        self, path: str, params: dict | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> dict:
        if client:
            resp = await client.get(path, headers=self._headers, params=params)
        else:
            async with httpx.AsyncClient(base_url=BASE_URL) as c:
                resp = await c.get(path, headers=self._headers, params=params)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("X-RateLimit-Reset", "60"))
            raise WhoopRateLimitError(retry_after=retry_after)
        if resp.status_code != 200:
            raise WhoopAPIError(
                f"GET {path} failed: {resp.text}",
                status_code=resp.status_code,
                response_body=resp.text,
            )
        return resp.json()

    async def _get_paginated(
        self, path: str, start: str | None = None, end: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> list[dict]:
        params: dict = {}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        all_records = []
        while True:
            data = await self._get(path, params, client=client)
            all_records.extend(data.get("records", []))
            next_token = data.get("next_token")
            if not next_token:
                break
            params["nextToken"] = next_token
        return all_records

    async def get_recovery(
        self, start: str | None = None, end: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> list[Recovery]:
        records = await self._get_paginated(
            "/developer/v2/recovery", start, end, client=client,
        )
        return [Recovery.from_api(r) for r in records]

    async def get_sleep(
        self, start: str | None = None, end: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> list[Sleep]:
        records = await self._get_paginated(
            "/developer/v2/activity/sleep", start, end, client=client,
        )
        return [Sleep.from_api(r) for r in records]

    async def get_workouts(
        self, start: str | None = None, end: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> list[Workout]:
        records = await self._get_paginated(
            "/developer/v2/activity/workout", start, end, client=client,
        )
        return [Workout.from_api(r) for r in records]

    async def get_cycles(
        self, start: str | None = None, end: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> list[Cycle]:
        records = await self._get_paginated(
            "/developer/v2/cycle", start, end, client=client,
        )
        return [Cycle.from_api(r) for r in records]

    async def get_body_measurement(
        self, client: httpx.AsyncClient | None = None,
    ) -> BodyMeasurement:
        data = await self._get(
            "/developer/v2/user/body_measurement", client=client,
        )
        return BodyMeasurement.from_api(data)
