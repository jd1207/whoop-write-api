from __future__ import annotations
from whoop.auth import WhoopAuth
from whoop.read import WhoopReadAPI
from whoop.write import WhoopWriteAPI
from whoop.models import (
    Recovery, Sleep, Workout, Cycle, BodyMeasurement, WorkoutWrite,
)


class WhoopClient:
    def __init__(
        self,
        token: str | None = None,
        auth: WhoopAuth | None = None,
        timezone: str = "America/Los_Angeles",
    ):
        if token:
            self._token = token
        elif auth and auth.access_token:
            self._token = auth.access_token
        else:
            raise ValueError("provide either token or authenticated WhoopAuth")
        self._read = WhoopReadAPI(token=self._token)
        self._write = WhoopWriteAPI(token=self._token, timezone=timezone)
        self._auth = auth

    async def get_recovery(self, start: str | None = None, end: str | None = None) -> list[Recovery]:
        return await self._read.get_recovery(start, end)

    async def get_sleep(self, start: str | None = None, end: str | None = None) -> list[Sleep]:
        return await self._read.get_sleep(start, end)

    async def get_workouts(self, start: str | None = None, end: str | None = None) -> list[Workout]:
        return await self._read.get_workouts(start, end)

    async def get_cycles(self, start: str | None = None, end: str | None = None) -> list[Cycle]:
        return await self._read.get_cycles(start, end)

    async def get_body_measurement(self) -> BodyMeasurement:
        return await self._read.get_body_measurement()

    async def log_workout(self, workout: WorkoutWrite) -> dict:
        return await self._write.log_workout(workout)
