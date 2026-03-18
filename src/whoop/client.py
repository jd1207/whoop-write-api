from __future__ import annotations
from whoop.auth import WhoopAuth
from whoop.read import WhoopReadAPI
from whoop.write import WhoopWriteAPI
from whoop.models import (
    Recovery, Sleep, Workout, Cycle, BodyMeasurement, WorkoutWrite,
    WorkoutResult, SportTypeInfo, ActivityResult, DetailedExercise,
    JournalInput, JournalBehavior,
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

    async def log_workout(self, workout: WorkoutWrite) -> WorkoutResult:
        return await self._write.log_workout(workout)

    async def get_sport_types(self) -> list[SportTypeInfo]:
        return await self._write.get_sport_types()

    async def create_activity(
        self, activity_type: str, start: str, end: str,
    ) -> ActivityResult:
        return await self._write.create_activity(activity_type, start, end)

    async def delete_activity(
        self, activity_id: str, is_recovery: bool = False,
    ) -> None:
        return await self._write.delete_activity(activity_id, is_recovery)

    async def link_exercises_detailed(
        self, activity_id: str, exercises: list[DetailedExercise],
    ) -> dict:
        return await self._write.link_exercises_detailed(activity_id, exercises)

    async def log_journal(
        self, date: str, inputs: list[JournalInput], notes: str = "",
    ) -> None:
        return await self._write.log_journal(date, inputs, notes)

    async def get_journal_behaviors(self, date: str) -> list[JournalBehavior]:
        return await self._write.get_journal_behaviors(date)

    async def update_weight(self, weight_kg: float) -> bool:
        return await self._write.update_weight(weight_kg)

    async def set_alarm(
        self,
        time: str,
        enabled: bool = True,
        timezone_offset: str = "-0400",
    ) -> dict:
        return await self._write.set_alarm(time, enabled, timezone_offset)
