from __future__ import annotations
from typing import TYPE_CHECKING
import httpx

from whoop.write_models import JournalInput, JournalBehavior

if TYPE_CHECKING:
    from whoop.write import WhoopWriteAPI


async def log_journal(
    api: WhoopWriteAPI, date: str, inputs: list[JournalInput],
    notes: str = "", client: httpx.AsyncClient | None = None,
) -> None:
    """log journal entry for a given date (YYYY-MM-DD)"""
    payload: dict = {
        "tracker_inputs": [inp.to_dict() for inp in inputs],
    }
    if notes:
        payload["notes"] = notes
    await api._put(
        f"/journal-service/v2/journals/entries/user/date/{date}",
        payload, client=client,
    )


async def get_journal_behaviors(
    api: WhoopWriteAPI, date: str,
    client: httpx.AsyncClient | None = None,
) -> list[JournalBehavior]:
    """get available journal behavior trackers for a date"""
    data = await api._get(
        f"/journal-service/v2/journals/behaviors/user/{date}",
        client=client,
    )
    return [JournalBehavior.from_api(item) for item in data]


async def update_weight(
    api: WhoopWriteAPI, weight_kg: float,
    client: httpx.AsyncClient | None = None,
) -> bool:
    """update user weight - fetches current profile then PUTs with new weight"""
    profile = await api._get(
        "/profile-service/v1/profile/bff/edit", client=client,
    )
    profile["weight_kilogram"] = weight_kg
    resp = await api._put(
        "/profile-service/v1/profile", profile, client=client,
    )
    if resp.status_code == 200:
        return resp.json()
    return True


async def set_alarm(
    api: WhoopWriteAPI, time: str, enabled: bool = True,
    timezone_offset: str = "-0400",
    client: httpx.AsyncClient | None = None,
) -> dict:
    """set smart alarm preferences"""
    payload = {
        "enabled": enabled,
        "goal": "EXACT_TIME_OPTIMIZE_SLEEP",
        "upper_time_bound": time,
        "time_zone_offset": timezone_offset,
        "schedule_enabled": False,
    }
    resp = await api._put(
        "/smart-alarm-service/v1/smartalarm/preferences",
        payload, client=client,
    )
    if resp.status_code == 200:
        return resp.json()
    return {}
