"""Tests for gridX diagnostics."""

from unittest.mock import MagicMock

import pytest

from custom_components.gridx.const import COORDINATOR_LIVE
from custom_components.gridx.diagnostics import (
    REDACT_KEYS,
    async_get_config_entry_diagnostics,
)
from custom_components.gridx.models import (
    GridxBattery,
    GridxEVChargingStation,
    GridxHeater,
    GridxHeatPump,
    GridxSystemData,
)


@pytest.fixture
def mock_system_data():
    """Return a GridxSystemData instance with one of each appliance."""
    return GridxSystemData(
        production=3500.0,
        consumption=2200.0,
        grid=-1300.0,
        photovoltaic=3500.0,
        batteries=[GridxBattery(appliance_id="bat1", state_of_charge=0.8)],
        heat_pumps=[GridxHeatPump(appliance_id="hp1", power=800.0)],
        ev_charging_stations=[GridxEVChargingStation(appliance_id="ev1", power=7400.0)],
        heaters=[GridxHeater(appliance_id="heater1", power=500.0)],
    )


@pytest.fixture
def mock_coordinator(mock_system_data):
    """Return a mock coordinator with one system."""
    coordinator = MagicMock()
    coordinator.data = {"system-abc": mock_system_data}
    return coordinator


@pytest.fixture
def mock_entry(mock_coordinator):
    """Return a mock config entry with runtime_data."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.runtime_data = {COORDINATOR_LIVE: mock_coordinator}
    entry.as_dict.return_value = {
        "entry_id": "test_entry_id",
        "domain": "gridx",
        "data": {
            "email": "user@example.com",
            "password": "secret123",
        },
        "options": {},
        "title": "gridX",
    }
    return entry


@pytest.fixture
def mock_hass():
    """Return a mock hass."""
    return MagicMock()


@pytest.mark.asyncio
async def test_diagnostics_returns_structure(mock_hass, mock_entry):
    """Diagnostics output has config_entry and coordinator_data keys."""
    result = await async_get_config_entry_diagnostics(mock_hass, mock_entry)
    assert "config_entry" in result
    assert "coordinator_data" in result


@pytest.mark.asyncio
async def test_diagnostics_coordinator_data_keys(mock_hass, mock_entry):
    """Each system entry contains expected power-flow keys."""
    result = await async_get_config_entry_diagnostics(mock_hass, mock_entry)
    system_data = result["coordinator_data"]["system-abc"]
    for key in ("production", "consumption", "grid", "photovoltaic"):
        assert key in system_data


@pytest.mark.asyncio
async def test_diagnostics_appliance_counts(mock_hass, mock_entry):
    """Appliance counts are integers, not full objects."""
    result = await async_get_config_entry_diagnostics(mock_hass, mock_entry)
    system_data = result["coordinator_data"]["system-abc"]
    assert system_data["batteries"] == 1
    assert system_data["heat_pumps"] == 1
    assert system_data["ev_charging_stations"] == 1
    assert system_data["heaters"] == 1


@pytest.mark.asyncio
async def test_diagnostics_redacts_credentials(mock_hass, mock_entry):
    """Email and password are redacted in config_entry data."""
    result = await async_get_config_entry_diagnostics(mock_hass, mock_entry)
    config_data = result["config_entry"]["data"]
    assert config_data["email"] == "**REDACTED**"
    assert config_data["password"] == "**REDACTED**"


@pytest.mark.asyncio
async def test_diagnostics_preserves_non_sensitive_data(mock_hass, mock_entry):
    """Non-sensitive fields in config_entry are not redacted."""
    result = await async_get_config_entry_diagnostics(mock_hass, mock_entry)
    assert result["config_entry"]["domain"] == "gridx"
    assert result["config_entry"]["title"] == "gridX"


def test_redact_keys_contains_expected_fields():
    """REDACT_KEYS covers all credential-related fields."""
    assert "email" in REDACT_KEYS
    assert "password" in REDACT_KEYS
    assert "access_token" in REDACT_KEYS
    assert "refresh_token" in REDACT_KEYS
    assert "id_token" in REDACT_KEYS
