import time
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock
from whoop.client import WhoopClient
from whoop.auth import WhoopAuth
from whoop.cognito import TokenSet
from whoop.exceptions import WhoopAuthExpiredError, WhoopAuthError


def test_simple_token_mode():
    client = WhoopClient(token="simple-token")
    assert client._token_holder.token == "simple-token"
    assert client._refresh_token is None


def test_token_set_mode():
    ts = TokenSet(access_token="a", refresh_token="r", expires_at=9999999999.0)
    client = WhoopClient(token_set=ts)
    assert client._token_holder.token == "a"
    assert client._refresh_token == "r"
    assert client._expires_at == 9999999999.0


def test_no_auth_raises():
    with pytest.raises(ValueError):
        WhoopClient()


def test_backwards_compat_auth_mode():
    auth = WhoopAuth()
    auth.access_token = "oauth-token"
    client = WhoopClient(auth=auth)
    assert client._token_holder.token == "oauth-token"
    assert client._refresh_token is None


@pytest.mark.asyncio
async def test_context_manager(mock_api, fake_token):
    async with WhoopClient(token=fake_token) as client:
        assert client._shared_client is not None
    assert client._shared_client is None


@pytest.mark.asyncio
async def test_context_manager_calls_ensure_token(mock_api):
    ts = TokenSet(
        access_token="old",
        refresh_token="refresh-123",
        expires_at=time.time() - 100,
    )
    mock_api.post("/auth-service/v3/whoop").mock(
        return_value=httpx.Response(200, json={
            "AuthenticationResult": {
                "AccessToken": "new-from-enter",
                "ExpiresIn": 86400,
            },
        })
    )
    async with WhoopClient(token_set=ts) as client:
        assert client._token_holder.token == "new-from-enter"


@pytest.mark.asyncio
async def test_context_manager_with_simple_token(mock_api, fake_token):
    mock_api.get("/developer/v2/recovery").mock(
        return_value=httpx.Response(200, json={
            "records": [{
                "cycle_id": 1, "sleep_id": 2, "user_id": 3,
                "score": {
                    "recovery_score": 88.0, "resting_heart_rate": 48.0,
                    "hrv_rmssd_milli": 72.0, "spo2_percentage": 98.0,
                    "skin_temp_celsius": 33.0,
                },
                "created_at": "2026-03-18T07:00:00.000Z",
                "updated_at": "2026-03-18T07:00:00.000Z",
            }],
            "next_token": None,
        })
    )
    async with WhoopClient(token=fake_token) as client:
        recoveries = await client.get_recovery()
        assert recoveries[0].recovery_score == 88.0


@pytest.mark.asyncio
async def test_ensure_token_skips_simple_mode(fake_token):
    client = WhoopClient(token=fake_token)
    await client._ensure_token()


@pytest.mark.asyncio
async def test_ensure_token_skips_when_not_near_expiry():
    ts = TokenSet(
        access_token="current",
        refresh_token="r",
        expires_at=time.time() + 3600,
    )
    client = WhoopClient(token_set=ts)
    await client._ensure_token()
    assert client._token_holder.token == "current"


@pytest.mark.asyncio
async def test_ensure_token_refreshes_when_expiring(mock_api):
    ts = TokenSet(
        access_token="old-access",
        refresh_token="refresh-123",
        expires_at=time.time() - 100,
    )
    mock_api.post("/auth-service/v3/whoop").mock(
        return_value=httpx.Response(200, json={
            "AuthenticationResult": {
                "AccessToken": "new-access",
                "ExpiresIn": 86400,
            },
        })
    )
    client = WhoopClient(token_set=ts)
    await client._ensure_token()
    assert client._token_holder.token == "new-access"


@pytest.mark.asyncio
async def test_ensure_token_calls_callback(mock_api):
    ts = TokenSet(
        access_token="old",
        refresh_token="refresh-123",
        expires_at=time.time() - 100,
    )
    mock_api.post("/auth-service/v3/whoop").mock(
        return_value=httpx.Response(200, json={
            "AuthenticationResult": {
                "AccessToken": "new",
                "ExpiresIn": 86400,
            },
        })
    )
    callback = AsyncMock()
    client = WhoopClient(token_set=ts, on_token_refresh=callback)
    await client._ensure_token()
    callback.assert_called_once()
    called_ts = callback.call_args[0][0]
    assert isinstance(called_ts, TokenSet)
    assert called_ts.access_token == "new"


@pytest.mark.asyncio
async def test_ensure_token_no_callback_ok(mock_api):
    ts = TokenSet(
        access_token="old",
        refresh_token="refresh-123",
        expires_at=time.time() - 100,
    )
    mock_api.post("/auth-service/v3/whoop").mock(
        return_value=httpx.Response(200, json={
            "AuthenticationResult": {
                "AccessToken": "new",
                "ExpiresIn": 86400,
            },
        })
    )
    client = WhoopClient(token_set=ts, on_token_refresh=None)
    await client._ensure_token()
    assert client._token_holder.token == "new"


