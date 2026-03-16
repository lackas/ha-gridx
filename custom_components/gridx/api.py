"""Async API client for gridX energy management."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import aiohttp

from .const import (
    API_GATEWAYS_URL,
    API_LIVE_URL,
    AUTH0_AUDIENCE,
    AUTH0_CLIENT_ID,
    AUTH0_GRANT_TYPE,
    AUTH0_REALM,
    AUTH0_SCOPE,
    AUTH0_TOKEN_URL,
    AUTH_COOLDOWN_SECONDS,
)
from .models import GridxSystemData, parse_live_data


class GridxError(Exception):
    """Base exception for gridX API errors."""


class GridxAuthenticationError(GridxError):
    """Authentication failed (bad credentials, expired, 401/403)."""


class GridxConnectionError(GridxError):
    """Connection failed (timeout, DNS, refused)."""


class GridxApiError(GridxError):
    """Unexpected API error (5xx, bad response)."""


class GridxApi:
    """Async client for the gridX API."""

    def __init__(
        self, session: aiohttp.ClientSession, email: str, password: str
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._email = email
        self._password = password
        self._token: dict[str, Any] | None = None
        self._last_auth_attempt: float = 0  # monotonic timestamp

    async def authenticate(self) -> None:
        """Authenticate with Auth0 and store the token."""
        now = time.monotonic()
        if now - self._last_auth_attempt < AUTH_COOLDOWN_SECONDS:
            # Cooldown: skip hitting Auth0 again
            return

        self._last_auth_attempt = now

        payload = {
            "grant_type": AUTH0_GRANT_TYPE,
            "username": self._email,
            "password": self._password,
            "client_id": AUTH0_CLIENT_ID,
            "audience": AUTH0_AUDIENCE,
            "realm": AUTH0_REALM,
            "scope": AUTH0_SCOPE,
        }

        try:
            async with self._session.post(
                AUTH0_TOKEN_URL, json=payload
            ) as resp:
                if resp.status in (401, 403):
                    raise GridxAuthenticationError(
                        f"Authentication failed: HTTP {resp.status}"
                    )
                resp.raise_for_status()
                data = await resp.json()
        except aiohttp.ClientResponseError as err:
            if err.status in (401, 403):
                raise GridxAuthenticationError(
                    f"Authentication failed: HTTP {err.status}"
                ) from err
            raise GridxApiError(f"Auth API error: {err}") from err
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise GridxConnectionError(f"Connection error during auth: {err}") from err

        expires_in = data.get("expires_in", 3600)
        self._token = {
            "access_token": data.get("access_token"),
            "id_token": data.get("id_token"),
            "refresh_token": data.get("refresh_token"),
            "expires_at": time.monotonic() + expires_in,
        }

    async def _refresh_token(self) -> None:
        """Refresh the access token using the stored refresh token."""
        if not self._token or not self._token.get("refresh_token"):
            raise GridxAuthenticationError("No refresh token available")

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self._token["refresh_token"],
            "client_id": AUTH0_CLIENT_ID,
        }

        try:
            async with self._session.post(
                AUTH0_TOKEN_URL, json=payload
            ) as resp:
                if resp.status in (401, 403):
                    raise GridxAuthenticationError(
                        f"Token refresh failed: HTTP {resp.status}"
                    )
                resp.raise_for_status()
                data = await resp.json()
        except aiohttp.ClientResponseError as err:
            if err.status in (401, 403):
                raise GridxAuthenticationError(
                    f"Token refresh failed: HTTP {err.status}"
                ) from err
            raise GridxApiError(f"Token refresh API error: {err}") from err
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise GridxConnectionError(
                f"Connection error during token refresh: {err}"
            ) from err

        expires_in = data.get("expires_in", 3600)
        self._token = {
            "access_token": data.get("access_token"),
            "id_token": data.get("id_token"),
            "refresh_token": data.get(
                "refresh_token", self._token.get("refresh_token")
            ),
            "expires_at": time.monotonic() + expires_in,
        }

    async def _ensure_token(self) -> None:
        """Ensure we have a valid, non-expired token."""
        if self._token is None:
            await self.authenticate()
            return

        # If token expires within 60 seconds, try to refresh
        if self._token["expires_at"] - time.monotonic() < 60:
            try:
                await self._refresh_token()
            except GridxError:
                # Fall back to full re-auth (bypass cooldown by resetting timestamp)
                self._last_auth_attempt = 0
                await self.authenticate()

    async def _get(self, url: str) -> Any:
        """Perform an authenticated GET request."""
        await self._ensure_token()

        headers = {"Authorization": f"Bearer {self._token['id_token']}"}

        try:
            async with self._session.get(url, headers=headers) as resp:
                if resp.status in (401, 403):
                    raise GridxAuthenticationError(
                        f"API request unauthorized: HTTP {resp.status}"
                    )
                if resp.status >= 500:
                    raise GridxApiError(f"Server error: HTTP {resp.status}")
                resp.raise_for_status()
                return await resp.json()
        except GridxError:
            raise
        except aiohttp.ClientResponseError as err:
            if err.status in (401, 403):
                raise GridxAuthenticationError(
                    f"API request unauthorized: HTTP {err.status}"
                ) from err
            if err.status >= 500:
                raise GridxApiError(f"Server error: HTTP {err.status}") from err
            raise GridxApiError(f"API error: {err}") from err
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise GridxConnectionError(f"Connection error: {err}") from err

    async def async_get_gateways(self) -> list[str]:
        """Return list of system IDs from the gateways endpoint."""
        data = await self._get(API_GATEWAYS_URL)
        return [entry["system"]["id"] for entry in data]

    async def async_get_live_data(self, system_id: str) -> GridxSystemData:
        """Return parsed live data for the given system ID."""
        url = API_LIVE_URL.format(system_id)
        data = await self._get(url)
        return parse_live_data(data)
