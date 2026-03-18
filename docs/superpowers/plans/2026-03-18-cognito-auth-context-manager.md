# Cognito Auth & Context Manager Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add programmatic Cognito login with auto-refresh and `async with` context manager for connection pooling.

**Architecture:** New `CognitoAuth` class talks directly to AWS Cognito via raw HTTP (no boto3). `WhoopClient` gains a `TokenHolder` pattern so token refresh propagates to read/write APIs automatically. Context manager creates a shared `httpx.AsyncClient` for connection reuse. All existing API (`WhoopClient(token="...")`) works unchanged.

**Tech Stack:** Python 3.11+, httpx, zoneinfo (stdlib), pytest + pytest-asyncio + respx

**Spec:** `docs/superpowers/specs/2026-03-18-cognito-auth-context-manager-design.md`

---

## Chunk 1: Foundation (exceptions, cognito, token holder)

### Task 1: Add WhoopAuthExpiredError

**Files:**
- Modify: `src/whoop/exceptions.py`
- Create: `tests/test_exceptions_v2.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_exceptions_v2.py
from whoop.exceptions import WhoopAuthExpiredError, WhoopAuthError


def test_auth_expired_is_subclass():
    assert issubclass(WhoopAuthExpiredError, WhoopAuthError)


def test_auth_expired_error():
    err = WhoopAuthExpiredError("refresh token expired")
    assert str(err) == "refresh token expired"
    assert err.status_code is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/deck/whoop-write-api && venv/bin/python -m pytest tests/test_exceptions_v2.py -v`
Expected: FAIL with `ImportError: cannot import name 'WhoopAuthExpiredError'`

- [ ] **Step 3: Add WhoopAuthExpiredError to exceptions.py**

Append to `src/whoop/exceptions.py`:

```python
class WhoopAuthExpiredError(WhoopAuthError):
    """refresh token is no longer valid — re-authentication required"""
    pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/deck/whoop-write-api && venv/bin/python -m pytest tests/test_exceptions_v2.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/whoop/exceptions.py tests/test_exceptions_v2.py
git commit -m "feat: add WhoopAuthExpiredError for terminal auth failures"
```

### Task 2: Create CognitoAuth

**Files:**
- Create: `src/whoop/cognito.py`
- Create: `tests/test_cognito.py`
- Modify: `tests/conftest.py` (add cognito mock fixture)

- [ ] **Step 1: Add cognito mock fixture to conftest.py**

Add to `tests/conftest.py`:

```python
@pytest.fixture
def mock_cognito():
    with respx.mock(base_url="https://cognito-idp.us-west-2.amazonaws.com") as respx_mock:
        yield respx_mock
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_cognito.py
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
    import json
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
    import json
    body = json.loads(route.calls.last.request.content)
    assert body["ClientId"] == "custom-id"


def test_token_set_fields():
    ts = TokenSet(access_token="a", refresh_token="r", expires_at=1000.0)
    assert ts.access_token == "a"
    assert ts.refresh_token == "r"
    assert ts.expires_at == 1000.0
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /home/deck/whoop-write-api && venv/bin/python -m pytest tests/test_cognito.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Implement cognito.py**

```python
# src/whoop/cognito.py
from __future__ import annotations
import time
from dataclasses import dataclass
import httpx
from whoop.exceptions import WhoopAuthError, WhoopAuthExpiredError

COGNITO_URL = "https://cognito-idp.us-west-2.amazonaws.com/"
DEFAULT_CLIENT_ID = "37365lrcda1js3fapqfe2n40eh"

COGNITO_HEADERS = {
    "Content-Type": "application/x-amz-json-1.1",
    "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
}


@dataclass
class TokenSet:
    access_token: str
    refresh_token: str
    expires_at: float