@pytest.mark.asyncio
async def test_ensure_token_expired_refresh_raises(mock_api):
    ts = TokenSet(
        access_token="old",
        refresh_token="dead-refresh",
        expires_at=time.time() - 100,
    )
    mock_api.post("/auth-service/v3/whoop").mock(
        return_value=httpx.Response(400, json={
            "__type": "NotAuthorizedException",
            "message": "Refresh Token has expired.",
        })
    )
    client = WhoopClient(token_set=ts)
    with pytest.raises(WhoopAuthExpiredError):
        await client._ensure_token()


@pytest.mark.asyncio
async def test_ensure_token_network_error_still_valid():
    """network error during refresh but token still within validity"""
    ts = TokenSet(
        access_token="current",
        refresh_token="r",
        expires_at=time.time() + 100,
    )
    client = WhoopClient(token_set=ts)
    # force refresh attempt by setting expires_at within buffer
    client._expires_at = time.time() + 200
    # but keep it valid; mock cognito to raise network error
    client._cognito.refresh = AsyncMock(side_effect=ConnectionError("no network"))
    client._expires_at = time.time() + 200
    await client._ensure_token()
    assert client._token_holder.token == "current"


@pytest.mark.asyncio
async def test_ensure_token_network_error_past_expiry():
    """network error during refresh and token already expired"""
    ts = TokenSet(
        access_token="expired",
        refresh_token="r",
        expires_at=time.time() - 100,
    )
    client = WhoopClient(token_set=ts)
    client._cognito.refresh = AsyncMock(side_effect=ConnectionError("no network"))
    with pytest.raises(WhoopAuthError, match="token expired and refresh failed"):
        await client._ensure_token()


@pytest.mark.asyncio
async def test_token_propagates_to_read_write():
    ts = TokenSet(
        access_token="initial",
        refresh_token="r",
        expires_at=9999999999.0,
    )
    client = WhoopClient(token_set=ts)
    assert client._read.token == "initial"
    assert client._write.token == "initial"
    client._token_holder.token = "updated"
    assert client._read.token == "updated"
    assert client._write.token == "updated"


@pytest.mark.asyncio
async def test_401_triggers_refresh_and_retry(mock_api):
    ts = TokenSet(
        access_token="stale",
        refresh_token="refresh-ok",
        expires_at=time.time() + 3600,
    )
    call_count = 0

    def api_handler(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(401, text="Unauthorized")
        return httpx.Response(200, json={
            "records": [], "next_token": None,
        })

    mock_api.get("/developer/v2/recovery").mock(side_effect=api_handler)
    mock_api.post("/auth-service/v3/whoop").mock(
        return_value=httpx.Response(200, json={
            "AuthenticationResult": {
                "AccessToken": "fresh",
                "ExpiresIn": 86400,
            },
        })
    )
    client = WhoopClient(token_set=ts)
    result = await client.get_recovery()
    assert result == []
    assert client._token_holder.token == "fresh"


@pytest.mark.asyncio
async def test_401_after_retry_raises(mock_api):
    ts = TokenSet(
        access_token="stale",
        refresh_token="refresh-ok",
        expires_at=time.time() + 3600,
    )
    mock_api.get("/developer/v2/recovery").mock(
        return_value=httpx.Response(401, text="Unauthorized"),
    )
    mock_api.post("/auth-service/v3/whoop").mock(
        return_value=httpx.Response(200, json={
            "AuthenticationResult": {
                "AccessToken": "still-bad",
                "ExpiresIn": 86400,
            },
        })
    )
    client = WhoopClient(token_set=ts)
    with pytest.raises(WhoopAuthExpiredError, match="token rejected after refresh"):
        await client.get_recovery()


@pytest.mark.asyncio
async def test_backwards_compat_no_context_manager(mock_api, fake_token):
    mock_api.get("/developer/v2/recovery").mock(
        return_value=httpx.Response(200, json={
            "records": [],
            "next_token": None,
        })
    )
    client = WhoopClient(token=fake_token)
    result = await client.get_recovery()
    assert result == []


@pytest.mark.asyncio
async def test_context_manager_end_to_end(mock_api):
    ts = TokenSet(
        access_token="valid",
        refresh_token="r",
        expires_at=time.time() + 3600,
    )
    mock_api.get("/developer/v2/recovery").mock(
        return_value=httpx.Response(200, json={
            "records": [{
                "cycle_id": 1, "sleep_id": 2, "user_id": 3,
                "score": {
                    "recovery_score": 95.0, "resting_heart_rate": 45.0,
                    "hrv_rmssd_milli": 80.0, "spo2_percentage": 99.0,
                    "skin_temp_celsius": 33.0,
                },
                "created_at": "2026-03-18T07:00:00.000Z",
                "updated_at": "2026-03-18T07:00:00.000Z",
            }],
            "next_token": None,
        })
    )
    async with WhoopClient(token_set=ts) as client:
        recoveries = await client.get_recovery()
        assert recoveries[0].recovery_score == 95.0
