"""Tests for gridX data models."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from custom_components.gridx.models import (
    GridxBattery,
    GridxHeatPump,
    GridxSystemData,
    parse_live_data,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


class TestParseFullResponse:
    def test_parse_full_response(self):
        data = load_fixture("live_data.json")
        result = parse_live_data(data)

        assert isinstance(result, GridxSystemData)

        # Top-level power flows
        assert result.consumption == pytest.approx(1728.769)
        assert result.grid == pytest.approx(22.233)
        assert result.photovoltaic == pytest.approx(0.0)
        assert result.production == pytest.approx(0.0)
        assert result.self_consumption == pytest.approx(0.0)
        assert result.self_consumption_rate == pytest.approx(0.88)
        assert result.self_sufficiency_rate == pytest.approx(0.97)
        assert result.self_supply == pytest.approx(2285.49)
        assert result.total_consumption == pytest.approx(2307.723)
        assert result.heat_pump == pytest.approx(578.954)
        assert result.direct_consumption == pytest.approx(0.0)
        assert result.direct_consumption_ev == pytest.approx(0.0)
        assert result.direct_consumption_heat_pump == pytest.approx(578.954)
        assert result.direct_consumption_heater == pytest.approx(0.0)
        assert result.direct_consumption_household == pytest.approx(0.0)
        assert result.direct_consumption_rate == pytest.approx(0.55)
        assert result.grid_meter_reading_negative == 285480000
        assert result.grid_meter_reading_positive == 1428840000

        # measured_at parsed as datetime
        assert result.measured_at == datetime(2026, 3, 16, 19, 27, 28, tzinfo=UTC)

        # Aggregate battery
        assert result.battery_power == pytest.approx(2285.49)
        assert result.battery_charge == pytest.approx(0.0)
        assert result.battery_discharge == pytest.approx(2285.49)
        assert result.battery_state_of_charge == pytest.approx(0.58)
        assert result.battery_remaining_charge == pytest.approx(8700.0)
        assert result.battery_capacity == pytest.approx(15000.0)
        assert result.battery_nominal_capacity == pytest.approx(15000.0)

        # Individual batteries
        assert len(result.batteries) == 1
        bat = result.batteries[0]
        assert isinstance(bat, GridxBattery)
        assert bat.appliance_id == "battery-001"
        assert bat.capacity == pytest.approx(15000.0)
        assert bat.charge == pytest.approx(0.0)
        assert bat.discharge == pytest.approx(2285.49)
        assert bat.nominal_capacity == pytest.approx(15000.0)
        assert bat.power == pytest.approx(2285.49)
        assert bat.remaining_charge == pytest.approx(8700.0)
        assert bat.state_of_charge == pytest.approx(0.58)

        # Individual heat pumps
        assert len(result.heat_pumps) == 1
        hp = result.heat_pumps[0]
        assert isinstance(hp, GridxHeatPump)
        assert hp.appliance_id == "heatpump-001"
        assert hp.power == pytest.approx(578.954)
        assert hp.sg_ready_state == "AUTO"

        # Empty appliance lists
        assert result.ev_charging_stations == []
        assert result.heaters == []


class TestParseMinimalResponse:
    def test_parse_minimal_response(self):
        data = load_fixture("live_data_minimal.json")
        result = parse_live_data(data)

        assert result.consumption == pytest.approx(500.0)
        assert result.grid == pytest.approx(300.0)
        assert result.photovoltaic == pytest.approx(200.0)
        assert result.direct_consumption_household == pytest.approx(200.0)

        # No appliances
        assert result.batteries == []
        assert result.heat_pumps == []
        assert result.ev_charging_stations == []
        assert result.heaters == []

        # Aggregate battery defaults to 0
        assert result.battery_power == pytest.approx(0.0)
        assert result.battery_state_of_charge == pytest.approx(0.0)

        assert result.measured_at == datetime(2026, 3, 16, 12, 0, 0, tzinfo=UTC)


class TestParseMultiApplianceResponse:
    def test_parse_multi_appliance_response(self):
        data = load_fixture("live_data_multi.json")
        result = parse_live_data(data)

        assert len(result.batteries) == 2
        assert result.batteries[0].appliance_id == "battery-001"
        assert result.batteries[0].state_of_charge == pytest.approx(0.67)
        assert result.batteries[0].power == pytest.approx(-100.0)
        assert result.batteries[1].appliance_id == "battery-002"
        assert result.batteries[1].state_of_charge == pytest.approx(0.4)
        assert result.batteries[1].power == pytest.approx(500.0)

        assert len(result.heat_pumps) == 2
        assert result.heat_pumps[0].appliance_id == "heatpump-001"
        assert result.heat_pumps[0].sg_ready_state == "AUTO"
        assert result.heat_pumps[1].appliance_id == "heatpump-002"
        assert result.heat_pumps[1].sg_ready_state == "BOOST"

        # Aggregate battery from "battery" key
        assert result.battery_state_of_charge == pytest.approx(0.6)
        assert result.battery_capacity == pytest.approx(20000.0)
        assert result.battery_nominal_capacity == pytest.approx(20000.0)


class TestParseDefaultFields:
    def test_parse_missing_fields_default(self):
        result = parse_live_data({})

        assert result.consumption == pytest.approx(0.0)
        assert result.grid == pytest.approx(0.0)
        assert result.photovoltaic == pytest.approx(0.0)
        assert result.heat_pump == pytest.approx(0.0)
        assert result.battery_power == pytest.approx(0.0)
        assert result.battery_state_of_charge == pytest.approx(0.0)
        assert result.batteries == []
        assert result.heat_pumps == []
        assert result.ev_charging_stations == []
        assert result.heaters == []
        assert result.measured_at is None


class TestParseUnknownFields:
    def test_parse_unknown_fields_ignored(self):
        data = {
            "consumption": 100.0,
            "unknownField": "surprise",
            "anotherUnknown": 42,
        }
        result = parse_live_data(data)
        assert result.consumption == pytest.approx(100.0)
        # No exception raised


class TestParseInvalidFields:
    def test_parse_invalid_fields_default_safely(self):
        data = {
            "measuredAt": 123,
            "consumption": None,
            "grid": "invalid",
            "battery": "not-a-dict",
            "batteries": [None, {"applianceID": 42, "power": "bad"}],
            "heatPumps": "wrong-type",
            "evChargingStations": [[], {"applianceID": "ev-1", "currentL1": ""}],
            "heaters": [True, {"temperature": "oops"}],
        }

        result = parse_live_data(data)

        assert result.measured_at is None
        assert result.consumption == pytest.approx(0.0)
        assert result.grid == pytest.approx(0.0)
        assert result.battery_power == pytest.approx(0.0)
        assert len(result.batteries) == 1
        assert result.batteries[0].appliance_id == "42"
        assert result.batteries[0].power == pytest.approx(0.0)
        assert result.heat_pumps == []
        assert len(result.ev_charging_stations) == 1
        assert result.ev_charging_stations[0].current_l1 == pytest.approx(0.0)
        assert len(result.heaters) == 1
        assert result.heaters[0].temperature == pytest.approx(0.0)
