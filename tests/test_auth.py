import pytest
import httpx
import respx
from whoop.auth import WhoopAuth
from whoop.exceptions import WhoopAuthError

@pytest.mark.asyncio
async def test_oauth_token_exchange(mock_api):
    mock_api.post("/oauth/oauth2/token").mock(
        return_value=httpx.Response(200, json={
            "access_token": "new-token",
            "refresh_token": "new-refresh",
            "expires_in": 3600,
        })
    )
    auth = WhoopAuth(client_id="test-id", client_secret="test-secret")
    token = await auth.exchange_code("auth-code", "http://localhost/callback")
    assert token == "new-token"
    assert auth.refresh_token == "new-refresh"

@pytest.mark.asyncio
async def test_oauth_token_refresh(mock_api):
    mock_api.post("/oauth/oauth2/token").mock(
        return_value=httpx.Response(200, json={
            "access_token": "refreshed-token",
            "refresh_token": "new-refresh",
            "expires_in": 3600,
        })
    )
    auth = WhoopAuth(client_id="test-id", client_secret="test-secret")
    auth.refresh_token = "old-refresh"
    token = await auth.refresh()
    assert token == "refreshed-token"

@pytest.mark.asyncio
async def test_legacy_password_auth(mock_oauth):
    mock_oauth.post("/oauth/token").mock(
        return_value=httpx.Response(200, json={
            "access_token": "legacy-token",
            "refresh_token": "legacy-refresh",
            "expires_in": 86400,
        })
    )
    auth = WhoopAuth()
    token = await auth.login_password("user@test.com", "password123")
    assert token == "legacy-token"

@pytest.mark.asyncio
async def test_oauth_exchange_no_refresh_token(mock_api):
    mock_api.post("/oauth/oauth2/token").mock(
        return_value=httpx.Response(200, json={
            "access_token": "new-token",
            "token_type": "bearer",
            "expires_in": 3600,
        })
    )
    auth = WhoopAuth(client_id="test-id", client_secret="test-secret")
    token = await auth.exchange_code("auth-code", "http://localhost/callback")
    assert token == "new-token"
    assert auth.refresh_token is None


@pytest.mark.asyncio
async def test_login_password_emits_deprecation(mock_oauth):
    mock_oauth.post("/oauth/token").mock(
        return_value=httpx.Response(200, json={
            "access_token": "legacy-token",
            "expires_in": 86400,
        })
    )
    auth = WhoopAuth()
    with pytest.warns(DeprecationWarning, match="legacy endpoint"):
        await auth.login_password("user@test.com", "password123")


@pytest.mark.asyncio
async def test_auth_failure(mock_api):
    mock_api.post("/oauth/oauth2/token").mock(
        return_value=httpx.Response(401, json={"error": "invalid_grant"})
    )
    auth = WhoopAuth(client_id="test-id", client_secret="test-secret")
    with pytest.raises(WhoopAuthError):
        await auth.exchange_code("bad-code", "http://localhost/callback")
