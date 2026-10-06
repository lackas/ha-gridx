"""Tests for the gridX EV charging control entities."""

from datetime import datetime, time
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from custom_components.gridx.api import GridxApiError
from custom_components.gridx.entity import iter_ev_stations
from custom_components.gridx.models import GridxEVChargingStation, GridxSystemData
from custom_components.gridx.number import (
    GridxEVMaxChargePowerNumber,
    GridxEVMinSocNumber,
)
from custom_components.gridx.select import GridxEVChargeModeSelect
from custom_components.gridx.time import GridxEVDepartureTime

from .conftest import load_fixture

BERLIN = ZoneInfo("Europe/Berlin")


@pytest.fixture(autouse=True)
def berlin_time_zone():
    """Run with a non-UTC local time zone so conversions are visible."""
    dt_util.set_default_time_zone(BERLIN)
    yield
    dt_util.set_default_time_zone(dt_util.UTC)


def frozen_now(value: str):
    """Patch the current time used for the next departure."""
    return patch(
        "custom_components.gridx.entity.dt_util.now",
        return_value=datetime.fromisoformat(value).astimezone(BERLIN),
    )


def make_coordinator(config: dict | None = None) -> MagicMock:
    """Coordinator with one system and one EV station."""
    data = GridxSystemData(
        ev_charging_stations=[GridxEVChargingStation(appliance_id="ev-001")]
    )
    if config is not None:
        data.ev_configurations["ev-001"] = config
    coordinator = MagicMock()
    coordinator.data = {"system-id-001": data}
    coordinator.async_set_ev_configuration = AsyncMock()
    coordinator.async_get_ev_capacity = AsyncMock(return_value=79000)
    return coordinator


def make_entity(cls, key: str, config: dict | None = None):
    if config is None:
        config = load_fixture("ev_configuration.json")
    coordinator = make_coordinator(config)
    return cls(coordinator, "system-id-001", "ev-001", "gridX EV Charger", key)


def sent_changes(entity) -> dict:
    """The changes passed to the coordinator in the single PATCH."""
    entity.coordinator.async_set_ev_configuration.assert_awaited_once()
    system_id, appliance_id, changes = (
        entity.coordinator.async_set_ev_configuration.await_args.args
    )
    assert (system_id, appliance_id) == ("system-id-001", "ev-001")
    return changes


def test_iter_ev_stations_names_devices():
    coordinator = MagicMock()
    coordinator.data = {
        "sys": GridxSystemData(
            ev_charging_stations=[
                GridxEVChargingStation(appliance_id="ev-a"),
                GridxEVChargingStation(appliance_id="ev-b"),
            ]
        )
    }
    assert list(iter_ev_stations(coordinator)) == [
        ("sys", "ev-a", "gridX EV Charger"),
        ("sys", "ev-b", "gridX EV Charger 2"),
    ]


class TestChargeModeSelect:
    def test_unique_id_and_options(self):
        select = make_entity(GridxEVChargeModeSelect, "ev_charge_mode")
        assert select.unique_id == "ev-001_ev_charge_mode"
        assert select.translation_key == "ev_charge_mode"
        assert select.options == ["forced", "min", "departure_time", "surplus"]

    def test_current_option(self):
        select = make_entity(GridxEVChargeModeSelect, "ev_charge_mode")
        assert select.current_option == "surplus"
        assert select.available

    def test_unknown_mode(self):
        select = make_entity(
            GridxEVChargeModeSelect, "ev_charge_mode", {"chargeMode": "NEW_MODE"}
        )
        assert select.current_option is None

    def test_unavailable_without_config(self):
        coordinator = make_coordinator(None)
        select = GridxEVChargeModeSelect(
            coordinator, "system-id-001", "ev-001", "gridX EV Charger", "x"
        )
        assert not select.available

    @pytest.mark.asyncio
    async def test_select_forced(self):
        select = make_entity(GridxEVChargeModeSelect, "ev_charge_mode")
        await select.async_select_option("forced")
        assert sent_changes(select) == {"chargeMode": "FORCED_EV"}

    @pytest.mark.asyncio
    async def test_select_min_uses_defaults_and_profile_capacity(self):
        select = make_entity(GridxEVChargeModeSelect, "ev_charge_mode")
        await select.async_select_option("min")
        assert sent_changes(select) == {
            "chargeMode": "MIN_EV",
            "minRequestedSoc": 80,
            "userTotalCapacity": 79000,
        }
        select.coordinator.async_get_ev_capacity.assert_awaited_once_with(
            "system-id-001", "ev-001"
        )

    @pytest.mark.asyncio
    async def test_select_min_keeps_configured_values(self):
        select = make_entity(
            GridxEVChargeModeSelect,
            "ev_charge_mode",
            {"chargeMode": "SURPLUS_EV", "minRequestedSoc": 60, "userTotalCapacity": 1},
        )
        await select.async_select_option("min")
        assert sent_changes(select) == {
            "chargeMode": "MIN_EV",
            "minRequestedSoc": 60,
            "userTotalCapacity": 1,
        }
        select.coordinator.async_get_ev_capacity.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_select_departure_time_defaults_to_next_seven(self):
        select = make_entity(GridxEVChargeModeSelect, "ev_charge_mode")
        # 22:00 in Berlin, so the next 07:00 is tomorrow
        with frozen_now("2026-10-06T20:00:00+00:00"):
            await select.async_select_option("departure_time")
        assert sent_changes(select) == {
            "chargeMode": "DEPARTURE_TIME_EV",
            "minRequestedSoc": 80,
            "userTotalCapacity": 79000,
            "departureTimestamp": "2026-10-07T05:00:00Z",
        }

    @pytest.mark.asyncio
    async def test_select_departure_time_keeps_configured_timestamp(self):
        select = make_entity(
            GridxEVChargeModeSelect,
            "ev_charge_mode",
            {
                "minRequestedSoc": 70,
                "userTotalCapacity": 79000,
                "departureTimestamp": "2026-10-01T04:30:00Z",
            },
        )
        await select.async_select_option("departure_time")
        assert sent_changes(select)["departureTimestamp"] == "2026-10-01T04:30:00Z"

    @pytest.mark.asyncio
    async def test_select_min_without_capacity_raises(self):
        select = make_entity(GridxEVChargeModeSelect, "ev_charge_mode")
        select.coordinator.async_get_ev_capacity.return_value = None
        with pytest.raises(HomeAssistantError, match="capacity"):
            await select.async_select_option("min")
        select.coordinator.async_set_ev_configuration.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_api_error_becomes_home_assistant_error(self):
        select = make_entity(GridxEVChargeModeSelect, "ev_charge_mode")
        select.coordinator.async_set_ev_configuration.side_effect = GridxApiError(
            "HTTP 400"
        )
        with pytest.raises(HomeAssistantError, match="HTTP 400"):
            await select.async_select_option("forced")


