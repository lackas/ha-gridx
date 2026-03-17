"""Tests for the gridX API client."""

from __future__ import annotations

import json
import time
from pathlib import Path

import aiohttp
import pytest
from aioresponses import aioresponses

from custom_components.gridx.api import (
    GridxApi,
    GridxApiError,
    GridxAuthenticationError,
    GridxConnectionError,
)
from custom_components.gridx.const import (
    API_GATEWAYS_URL,
    API_LIVE_URL,
    AUTH0_TOKEN_URL,
)
from custom_components.gridx.models import GridxSystemData

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


# ---------------------------------------------------------------------------
# Token response helper
# ---------------------------------------------------------------------------

TOKEN_RESPONSE = {
    "access_token": "access-abc",
    "id_token": "id-token-xyz",
    "refresh_token": "refresh-123",
    "expires_in": 3600,
    "token_type": "Bearer",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAuthenticate:
    @pytest.mark.asyncio
    async def test_authenticate_success(self):
        async with aiohttp.ClientSession() as session:
            api = GridxApi(session, "user@example.com", "secret")

            with aioresponses() as m:
                m.post(AUTH0_TOKEN_URL, payload=TOKEN_RESPONSE)
                await api.authenticate()

            assert api._token is not None
            assert api._token["access_token"] == "access-abc"
            assert api._token["id_token"] == "id-token-xyz"
            assert api._token["refresh_token"] == "refresh-123"
            assert api._token["expires_at"] > time.monotonic()

    @pytest.mark.asyncio
    async def test_authenticate_bad_credentials(self):
        async with aiohttp.ClientSession() as session:
            api = GridxApi(session, "bad@example.com", "wrong")

            with aioresponses() as m:
                m.post(AUTH0_TOKEN_URL, status=401)
                with pytest.raises(GridxAuthenticationError):
                    await api.authenticate()

    @pytest.mark.asyncio
    async def test_authenticate_connection_error(self):
        async with aiohttp.ClientSession() as session:
            api = GridxApi(session, "user@example.com", "secret")

            with aioresponses() as m:
                m.post(AUTH0_TOKEN_URL, exception=aiohttp.ClientError("refused"))
                with pytest.raises(GridxConnectionError):
                    await api.authenticate()


class TestGetGateways:
    @pytest.mark.asyncio
    async def test_get_gateways_success(self):
        gateways_data = load_fixture("gateways.json")

        async with aiohttp.ClientSession() as session:
            api = GridxApi(session, "user@example.com", "secret")

            with aioresponses() as m:
                m.post(AUTH0_TOKEN_URL, payload=TOKEN_RESPONSE)
                m.get(API_GATEWAYS_URL, payload=gateways_data)
                result = await api.async_get_gateways()

            assert result == ["system-id-001"]


class TestGetLiveData:
    @pytest.mark.asyncio
    async def test_get_live_data_success(self):
        live_data = load_fixture("live_data.json")
        system_id = "system-id-001"
        url = API_LIVE_URL.format(system_id)

        async with aiohttp.ClientSession() as session:
            api = GridxApi(session, "user@example.com", "secret")

            with aioresponses() as m:
                m.post(AUTH0_TOKEN_URL, payload=TOKEN_RESPONSE)
                m.get(url, payload=live_data)
                result = await api.async_get_live_data(system_id)

            assert isinstance(result, GridxSystemData)
            assert result.consumption == pytest.approx(1728.769)
            assert result.battery_state_of_charge == pytest.approx(0.58)

    @pytest.mark.asyncio
    async def test_get_live_data_server_error(self):
        system_id = "system-id-001"
        url = API_LIVE_URL.format(system_id)

        async with aiohttp.ClientSession() as session:
            api = GridxApi(session, "user@example.com", "secret")

            with aioresponses() as m:
                m.post(AUTH0_TOKEN_URL, payload=TOKEN_RESPONSE)
                m.get(url, status=500)
                with pytest.raises(GridxApiError):
                    await api.async_get_live_data(system_id)

    @pytest.mark.asyncio
    async def test_get_live_data_invalid_payload_raises_api_error(self):
        system_id = "system-id-001"
        url = API_LIVE_URL.format(system_id)

        async with aiohttp.ClientSession() as session:
            api = GridxApi(session, "user@example.com", "secret")

            with aioresponses() as m:
                m.post(AUTH0_TOKEN_URL, payload=TOKEN_RESPONSE)
                m.get(url, payload=[])
                with pytest.raises(GridxApiError, match="Unexpected live data payload"):
                    await api.async_get_live_data(system_id)


class TestTokenRefresh:
    @pytest.mark.asyncio
    async def test_token_auto_refresh(self):
        """Token near-expiry should trigger re-auth before the API call."""
        live_data = load_fixture("live_data.json")
        system_id = "system-id-001"
        url = API_LIVE_URL.format(system_id)

        async with aiohttp.ClientSession() as session:
            api = GridxApi(session, "user@example.com", "secret")

            # Pre-seed token that expires in 30s (within the 60s threshold)
            api._token = {
                "access_token": "old-access",
                "id_token": "old-id-token",
                "refresh_token": "old-refresh",
                "expires_at": time.monotonic() + 30,
            }
            # Allow auth (no cooldown)
            api._last_auth_attempt = 0

            new_token = {**TOKEN_RESPONSE, "id_token": "new-id-token"}

            with aioresponses() as m:
                # Refresh token call
                m.post(AUTH0_TOKEN_URL, payload=new_token)
                # Actual API call
                m.get(url, payload=live_data)
                result = await api.async_get_live_data(system_id)

            # Should have used the refreshed token
            assert api._token["id_token"] == "new-id-token"
            assert isinstance(result, GridxSystemData)


class TestAuthCooldown:
    @pytest.mark.asyncio
    async def test_auth_cooldown(self):
        """Second authenticate() call within cooldown window must not hit Auth0."""
        async with aiohttp.ClientSession() as session:
            api = GridxApi(session, "user@example.com", "secret")

            with aioresponses() as m:
                # Only one POST should happen; if two happen aioresponses raises
                m.post(AUTH0_TOKEN_URL, payload=TOKEN_RESPONSE)

                await api.authenticate()
                # Second call within cooldown — must be a no-op
                await api.authenticate()

            # Token from first call is still there
            assert api._token is not None
            assert api._token["id_token"] == "id-token-xyz"

    @pytest.mark.asyncio
    async def test_auth_cooldown_does_not_hide_missing_token(self):
        """A failed auth attempt must not leave later calls without a token."""
        async with aiohttp.ClientSession() as session:
            api = GridxApi(session, "user@example.com", "secret")

            with aioresponses() as m:
                m.post(
                    AUTH0_TOKEN_URL,
                    exception=aiohttp.ClientError("temporary auth failure"),
                )
                with pytest.raises(GridxConnectionError):
                    await api.authenticate()

                m.post(AUTH0_TOKEN_URL, payload=TOKEN_RESPONSE)
                await api.authenticate()

            assert api._token is not None
            assert api._token["id_token"] == "id-token-xyz"