class CognitoAuth:
    """authenticate with whoop via AWS cognito (same as mobile app)"""

    def __init__(self, client_id: str = DEFAULT_CLIENT_ID):
        self.client_id = client_id

    async def _initiate_auth(self, auth_flow: str, auth_params: dict) -> dict:
        payload = {
            "AuthFlow": auth_flow,
            "ClientId": self.client_id,
            "AuthParameters": auth_params,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                COGNITO_URL, headers=COGNITO_HEADERS, json=payload,
            )
        if resp.status_code != 200:
            data = resp.json()
            error_type = data.get("__type", "")
            message = data.get("message", resp.text)
            if "NotAuthorizedException" in error_type:
                if auth_flow == "REFRESH_TOKEN_AUTH":
                    raise WhoopAuthExpiredError(
                        f"refresh token expired: {message}",
                    )
                raise WhoopAuthError(
                    f"invalid credentials: {message}",
                )
            raise WhoopAuthError(
                f"cognito auth failed: {message}",
                status_code=resp.status_code,
                response_body=resp.text,
            )
        return resp.json()

    async def login(self, email: str, password: str) -> TokenSet:
        """authenticate with email and password"""
        data = await self._initiate_auth(
            "USER_PASSWORD_AUTH",
            {"USERNAME": email, "PASSWORD": password},
        )
        result = data["AuthenticationResult"]
        return TokenSet(
            access_token=result["AccessToken"],
            refresh_token=result["RefreshToken"],
            expires_at=time.time() + result["ExpiresIn"],
        )

    async def refresh(self, refresh_token: str) -> TokenSet:
        """refresh an expired access token"""
        data = await self._initiate_auth(
            "REFRESH_TOKEN_AUTH",
            {"REFRESH_TOKEN": refresh_token},
        )
        result = data["AuthenticationResult"]
        return TokenSet(
            access_token=result["AccessToken"],
            refresh_token=refresh_token,
            expires_at=time.time() + result["ExpiresIn"],
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/deck/whoop-write-api && venv/bin/python -m pytest tests/test_cognito.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/whoop/cognito.py tests/test_cognito.py tests/conftest.py
git commit -m "feat: add CognitoAuth for programmatic whoop login"
```

### Task 3: Create TokenHolder

**Files:**
- Create: `src/whoop/token_holder.py`

- [ ] **Step 1: Create token_holder.py**

```python
# src/whoop/token_holder.py
from __future__ import annotations


class TokenHolder:
    """shared mutable token reference used by read/write APIs"""

    def __init__(self, token: str):
        self.token = token
```

- [ ] **Step 2: Commit**

```bash
git add src/whoop/token_holder.py
git commit -m "feat: add TokenHolder for shared mutable token reference"
```

---

## Chunk 2: Refactor Read/Write APIs to use TokenHolder and shared client

### Task 4: Refactor WhoopReadAPI

**Files:**
- Modify: `src/whoop/read.py`
- Modify: `tests/test_read.py` (verify no regressions)

- [ ] **Step 1: Update WhoopReadAPI to accept TokenHolder and optional shared client**

Replace `src/whoop/read.py`:

```python
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
```

- [ ] **Step 2: Run existing read tests to verify no regressions**

Run: `cd /home/deck/whoop-write-api && venv/bin/python -m pytest tests/test_read.py tests/test_client.py -v`
Expected: all PASS (existing tests pass `token` as string, which still works)

- [ ] **Step 3: Commit**

```bash
git add src/whoop/read.py
git commit -m "refactor: WhoopReadAPI uses TokenHolder and accepts shared client"
```

### Task 5: Refactor WhoopWriteAPI

**Files:**
- Modify: `src/whoop/write.py`

- [ ] **Step 1: Update WhoopWriteAPI to accept TokenHolder and optional shared client**

Changes to make in `src/whoop/write.py`:
1. Import `TokenHolder`
2. Change `__init__` to accept `str | TokenHolder` for token
3. Add `token` property/setter like ReadAPI
4. Update `_headers` to read from `_token_holder`
5. Add `client` param to `_post`, `_get`, `_put`, `_delete`
6. All methods that call these pass `client=None` (default — backward compat)

Key changes to `__init__`:
```python
def __init__(self, token: str | TokenHolder = "", timezone: str = "America/Los_Angeles"):
    if isinstance(token, TokenHolder):
        self._token_holder = token
    else:
        self._token_holder = TokenHolder(token)
    self.timezone = timezone
    # ... rest unchanged
```

Update `_headers`:
```python
@property
def _headers(self) -> dict:
    return {
        "Authorization": f"Bearer {self._token_holder.token}",
        "Content-Type": "application/json",
        "x-whoop-time-zone": self.timezone,
        **WRITE_HEADERS_EXTRA,
    }
```

Add `client` parameter to all HTTP methods:
```python
async def _post(self, path: str, json: dict, client: httpx.AsyncClient | None = None) -> dict:
    if client:
        resp = await client.post(path, headers=self._headers, json=json)
    else:
        async with httpx.AsyncClient(base_url=BASE_URL) as c:
            resp = await c.post(path, headers=self._headers, json=json)
    # ... error handling unchanged
```

Same pattern for `_get`, `_put`, `_delete`.

Add `token` property/setter:
```python
@property
def token(self) -> str:
    return self._token_holder.token

@token.setter
def token(self, value: str) -> None:
    self._token_holder.token = value
```

- [ ] **Step 2: Run existing write tests to verify no regressions**

Run: `cd /home/deck/whoop-write-api && venv/bin/python -m pytest tests/test_write.py tests/test_write_v2.py tests/test_client.py tests/test_client_v2.py -v`
Expected: all PASS

- [ ] **Step 3: Commit**

```bash
git add src/whoop/write.py
git commit -m "refactor: WhoopWriteAPI uses TokenHolder and accepts shared client"
```

---

## Chunk 3: WhoopClient with auto-refresh and context manager

### Task 6: Rewrite WhoopClient

**Files:**
- Modify: `src/whoop/client.py`
- Create: `tests/test_client_auth.py`

- [ ] **Step 1: Write failing tests for new client features**

```python
# tests/test_client_auth.py
import time
import pytest
import httpx
from unittest.mock import AsyncMock
from whoop.client import WhoopClient
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


@pytest.mark.asyncio
async def test_context_manager(mock_api, fake_token):
    async with WhoopClient(token=fake_token) as client:
        assert client._shared_client is not None
    assert client._shared_client is None


@pytest.mark.asyncio
async def test_ensure_token_skips_simple_mode(fake_token):
    client = WhoopClient(token=fake_token)
    await client._ensure_token()  # should not raise


@pytest.mark.asyncio
async def test_ensure_token_refreshes_when_expiring(mock_cognito):
    ts = TokenSet(
        access_token="old-access",
        refresh_token="refresh-123",
        expires_at=time.time() - 100,  # already expired
    )
    mock_cognito.post("/").mock(
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
async def test_ensure_token_calls_callback(mock_cognito):
    ts = TokenSet(
        access_token="old",
        refresh_token="refresh-123",
        expires_at=time.time() - 100,
    )
    mock_cognito.post("/").mock(
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
async def test_ensure_token_no_callback_ok(mock_cognito):
    ts = TokenSet(
        access_token="old",
        refresh_token="refresh-123",
        expires_at=time.time() - 100,
    )
    mock_cognito.post("/").mock(
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
async def test_ensure_token_expired_refresh_raises(mock_cognito):
    ts = TokenSet(
        access_token="old",
        refresh_token="dead-refresh",
        expires_at=time.time() - 100,
    )
    mock_cognito.post("/").mock(
        return_value=httpx.Response(400, json={
            "__type": "NotAuthorizedException",
            "message": "Refresh Token has expired.",
        })
    )
    client = WhoopClient(token_set=ts)
    with pytest.raises(WhoopAuthExpiredError):
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
    # simulate a refresh
    client._token_holder.token = "updated"
    assert client._read.token == "updated"
    assert client._write.token == "updated"


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/deck/whoop-write-api && venv/bin/python -m pytest tests/test_client_auth.py -v`
Expected: multiple failures

- [ ] **Step 3: Rewrite client.py**

```python
# src/whoop/client.py
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
from whoop.exceptions import WhoopAuthExpiredError
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
        if not self._refresh_token or not self._expires_at:
            return
        if time.time() < self._expires_at - REFRESH_BUFFER_SECONDS:
            return
        new_tokens = await self._cognito.refresh(self._refresh_token)
        self._token_holder.token = new_tokens.access_token
        self._expires_at = new_tokens.expires_at
        self._refresh_token = new_tokens.refresh_token
        if self._on_token_refresh:
            await self._on_token_refresh(new_tokens)

    async def __aenter__(self) -> WhoopClient:
        await self._ensure_token()
        self._shared_client = httpx.AsyncClient(base_url=BASE_URL)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._shared_client:
            await self._shared_client.aclose()
            self._shared_client = None

    async def get_recovery(self, start: str | None = None, end: str | None = None) -> list[Recovery]:
        await self._ensure_token()
        return await self._read.get_recovery(start, end, client=self._shared_client)

    async def get_sleep(self, start: str | None = None, end: str | None = None) -> list[Sleep]:
        await self._ensure_token()
        return await self._read.get_sleep(start, end, client=self._shared_client)

    async def get_workouts(self, start: str | None = None, end: str | None = None) -> list[Workout]:
        await self._ensure_token()
        return await self._read.get_workouts(start, end, client=self._shared_client)

    async def get_cycles(self, start: str | None = None, end: str | None = None) -> list[Cycle]:
        await self._ensure_token()
        return await self._read.get_cycles(start, end, client=self._shared_client)

    async def get_body_measurement(self) -> BodyMeasurement:
        await self._ensure_token()
        return await self._read.get_body_measurement(client=self._shared_client)

    async def log_workout(self, workout: WorkoutWrite) -> WorkoutResult:
        await self._ensure_token()
        return await self._write.log_workout(workout)

    async def get_sport_types(self) -> list[SportTypeInfo]:
        await self._ensure_token()
        return await self._write.get_sport_types()

    async def get_exercises(self) -> ExerciseCatalog:
        await self._ensure_token()
        return await self._write.get_exercises()

    async def create_activity(self, activity_type: str, start: str, end: str) -> ActivityResult:
        await self._ensure_token()
        return await self._write.create_activity(activity_type, start, end)

    async def delete_activity(self, activity_id: str, is_recovery: bool = False) -> None:
        await self._ensure_token()
        return await self._write.delete_activity(activity_id, is_recovery)

    async def link_exercises_detailed(self, activity_id: str, exercises: list[DetailedExercise]) -> dict:
        await self._ensure_token()
        return await self._write.link_exercises_detailed(activity_id, exercises)

    async def log_journal(self, date: str, inputs: list[JournalInput], notes: str = "") -> None:
        await self._ensure_token()
        return await self._write.log_journal(date, inputs, notes)

    async def get_journal_behaviors(self, date: str) -> list[JournalBehavior]:
        await self._ensure_token()
        return await self._write.get_journal_behaviors(date)

    async def update_weight(self, weight_kg: float) -> bool:
        await self._ensure_token()
        return await self._write.update_weight(weight_kg)

    async def set_alarm(self, time: str, enabled: bool = True, timezone_offset: str = "-0400") -> dict:
        await self._ensure_token()
        return await self._write.set_alarm(time, enabled, timezone_offset)
```

- [ ] **Step 4: Run all tests**

Run: `cd /home/deck/whoop-write-api && venv/bin/python -m pytest -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/whoop/client.py tests/test_client_auth.py
git commit -m "feat: WhoopClient with cognito auto-refresh and async with context manager

- TokenSet constructor for cognito auth
- _ensure_token() refreshes before each request
- on_token_refresh callback for token persistence
- async with creates shared httpx client
- All existing API unchanged (backwards compat)"
```

---

## Chunk 4: Exports, docs, cleanup

### Task 7: Update exports

**Files:**
- Modify: `src/whoop/__init__.py`

- [ ] **Step 1: Update __init__.py**

Add `CognitoAuth`, `TokenSet`, `WhoopAuthExpiredError` to imports and `__all__`.

```python
from whoop.cognito import CognitoAuth, TokenSet
from whoop.exceptions import WhoopAuthError, WhoopAPIError, WhoopRateLimitError, WhoopAuthExpiredError
```

Add to `__all__`: `"CognitoAuth"`, `"TokenSet"`, `"WhoopAuthExpiredError"`

- [ ] **Step 2: Verify imports work**

Run: `cd /home/deck/whoop-write-api && venv/bin/python -c "from whoop import CognitoAuth, TokenSet, WhoopAuthExpiredError; print('ok')"`

- [ ] **Step 3: Run full test suite**

Run: `cd /home/deck/whoop-write-api && venv/bin/python -m pytest -v`
Expected: all PASS

- [ ] **Step 4: Commit**

```bash
git add src/whoop/__init__.py
git commit -m "feat: export CognitoAuth, TokenSet, WhoopAuthExpiredError"
```

### Task 8: Update README and CHANGELOG

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `pyproject.toml` (bump version)

- [ ] **Step 1: Update README authentication section**

Add Cognito auth examples and `async with` usage to the Authentication section and Write API section. Update roadmap to remove these items.

- [ ] **Step 2: Update CHANGELOG**

Add v0.4.0 section with:
- Cognito auth (`CognitoAuth.login()`, `CognitoAuth.refresh()`)
- Auto token refresh with `on_token_refresh` callback
- `WhoopAuthExpiredError` for terminal auth failures
- `async with` context manager for connection pooling
- `TokenHolder` pattern for automatic token propagation
- `TokenSet` dataclass

- [ ] **Step 3: Bump version to 0.4.0 in pyproject.toml**

- [ ] **Step 4: Run full test suite one final time**

Run: `cd /home/deck/whoop-write-api && venv/bin/python -m pytest -v`

- [ ] **Step 5: Commit**

```bash
git add README.md CHANGELOG.md pyproject.toml
git commit -m "docs: update README and CHANGELOG for v0.4.0 cognito auth"
```