class TestMinSocNumber:
    def test_value(self):
        number = make_entity(
            GridxEVMinSocNumber, "ev_min_requested_soc", {"minRequestedSoc": 60}
        )
        assert number.unique_id == "ev-001_ev_min_requested_soc"
        assert number.native_value == 60
        assert number.native_step == 5

    def test_value_unset(self):
        number = make_entity(GridxEVMinSocNumber, "ev_min_requested_soc")
        assert number.native_value is None

    @pytest.mark.asyncio
    async def test_set_value_sends_capacity(self):
        number = make_entity(GridxEVMinSocNumber, "ev_min_requested_soc")
        await number.async_set_native_value(60.0)
        assert sent_changes(number) == {
            "minRequestedSoc": 60,
            "userTotalCapacity": 79000,
        }


class TestMaxChargePowerNumber:
    def test_disabled_by_default(self):
        number = make_entity(GridxEVMaxChargePowerNumber, "ev_max_charge_power")
        assert number.unique_id == "ev-001_ev_max_charge_power"
        assert number.entity_registry_enabled_default is False

    def test_no_limit_reads_as_zero(self):
        number = make_entity(GridxEVMaxChargePowerNumber, "ev_max_charge_power")
        assert number.native_value == 0

    @pytest.mark.asyncio
    async def test_set_limit(self):
        number = make_entity(GridxEVMaxChargePowerNumber, "ev_max_charge_power")
        await number.async_set_native_value(11000.0)
        assert sent_changes(number) == {"maxChargePower": 11000}

    @pytest.mark.asyncio
    async def test_zero_clears_limit(self):
        number = make_entity(GridxEVMaxChargePowerNumber, "ev_max_charge_power")
        await number.async_set_native_value(0.0)
        assert sent_changes(number) == {"maxChargePower": None}


class TestDepartureTime:
    def test_value_in_local_time(self):
        entity = make_entity(
            GridxEVDepartureTime,
            "ev_departure_time",
            {"departureTimestamp": "2026-10-07T05:30:00Z"},
        )
        assert entity.unique_id == "ev-001_ev_departure_time"
        assert entity.native_value == time(7, 30)

    def test_value_unset(self):
        entity = make_entity(GridxEVDepartureTime, "ev_departure_time")
        assert entity.native_value is None

    @pytest.mark.asyncio
    async def test_set_value_later_today(self):
        entity = make_entity(GridxEVDepartureTime, "ev_departure_time")
        # 06:00 in Berlin
        with frozen_now("2026-10-06T04:00:00+00:00"):
            await entity.async_set_value(time(6, 30))
        assert sent_changes(entity) == {"departureTimestamp": "2026-10-06T04:30:00Z"}

    @pytest.mark.asyncio
    async def test_set_value_tomorrow(self):
        entity = make_entity(GridxEVDepartureTime, "ev_departure_time")
        with frozen_now("2026-10-06T20:00:00+00:00"):
            await entity.async_set_value(time(6, 15))
        assert sent_changes(entity) == {"departureTimestamp": "2026-10-07T04:15:00Z"}
