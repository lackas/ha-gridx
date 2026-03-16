"""Tests for the gridX DataUpdateCoordinator."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.gridx.api import (
    GridxApiError,
    GridxAuthenticationError,
    GridxConnectionError,
)
from custom_components.gridx.const import (
    DEFAULT_SCAN_INTERVAL,
    ERROR_SCAN_INTERVAL_MAX,
)
from custom_components.gridx.models import GridxSystemData


def make_hass():
    """Create a minimal mock hass object."""
    hass = MagicMock()
    hass.bus = MagicMock()
    hass.bus.async_listen = MagicMock(return_value=lambda: None)
    hass.data = {}
    # Provide a real asyncio loop so the coordinator can schedule tasks
    import asyncio

    hass.loop = asyncio.get_event_loop()
    return hass


def make_config_entry(system_ids=None):
    """Create a minimal mock ConfigEntry."""
    if system_ids is None:
        system_ids = ["system-id-001"]
    entry = MagicMock()
    entry.data = {
        "system_ids": system_ids,
        "email": "test@test.com",
        "password": "pass",
    }
    entry.async_start_reauth = MagicMock()
    return entry


def make_api(live_data=None):
    """Create a mock GridxApi."""
    api = MagicMock()
    api._ensure_token = AsyncMock()
    if live_data is None:
        live_data = GridxSystemData(consumption=1500.0)
    api.async_get_live_data = AsyncMock(return_value=live_data)
    return api


# ---------------------------------------------------------------------------
# Import coordinator here (after helpers so failures are obvious)
# ---------------------------------------------------------------------------
from custom_components.gridx.coordinator import GridxCoordinator  # noqa: E402


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_coordinator_update_success():
    """Successful update returns correct data for each system ID."""
    system_data = GridxSystemData(consumption=1500.0, photovoltaic=3000.0)
    api = make_api(live_data=system_data)
    hass = make_hass()
    entry = make_config_entry(system_ids=["system-id-001"])

    coordinator = GridxCoordinator(hass, api, entry)

    result = await coordinator._async_update_data()

    assert "system-id-001" in result
    assert result["system-id-001"].consumption == 1500.0
    assert result["system-id-001"].photovoltaic == 3000.0
    api._ensure_token.assert_awaited_once()
    api.async_get_live_data.assert_awaited_once_with("system-id-001")

    # Interval should be reset to default
    assert coordinator.update_interval == timedelta(seconds=DEFAULT_SCAN_INTERVAL)
    # Error counter reset
    assert coordinator._consecutive_errors == 0


@pytest.mark.asyncio
async def test_coordinator_connection_error():
    """GridxConnectionError → UpdateFailed is raised."""
    from homeassistant.helpers.update_coordinator import UpdateFailed

    api = make_api()
    api.async_get_live_data = AsyncMock(side_effect=GridxConnectionError("timeout"))
    hass = make_hass()
    entry = make_config_entry()

    coordinator = GridxCoordinator(hass, api, entry)

    with pytest.raises(UpdateFailed, match="Error fetching data"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_api_error():
    """GridxApiError → UpdateFailed is raised."""
    from homeassistant.helpers.update_coordinator import UpdateFailed

    api = make_api()
    api.async_get_live_data = AsyncMock(side_effect=GridxApiError("server error"))
    hass = make_hass()
    entry = make_config_entry()

    coordinator = GridxCoordinator(hass, api, entry)

    with pytest.raises(UpdateFailed, match="Error fetching data"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_auth_error():
    """GridxAuthenticationError → UpdateFailed raised + reauth triggered."""
    from homeassistant.helpers.update_coordinator import UpdateFailed

    api = make_api()
    api._ensure_token = AsyncMock(side_effect=GridxAuthenticationError("bad token"))
    hass = make_hass()
    entry = make_config_entry()

    coordinator = GridxCoordinator(hass, api, entry)

    with pytest.raises(UpdateFailed, match="Authentication failed"):
        await coordinator._async_update_data()

    entry.async_start_reauth.assert_called_once_with(hass)


@pytest.mark.asyncio
async def test_coordinator_backoff_increases():
    """After errors, update_interval increases: 120s → 240s."""
    from homeassistant.helpers.update_coordinator import UpdateFailed

    api = make_api()
    api.async_get_live_data = AsyncMock(side_effect=GridxConnectionError("timeout"))
    hass = make_hass()
    entry = make_config_entry()

    coordinator = GridxCoordinator(hass, api, entry)

    # First error → backoff = 120 * 2^0 = 120s
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    assert coordinator._consecutive_errors == 1
    assert coordinator.update_interval == timedelta(seconds=120)

    # Second error → backoff = 120 * 2^1 = 240s
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    assert coordinator._consecutive_errors == 2
    assert coordinator.update_interval == timedelta(seconds=240)


@pytest.mark.asyncio
async def test_coordinator_backoff_capped():
    """Backoff is capped at ERROR_SCAN_INTERVAL_MAX (900s)."""
    from homeassistant.helpers.update_coordinator import UpdateFailed

    api = make_api()
    api.async_get_live_data = AsyncMock(side_effect=GridxConnectionError("timeout"))
    hass = make_hass()
    entry = make_config_entry()

    coordinator = GridxCoordinator(hass, api, entry)
    # Force many consecutive errors
    coordinator._consecutive_errors = 10

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    assert coordinator.update_interval == timedelta(seconds=ERROR_SCAN_INTERVAL_MAX)


@pytest.mark.asyncio
async def test_coordinator_backoff_reset():
    """After a successful update following errors, interval resets to 60s."""
    api = make_api()
    hass = make_hass()
    entry = make_config_entry()

    coordinator = GridxCoordinator(hass, api, entry)
    # Simulate prior errors
    coordinator._consecutive_errors = 3
    coordinator.update_interval = timedelta(seconds=480)

    result = await coordinator._async_update_data()

    assert result is not None
    assert coordinator._consecutive_errors == 0
    assert coordinator.update_interval == timedelta(seconds=DEFAULT_SCAN_INTERVAL)


@pytest.mark.asyncio
async def test_coordinator_multiple_systems():
    """Multiple system IDs are all fetched and returned."""
    system_a = GridxSystemData(consumption=1000.0)
    system_b = GridxSystemData(consumption=2000.0)

    api = make_api()
    api.async_get_live_data = AsyncMock(side_effect=[system_a, system_b])
    hass = make_hass()
    entry = make_config_entry(system_ids=["sys-a", "sys-b"])

    coordinator = GridxCoordinator(hass, api, entry)

    result = await coordinator._async_update_data()

    assert result["sys-a"].consumption == 1000.0
    assert result["sys-b"].consumption == 2000.0
    assert api.async_get_live_data.await_count == 2
