"""Async API client for gridX energy management."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

import aiohttp

from .const import (
    API_GATEWAYS_URL,
    API_HISTORICAL_URL,
    API_LIVE_URL,
    AUTH0_AUDIENCE,
    AUTH0_CLIENT_ID,
    AUTH0_GRANT_TYPE,
    AUTH0_REALM,
    AUTH0_SCOPE,
    AUTH0_TOKEN_URL,
    AUTH_COOLDOWN_SECONDS,
    CONNECTION_RETRIES,
    CONNECTION_RETRY_DELAY,
)
from .models import GridxSystemData, parse_live_data

_LOGGER = logging.getLogger(__name__)


class GridxError(Exception):
    """Base exception for gridX API errors."""


class GridxAuthenticationError(GridxError):
    """Authentication failed (bad credentials, expired, 401/403)."""


class GridxConnectionError(GridxError):
    """Connection failed (timeout, DNS, refused)."""


class GridxApiError(GridxError):
    """Unexpected API error (5xx, bad response)."""


# Transient connection-layer errors that warrant a brief retry.
# Excludes ClientResponseError (HTTP-level, the server replied) and
# ClientPayloadError (mid-stream corruption — not helped by retry).
_TRANSIENT_EXCEPTIONS: tuple[type[BaseException], ...] = (
    TimeoutError,
    aiohttp.ClientConnectionError,
)


async def _retry_transient(
    coro_factory: Callable[[], Awaitable[Any]],
    op_name: str = "request",
) -> Any:
    """Run an async HTTP coroutine, retrying on transient connection errors.

    Only TimeoutError and aiohttp.ClientConnectionError trigger a retry
    (DNS timeout, connection refused, read timeout). HTTP-level errors
    (4xx, 5xx via raise_for_status) and Gridx*Error subclasses bubble out
    immediately. Delay between attempts doubles each time (1s, 2s, 4s, ...).

    Auth0 hostnames have CNAME chains (gridx.eu.auth0.com →
    pivot.prod.auth0edge.com → cdn.cloudflare.net) with 2s TTLs on
    intermediate hops, making DNS lookups more brittle than for single
    A-record hosts. Brief retries with exponential backoff absorb that.
    """
    delay = CONNECTION_RETRY_DELAY
    last_err: BaseException | None = None
    for attempt in range(CONNECTION_RETRIES + 1):
        try:
            return await coro_factory()
        except _TRANSIENT_EXCEPTIONS as err:
            last_err = err
            if attempt < CONNECTION_RETRIES:
                _LOGGER.debug(
                    "gridX %s attempt %d/%d failed (%s) — retrying in %.1fs",
                    op_name,
                    attempt + 1,
                    CONNECTION_RETRIES + 1,
                    err,
                    delay,
                )
                await asyncio.sleep(delay)
                delay *= 2
                continue
            # Exhausted retries — re-raise original type for outer handlers
            raise
    # Unreachable, but keeps type-checker happy
    assert last_err is not None
    raise last_err


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
        if (
            self._token is not None
            and now - self._last_auth_attempt < AUTH_COOLDOWN_SECONDS
        ):
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

        async def _do_request() -> dict[str, Any]:
            async with self._session.post(AUTH0_TOKEN_URL, json=payload) as resp:
                if resp.status in (401, 403):
                    raise GridxAuthenticationError(
                        f"Authentication failed: HTTP {resp.status}"
                    )
                resp.raise_for_status()
                return await resp.json()

        try:
            data = await _retry_transient(_do_request, op_name="auth")
        except aiohttp.ClientResponseError as err:
            if err.status in (401, 403):
                raise GridxAuthenticationError(
                    f"Authentication failed: HTTP {err.status}"
                ) from err
            raise GridxApiError(f"Auth API error: {err}") from err
        except (TimeoutError, aiohttp.ClientError) as err:
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

        async def _do_request() -> dict[str, Any]:
            async with self._session.post(AUTH0_TOKEN_URL, json=payload) as resp:
                if resp.status in (401, 403):
                    raise GridxAuthenticationError(
                        f"Token refresh failed: HTTP {resp.status}"
                    )
                resp.raise_for_status()
                return await resp.json()

        try:
            data = await _retry_transient(_do_request, op_name="refresh")
        except aiohttp.ClientResponseError as err:
            if err.status in (401, 403):
                raise GridxAuthenticationError(
                    f"Token refresh failed: HTTP {err.status}"
                ) from err
            raise GridxApiError(f"Token refresh API error: {err}") from err
        except (TimeoutError, aiohttp.ClientError) as err:
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

    async def _get(self, url: str, *, _retried: bool = False) -> Any:
        """Perform an authenticated GET request."""
        await self._ensure_token()

        headers = {"Authorization": f"Bearer {self._token['id_token']}"}

        async def _do_request() -> Any:
            async with self._session.get(url, headers=headers) as resp:
                if resp.status in (401, 403):
                    # Surface as ClientResponseError so the outer except can
                    # decide whether to refresh the token and retry once.
                    resp.raise_for_status()
                if resp.status >= 500:
                    raise GridxApiError(f"Server error: HTTP {resp.status}")
                resp.raise_for_status()
                return await resp.json()

        try:
            return await _retry_transient(_do_request, op_name="GET")
        except GridxError:
            raise
        except aiohttp.ClientResponseError as err:
            if err.status in (401, 403):
                if not _retried:
                    self._token = None
                    return await self._get(url, _retried=True)
                raise GridxAuthenticationError(
                    f"API request unauthorized: HTTP {err.status}"
                ) from err
            if err.status >= 500:
                raise GridxApiError(f"Server error: HTTP {err.status}") from err
            raise GridxApiError(f"API error: {err}") from err
        except (TimeoutError, aiohttp.ClientError) as err:
            raise GridxConnectionError(f"Connection error: {err}") from err

    async def async_get_gateways(self) -> list[str]:
        """Return list of system IDs from the gateways endpoint."""
        data = await self._get(API_GATEWAYS_URL)
        try:
            return [str(entry["system"]["id"]) for entry in data]
        except (KeyError, TypeError, ValueError) as err:
            raise GridxApiError("Unexpected gateways payload") from err

    async def async_get_live_data(self, system_id: str) -> GridxSystemData:
        """Return parsed live data for the given system ID."""
        url = API_LIVE_URL.format(system_id)
        data = await self._get(url)
        try:
            return parse_live_data(data)
        except (AttributeError, TypeError, ValueError) as err:
            raise GridxApiError("Unexpected live data payload") from err

    async def async_get_historical_data(
        self,
        system_id: str,
        start: str,
        end: str,
        resolution: str = "1d",
    ) -> dict[str, Any]:
        """Return raw historical data for the given system ID."""
        url = (
            f"{API_HISTORICAL_URL.format(system_id)}"
            f"?interval={start}/{end}&resolution={resolution}"
        )
        data = await self._get(url)
        if not isinstance(data, dict):
            raise GridxApiError("Unexpected historical data payload")
        return data
