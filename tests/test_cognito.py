import json
import time
import pytest
import httpx
from whoop.cognito import CognitoAuth, TokenSet, DEFAULT_CLIENT_ID
from whoop.exceptions import WhoopAuthError, WhoopAuthExpiredError


@pytest.mark.asyncio
async def test_login_success(mock_cognito):
    mock_cognito.post("/").mock(
        return_value=httpx.Response(200, json={
            "AuthenticationResult": {
                "AccessToken": "access-123",
                "RefreshToken": "refresh-456",
                "ExpiresIn": 86400,
                "TokenType": "Bearer",
            },
        })
    )
    auth = CognitoAuth()
    before = time.time()
    tokens = await auth.login("user@test.com", "password123")
    assert tokens.access_token == "access-123"
    assert tokens.refresh_token == "refresh-456"
    assert tokens.expires_at >= before + 86400


@pytest.mark.asyncio
async def test_login_bad_credentials(mock_cognito):
    mock_cognito.post("/").mock(
        return_value=httpx.Response(400, json={
            "__type": "NotAuthorizedException",
            "message": "Incorrect username or password.",
        })
    )
    auth = CognitoAuth()
    with pytest.raises(WhoopAuthError, match="invalid credentials"):
        await auth.login("bad@test.com", "wrong")


@pytest.mark.asyncio
async def test_refresh_success(mock_cognito):
    mock_cognito.post("/").mock(
        return_value=httpx.Response(200, json={
            "AuthenticationResult": {
                "AccessToken": "new-access-789",
                "ExpiresIn": 86400,
                "TokenType": "Bearer",
            },
        })
    )
    auth = CognitoAuth()
    tokens = await auth.refresh("refresh-456")
    assert tokens.access_token == "new-access-789"
    assert tokens.refresh_token == "refresh-456"


@pytest.mark.asyncio
async def test_refresh_expired(mock_cognito):
    mock_cognito.post("/").mock(
        return_value=httpx.Response(400, json={
            "__type": "NotAuthorizedException",
            "message": "Refresh Token has expired.",
        })
    )
    auth = CognitoAuth()
    with pytest.raises(WhoopAuthExpiredError):
        await auth.refresh("old-refresh")


@pytest.mark.asyncio
async def test_login_sends_correct_payload(mock_cognito):
    route = mock_cognito.post("/").mock(
        return_value=httpx.Response(200, json={
            "AuthenticationResult": {
                "AccessToken": "a", "RefreshToken": "r", "ExpiresIn": 3600,
            },
        })
    )
    auth = CognitoAuth()
    await auth.login("user@test.com", "pass123")
    request = route.calls.last.request
    body = json.loads(request.content)
    assert body["AuthFlow"] == "USER_PASSWORD_AUTH"
    assert body["ClientId"] == DEFAULT_CLIENT_ID
    assert body["AuthParameters"]["USERNAME"] == "user@test.com"
    assert body["AuthParameters"]["PASSWORD"] == "pass123"


@pytest.mark.asyncio
async def test_custom_client_id(mock_cognito):
    route = mock_cognito.post("/").mock(
        return_value=httpx.Response(200, json={
            "AuthenticationResult": {
                "AccessToken": "a", "RefreshToken": "r", "ExpiresIn": 3600,
            },
        })
    )
    auth = CognitoAuth(client_id="custom-id")
    await auth.login("user@test.com", "pass")
    body = json.loads(route.calls.last.request.content)
    assert body["ClientId"] == "custom-id"


def test_token_set_fields():
    ts = TokenSet(access_token="a", refresh_token="r", expires_at=1000.0)
    assert ts.access_token == "a"
    assert ts.refresh_token == "r"
    assert ts.expires_at == 1000.0


@pytest.mark.asyncio
async def test_expires_at_computed_from_time(mock_cognito):
    mock_cognito.post("/").mock(
        return_value=httpx.Response(200, json={
            "AuthenticationResult": {
                "AccessToken": "a", "RefreshToken": "r", "ExpiresIn": 7200,
            },
        })
    )
    auth = CognitoAuth()
    before = time.time()
    tokens = await auth.login("u@t.com", "p")
    after = time.time()
    assert before + 7200 <= tokens.expires_at <= after + 7200
