from __future__ import annotations
import warnings
import httpx
from whoop.exceptions import WhoopAuthError

OFFICIAL_BASE = "https://api.prod.whoop.com"
LEGACY_BASE = "https://api-7.whoop.com"


class WhoopAuth:
    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token: str | None = None
        self.refresh_token: str | None = None

    @property
    def headers(self) -> dict:
        if not self.access_token:
            raise WhoopAuthError("not authenticated")
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def exchange_code(self, code: str, redirect_uri: str) -> str:
        async with httpx.AsyncClient(base_url=OFFICIAL_BASE) as client:
            resp = await client.post(
                "/oauth/oauth2/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
        if resp.status_code != 200:
            raise WhoopAuthError(f"token exchange failed: {resp.text}", status_code=resp.status_code)
        data = resp.json()
        self.access_token = data["access_token"]
        self.refresh_token = data.get("refresh_token")
        return self.access_token

    async def refresh(self) -> str:
        if not self.refresh_token:
            raise WhoopAuthError("no refresh token available")
        async with httpx.AsyncClient(base_url=OFFICIAL_BASE) as client:
            resp = await client.post(
                "/oauth/oauth2/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
        if resp.status_code != 200:
            raise WhoopAuthError(f"token refresh failed: {resp.text}", status_code=resp.status_code)
        data = resp.json()
        self.access_token = data["access_token"]
        self.refresh_token = data.get("refresh_token")
        return self.access_token

    async def login_password(self, username: str, password: str, client_id: str = "whoop-recruiting-prod") -> str:
        warnings.warn(
            "login_password() uses a legacy endpoint that Whoop has deprecated. "
            "Use OAuth2 via exchange_code() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        async with httpx.AsyncClient(base_url=LEGACY_BASE) as client:
            resp = await client.post(
                "/oauth/token",
                data={
                    "grant_type": "password",
                    "username": username,
                    "password": password,
                    "client_id": client_id,
                },
            )
        if resp.status_code != 200:
            raise WhoopAuthError(f"password auth failed: {resp.text}", status_code=resp.status_code)
        data = resp.json()
        self.access_token = data["access_token"]
        self.refresh_token = data.get("refresh_token")
        return self.access_token
