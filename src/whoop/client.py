from __future__ import annotations
import time
from typing import Callable, Awaitable
import httpx
from whoop.auth import WhoopAuth
from whoop.cognito import CognitoAuth, TokenSet
from whoop.token_holder import TokenHolder
from whoop.read import WhoopReadAPI, BASE_URL
from whoop.write import WhoopWriteAPI
from whoop.write_exercises import ExerciseCatalog
from whoop.exceptions import WhoopAPIError, WhoopAuthError, WhoopAuthExpiredError
from whoop.models import (
    Recovery, Sleep, Workout, Cycle, BodyMeasurement, WorkoutWrite,
    WorkoutResult, SportTypeInfo, ActivityResult, DetailedExercise,
    JournalInput, JournalBehavior,
)

REFRESH_BUFFER_SECONDS = 300


class WhoopClient:
    def __init__(
        self,
        token: str | None = None,
        auth: WhoopAuth | None = None,
        token_set: TokenSet | None = None,
        on_token_refresh: Callable[[TokenSet], Awaitable[None]] | None = None,
        timezone: str = "America/Los_Angeles",
    ):
        if token_set:
            self._token_holder = TokenHolder(token_set.access_token)
            self._refresh_token = token_set.refresh_token
            self._expires_at = token_set.expires_at
        elif token:
            self._token_holder = TokenHolder(token)
            self._refresh_token = None
            self._expires_at = None
        elif auth and auth.access_token:
            self._token_holder = TokenHolder(auth.access_token)
            self._refresh_token = None
            self._expires_at = None
        else:
            raise ValueError("provide token, auth, or token_set")
        self._on_token_refresh = on_token_refresh
        self._cognito = CognitoAuth()
        self._read = WhoopReadAPI(token=self._token_holder)
        self._write = WhoopWriteAPI(token=self._token_holder, timezone=timezone)
        self._auth = auth
        self._shared_client: httpx.AsyncClient | None = None

    async def _ensure_token(self) -> None:
        """refresh access token if near expiry"""
        if not self._refresh_token or self._expires_at is None:
            return
        if time.time() < self._expires_at - REFRESH_BUFFER_SECONDS:
            return
        try:
            new_tokens = await self._cognito.refresh(self._refresh_token)
        except WhoopAuthExpiredError:
            raise
        except Exception as exc:
            if time.time() >= self._expires_at:
                raise WhoopAuthError(f"token expired and refresh failed: {exc}") from exc
            return
        self._token_holder.token = new_tokens.access_token
        self._expires_at = new_tokens.expires_at
        self._refresh_token = new_tokens.refresh_token
        if self._on_token_refresh:
            await self._on_token_refresh(new_tokens)

    async def _with_auth(self, coro_factory):
        """call coro_factory(), retry once with refresh on 401"""
        await self._ensure_token()
        try:
            return await coro_factory()
        except WhoopAPIError as e:
            if e.status_code != 401 or not self._refresh_token:
                raise
            self._expires_at = 0
            await self._ensure_token()
            try:
                return await coro_factory()
            except WhoopAPIError as e2:
                if e2.status_code == 401:
                    raise WhoopAuthExpiredError("token rejected after refresh") from e2
                raise

    async def __aenter__(self) -> WhoopClient:
        await self._ensure_token()
        self._shared_client = httpx.AsyncClient(base_url=BASE_URL)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._shared_client:
            await self._shared_client.aclose()
            self._shared_client = None

    async def get_recovery(self, start=None, end=None) -> list[Recovery]:
        return await self._with_auth(lambda: self._read.get_recovery(start, end, client=self._shared_client))

    async def get_sleep(self, start=None, end=None) -> list[Sleep]:
        return await self._with_auth(lambda: self._read.get_sleep(start, end, client=self._shared_client))

    async def get_workouts(self, start=None, end=None) -> list[Workout]:
        return await self._with_auth(lambda: self._read.get_workouts(start, end, client=self._shared_client))

    async def get_cycles(self, start=None, end=None) -> list[Cycle]:
        return await self._with_auth(lambda: self._read.get_cycles(start, end, client=self._shared_client))

    async def get_body_measurement(self) -> BodyMeasurement:
        return await self._with_auth(lambda: self._read.get_body_measurement(client=self._shared_client))

    async def log_workout(self, workout: WorkoutWrite) -> WorkoutResult:
        return await self._with_auth(lambda: self._write.log_workout(workout, client=self._shared_client))

    async def get_sport_types(self) -> list[SportTypeInfo]:
        return await self._with_auth(lambda: self._write.get_sport_types(client=self._shared_client))

    async def get_exercises(self) -> ExerciseCatalog:
        return await self._with_auth(lambda: self._write.get_exercises(client=self._shared_client))

    async def create_activity(self, activity_type: str, start: str, end: str) -> ActivityResult:
        return await self._with_auth(lambda: self._write.create_activity(activity_type, start, end, client=self._shared_client))

    async def delete_activity(self, activity_id: str, is_recovery: bool = False) -> None:
        return await self._with_auth(lambda: self._write.delete_activity(activity_id, is_recovery, client=self._shared_client))

    async def link_exercises_detailed(self, activity_id: str, exercises: list[DetailedExercise]) -> dict:
        return await self._with_auth(lambda: self._write.link_exercises_detailed(activity_id, exercises, client=self._shared_client))

    async def log_journal(self, date: str, inputs: list[JournalInput], notes: str = "") -> None:
        return await self._with_auth(lambda: self._write.log_journal(date, inputs, notes, client=self._shared_client))

    async def get_journal_behaviors(self, date: str) -> list[JournalBehavior]:
        return await self._with_auth(lambda: self._write.get_journal_behaviors(date, client=self._shared_client))

    async def update_weight(self, weight_kg: float) -> bool:
        return await self._with_auth(lambda: self._write.update_weight(weight_kg, client=self._shared_client))

    async def set_alarm(self, time: str, enabled: bool = True, timezone_offset: str = "-0400") -> dict:
        return await self._with_auth(lambda: self._write.set_alarm(time, enabled, timezone_offset, client=self._shared_client))
