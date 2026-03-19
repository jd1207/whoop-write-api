from __future__ import annotations
import time
from dataclasses import dataclass
import httpx
from whoop.exceptions import WhoopAuthError, WhoopAuthExpiredError

# whoop's auth proxy handles SECRET_HASH server-side so callers
# don't need the cognito client secret
AUTH_URL = "https://api.prod.whoop.com/auth-service/v3/whoop"
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
                AUTH_URL, headers=COGNITO_HEADERS, json=payload,
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
