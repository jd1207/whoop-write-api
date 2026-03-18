# Cognito Auth & Context Manager

**Date:** 2026-03-18
**Status:** Draft
**Version:** v0.4.0

## Problem

The write API requires Cognito auth tokens. Currently, tokens must be captured manually via mitmproxy — unsustainable for production use. Token lifetime is determined by the `ExpiresIn` field in the Cognito response (Whoop has configured ~24 hours based on observed tokens, but the library relies on the actual response value, not an assumption). The library also creates a new HTTP connection per request, wasting resources for apps that make multiple calls.

## Goals

1. Programmatic Cognito login via email/password (no mitmproxy, no boto3)
2. Automatic token refresh before expiry with caller-provided persistence callback
3. Terminal auth failure detection (`WhoopAuthExpiredError`) so callers can prompt re-auth
4. `async with` context manager for connection pooling
5. Zero breaking changes — existing `WhoopClient(token="...")` works unchanged

## Non-Goals

- Credential storage (caller's responsibility)
- Background refresh threads/timers
- JWT parsing (use Cognito's `ExpiresIn` response)
- Concurrent access locking (note: two coroutines refreshing simultaneously is harmless but the callback fires twice — document this)
- MFA support (Whoop doesn't require it currently)

## Design

### 1. CognitoAuth

**New file: `src/whoop/cognito.py`**

```python
COGNITO_URL = "https://cognito-idp.us-west-2.amazonaws.com/"
DEFAULT_CLIENT_ID = "37365lrcda1js3fapqfe2n40eh"
# sourced from whoop iOS app v5.43.0, march 2026
# override via CognitoAuth(client_id="...") if whoop rotates this


@dataclass
class TokenSet:
    access_token: str
    refresh_token: str
    expires_at: float  # unix timestamp


class CognitoAuth:
    def __init__(self, client_id: str = DEFAULT_CLIENT_ID):
        self.client_id = client_id

    async def login(self, email: str, password: str) -> TokenSet:
        """authenticate with whoop via cognito USER_PASSWORD_AUTH"""

    async def refresh(self, refresh_token: str) -> TokenSet:
        """refresh an expired access token"""
```

Request format (raw HTTP, no SDK):
```json
{
    "AuthFlow": "USER_PASSWORD_AUTH",
    "ClientId": "37365lrcda1js3fapqfe2n40eh",
    "AuthParameters": {
        "USERNAME": "user@example.com",
        "PASSWORD": "their-password"
    }
}
```

Headers:
```
Content-Type: application/x-amz-json-1.1
X-Amz-Target: AWSCognitoIdentityProviderService.InitiateAuth
```

Response contains `AuthenticationResult.AccessToken`, `AuthenticationResult.RefreshToken`, `AuthenticationResult.ExpiresIn`.

`expires_at` is computed as `time.time() + ExpiresIn` at the moment the response is received.

For refresh, the flow is identical but with `AuthFlow: REFRESH_TOKEN_AUTH` and `AuthParameters: {"REFRESH_TOKEN": "..."}`. Cognito returns a new access token but reuses the same refresh token.

Error handling:
- `NotAuthorizedException` from Cognito → primary error for both bad credentials AND non-existent users (Cognito pools typically have "Prevent user existence errors" enabled, so `UserNotFoundException` is rarely seen). During login, raise `WhoopAuthError("invalid credentials")`. During refresh, raise `WhoopAuthExpiredError("refresh token expired")`.
- `UserNotFoundException` → defensive handling, raise `WhoopAuthError` (may never occur depending on Whoop's Cognito config)
- Network errors → raise `WhoopAuthError` with context

### 2. Token Provider Pattern

**Critical design decision:** Read/write APIs must NOT store a static token string. Instead, they reference a shared mutable token holder so that token refresh propagates automatically.

```python
class TokenHolder:
    """shared mutable token reference used by read/write APIs"""
    def __init__(self, token: str):
        self.token = token
```

`WhoopClient` creates one `TokenHolder` and passes it to both `WhoopReadAPI` and `WhoopWriteAPI`. When `_ensure_token()` refreshes, it updates `self._token_holder.token` — the change propagates to both APIs immediately since they share the same object reference.

Read/write APIs change their `_headers` property:
```python
@property
def _headers(self) -> dict:
    return {
        "Authorization": f"Bearer {self._token_holder.token}",
        ...
    }
```

### 3. WhoopClient Changes

**Modified: `src/whoop/client.py`**

New constructor signature (uses `TokenSet` to avoid parameter proliferation):

```python
class WhoopClient:
    def __init__(
        self,
        token: str | None = None,
        auth: WhoopAuth | None = None,
        token_set: TokenSet | None = None,
        on_token_refresh: Callable[[TokenSet], Awaitable[None]] | None = None,
        timezone: str = "America/Los_Angeles",
    ):
```

Three modes:
1. **Simple token** (`token="..."`) — no refresh, works as today
2. **Developer OAuth** (`auth=WhoopAuth(...)`) — no refresh, works as today
3. **Cognito** (`token_set=TokenSet(...)`) — auto-refresh enabled

**`on_token_refresh` callback contract:**
- Signature: `async def callback(token_set: TokenSet) -> None`
- Called after every successful refresh
- Must be async (caller typically does I/O like DB writes)
- Exceptions from the callback propagate — the library does not swallow them
- If `on_token_refresh` is None, refresh still happens but new tokens aren't persisted

**Token refresh logic** (`_ensure_token()`):
- Called before every request
- If no `_refresh_token` or no `_expires_at`, skip (simple token mode)
- If current time > `expires_at - 300` (5 minute buffer), call `CognitoAuth.refresh()`
- On success, update `self._token_holder.token`, update `self._expires_at`, call `on_token_refresh` callback with new `TokenSet`
- On `NotAuthorizedException` from Cognito, raise `WhoopAuthExpiredError`
- On network error: if token is still within its validity window (not yet past `expires_at`), proceed with current token. If token is already past `expires_at`, raise `WhoopAuthError("token expired and refresh failed: <error>")`

**401 handling:** If any API request returns 401, `WhoopClient` attempts one token refresh + retry. If the retry also fails with 401, raise `WhoopAuthExpiredError`. This handles the case where the token expires between the `_ensure_token()` check and the actual request (race condition with very short-lived tokens).

**Context manager** (`__aenter__` / `__aexit__`):
- `__aenter__`: create shared `httpx.AsyncClient(base_url=BASE_URL)`, store on `self._shared_client`. Also call `_ensure_token()` to surface auth problems immediately.
- `__aexit__`: close the shared client, set `self._shared_client = None`
- Works with all three auth modes (simple token benefits from connection pooling too)

### 4. Read/Write API Changes

**Modified: `src/whoop/read.py`, `src/whoop/write.py`, `src/whoop/write_journal.py`**

All HTTP methods (`_get`, `_post`, `_put`, `_delete`) accept an optional `client` parameter:

```python
async def _post(self, path: str, json: dict, client: httpx.AsyncClient | None = None) -> dict:
    if client:
        resp = await client.post(path, headers=self._headers, json=json)
    else:
        async with httpx.AsyncClient(base_url=BASE_URL) as c:
            resp = await c.post(path, headers=self._headers, json=json)
    # ... error handling unchanged
```

`WhoopClient` wraps all API calls to:
1. Call `_ensure_token()` first
2. Pass `self._shared_client` if in context manager mode
3. Handle 401 retry logic

The `write_journal.py` methods (`log_journal`, `get_journal_behaviors`, `update_weight`, `set_alarm`) are called via the `WhoopWriteAPI` instance which shares the same `TokenHolder` and receives the same shared client — no special handling needed.

### 5. New Exception

**Modified: `src/whoop/exceptions.py`**

```python
class WhoopAuthExpiredError(WhoopAuthError):
    """refresh token is no longer valid — re-authentication required"""
    pass
```

### 6. Exports

**Modified: `src/whoop/__init__.py`**

Add: `CognitoAuth`, `TokenSet`, `WhoopAuthExpiredError`

## Usage Examples

### SpotMe: First-time setup

```python
from whoop import CognitoAuth

auth = CognitoAuth()
tokens = await auth.login("user@example.com", "password")

# spotme stores these in sqlite
db.save_whoop_tokens(tokens)
```

### SpotMe: Daily sync (unattended)

```python
from whoop import WhoopClient, TokenSet, WhoopAuthExpiredError

saved = db.load_whoop_tokens()
token_set = TokenSet(
    access_token=saved.access_token,
    refresh_token=saved.refresh_token,
    expires_at=saved.expires_at,
)

async def persist_tokens(new_tokens: TokenSet) -> None:
    db.save_whoop_tokens(new_tokens)

async with WhoopClient(
    token_set=token_set,
    on_token_refresh=persist_tokens,
) as client:
    try:
        recovery = await client.get_recovery()
        await client.create_activity("sauna", start, end)
    except WhoopAuthExpiredError:
        notify_user("whoop needs re-authentication")
```

### Simple script (backwards compat)

```python
from whoop import WhoopClient

client = WhoopClient(token="bearer-token-here")
recovery = await client.get_recovery()
```

### Context manager without Cognito (connection pooling only)

```python
async with WhoopClient(token="bearer-token") as client:
    recovery = await client.get_recovery()
    sleep = await client.get_sleep()  # reuses connection
```

## Testing Strategy

### cognito.py tests
- `login()` success → returns TokenSet with all fields
- `login()` bad credentials (NotAuthorizedException) → raises WhoopAuthError
- `login()` user not found (defensive) → raises WhoopAuthError
- `refresh()` success → returns new TokenSet with updated access_token
- `refresh()` expired refresh token (NotAuthorizedException) → raises WhoopAuthExpiredError
- `refresh()` preserves refresh_token in returned TokenSet
- `expires_at` computed from response time + ExpiresIn
- Custom `client_id` passed through to request

### client.py tests
- Context manager creates and closes shared httpx client
- Context manager calls `_ensure_token()` on `__aenter__`
- Context manager mode reuses connection (shared client passed to APIs)
- Context manager works with simple token mode (no refresh, connection pooling only)
- Non-context-manager mode still works (per-request clients)
- `_ensure_token()` refreshes when within 5-minute buffer
- `_ensure_token()` calls `on_token_refresh` callback with TokenSet after refresh
- `_ensure_token()` works when `on_token_refresh` is None
- `_ensure_token()` skips when no refresh_token (simple token mode)
- `_ensure_token()` raises `WhoopAuthExpiredError` on terminal failure
- `_ensure_token()` proceeds with current token on network error when token not yet expired
- `_ensure_token()` raises `WhoopAuthError` on network error when token already expired
- 401 response triggers one refresh + retry
- 401 after retry raises `WhoopAuthExpiredError`
- Token refresh propagates to read and write APIs (shared TokenHolder)
- Backwards compat: `WhoopClient(token="...")` works unchanged
- Backwards compat: `WhoopClient(auth=WhoopAuth(...))` works unchanged

## File Changes

| File | Action | Lines (est.) |
|------|--------|-------------|
| `src/whoop/cognito.py` | new | ~80 |
| `src/whoop/client.py` | edit | ~60 changed |
| `src/whoop/read.py` | edit | ~15 changed |
| `src/whoop/write.py` | edit | ~20 changed |
| `src/whoop/write_journal.py` | edit | ~10 changed |
| `src/whoop/exceptions.py` | edit | ~5 added |
| `src/whoop/__init__.py` | edit | ~3 added |
| `README.md` | edit | ~40 changed |
| `CHANGELOG.md` | edit | ~10 added |
| `tests/test_cognito.py` | new | ~100 |
| `tests/test_client_auth.py` | new | ~150 |
