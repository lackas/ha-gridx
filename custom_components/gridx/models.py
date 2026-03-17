"""Data models for the gridX integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class GridxBattery:
    """Represents an individual battery appliance."""

    appliance_id: str = ""
    capacity: float = 0.0
    charge: float = 0.0
    discharge: float = 0.0
    nominal_capacity: float = 0.0
    power: float = 0.0
    remaining_charge: float = 0.0
    state_of_charge: float = 0.0


@dataclass
class GridxHeatPump:
    """Represents an individual heat pump appliance."""

    appliance_id: str = ""
    power: float = 0.0
    sg_ready_state: str = ""


@dataclass
class GridxEVChargingStation:
    """Represents an individual EV charging station appliance."""

    appliance_id: str = ""
    power: float = 0.0
    state_of_charge: float = 0.0
    current_l1: float = 0.0
    current_l2: float = 0.0
    current_l3: float = 0.0
    reading_total: float = 0.0


@dataclass
class GridxHeater:
    """Represents an individual heater appliance."""

    appliance_id: str = ""
    power: float = 0.0
    temperature: float = 0.0


@dataclass
class GridxSystemData:
    """Parsed live data from the gridX API."""

    # Timestamp
    measured_at: datetime | None = None

    # Power flows (W)
    consumption: float = 0.0
    direct_consumption: float = 0.0
    direct_consumption_ev: float = 0.0
    direct_consumption_heat_pump: float = 0.0
    direct_consumption_heater: float = 0.0
    direct_consumption_household: float = 0.0
    direct_consumption_rate: float = 0.0
    grid: float = 0.0
    heat_pump: float = 0.0
    photovoltaic: float = 0.0
    production: float = 0.0
    self_consumption: float = 0.0
    self_consumption_rate: float = 0.0
    self_sufficiency_rate: float = 0.0
    self_supply: float = 0.0
    total_consumption: float = 0.0

    # Grid meter readings (Wh)
    grid_meter_reading_negative: float = 0.0
    grid_meter_reading_positive: float = 0.0

    # Aggregate battery (from "battery" key)
    battery_capacity: float = 0.0
    battery_charge: float = 0.0
    battery_discharge: float = 0.0
    battery_nominal_capacity: float = 0.0
    battery_power: float = 0.0
    battery_remaining_charge: float = 0.0
    battery_state_of_charge: float = 0.0

    # Individual appliances
    batteries: list[GridxBattery] = field(default_factory=list)
    heat_pumps: list[GridxHeatPump] = field(default_factory=list)
    ev_charging_stations: list[GridxEVChargingStation] = field(default_factory=list)
    heaters: list[GridxHeater] = field(default_factory=list)


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse an ISO 8601 UTC datetime string."""
    if not value:
        return None
    if not isinstance(value, str):
        return None
    try:
        # Python 3.11+ supports Z suffix; for older versions replace it
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_float(value: Any) -> float:
    """Parse a numeric field, defaulting invalid values to 0.0."""
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _parse_string(value: Any) -> str:
    """Parse a string field, defaulting missing values to an empty string."""
    if value is None:
        return ""
    return value if isinstance(value, str) else str(value)


def _parse_object(value: Any) -> dict[str, Any]:
    """Return a dictionary payload or an empty dict for invalid values."""
    return value if isinstance(value, dict) else {}


def _parse_object_list(value: Any) -> list[dict[str, Any]]:
    """Return only dictionary items from a list payload."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _parse_battery(raw: dict[str, Any]) -> GridxBattery:
    return GridxBattery(
        appliance_id=_parse_string(raw.get("applianceID")),
        capacity=_parse_float(raw.get("capacity")),
        charge=_parse_float(raw.get("charge")),
        discharge=_parse_float(raw.get("discharge")),
        nominal_capacity=_parse_float(raw.get("nominalCapacity")),
        power=_parse_float(raw.get("power")),
        remaining_charge=_parse_float(raw.get("remainingCharge")),
        state_of_charge=_parse_float(raw.get("stateOfCharge")),
    )


def _parse_heat_pump(raw: dict[str, Any]) -> GridxHeatPump:
    return GridxHeatPump(
        appliance_id=_parse_string(raw.get("applianceID")),
        power=_parse_float(raw.get("power")),
        sg_ready_state=_parse_string(raw.get("sgReadyState")),
    )


def _parse_ev_charging_station(raw: dict[str, Any]) -> GridxEVChargingStation:
    return GridxEVChargingStation(
        appliance_id=_parse_string(raw.get("applianceID")),
        power=_parse_float(raw.get("power")),
        state_of_charge=_parse_float(raw.get("stateOfCharge")),
        current_l1=_parse_float(raw.get("currentL1")),
        current_l2=_parse_float(raw.get("currentL2")),
        current_l3=_parse_float(raw.get("currentL3")),
        reading_total=_parse_float(raw.get("readingTotal")),
    )


def _parse_heater(raw: dict[str, Any]) -> GridxHeater:
    return GridxHeater(
        appliance_id=_parse_string(raw.get("applianceID")),
        power=_parse_float(raw.get("power")),
        temperature=_parse_float(raw.get("temperature")),
    )


def parse_live_data(data: dict[str, Any]) -> GridxSystemData:
    """Parse a raw gridX /live API response into a GridxSystemData instance."""

    # Aggregate battery
    bat = _parse_object(data.get("battery"))

    return GridxSystemData(
        measured_at=_parse_datetime(data.get("measuredAt")),
        consumption=_parse_float(data.get("consumption")),
        direct_consumption=_parse_float(data.get("directConsumption")),
        direct_consumption_ev=_parse_float(data.get("directConsumptionEV")),
        direct_consumption_heat_pump=_parse_float(data.get("directConsumptionHeatPump")),
        direct_consumption_heater=_parse_float(data.get("directConsumptionHeater")),
        direct_consumption_household=_parse_float(data.get("directConsumptionHousehold")),
        direct_consumption_rate=_parse_float(data.get("directConsumptionRate")),
        grid=_parse_float(data.get("grid")),
        heat_pump=_parse_float(data.get("heatPump")),
        photovoltaic=_parse_float(data.get("photovoltaic")),
        production=_parse_float(data.get("production")),
        self_consumption=_parse_float(data.get("selfConsumption")),
        self_consumption_rate=_parse_float(data.get("selfConsumptionRate")),
        self_sufficiency_rate=_parse_float(data.get("selfSufficiencyRate")),
        self_supply=_parse_float(data.get("selfSupply")),
        total_consumption=_parse_float(data.get("totalConsumption")),
        grid_meter_reading_negative=_parse_float(data.get("gridMeterReadingNegative")),
        grid_meter_reading_positive=_parse_float(data.get("gridMeterReadingPositive")),
        battery_capacity=_parse_float(bat.get("capacity")),
        battery_charge=_parse_float(bat.get("charge")),
        battery_discharge=_parse_float(bat.get("discharge")),
        battery_nominal_capacity=_parse_float(bat.get("nominalCapacity")),
        battery_power=_parse_float(bat.get("power")),
        battery_remaining_charge=_parse_float(bat.get("remainingCharge")),
        battery_state_of_charge=_parse_float(bat.get("stateOfCharge")),
        batteries=[_parse_battery(b) for b in _parse_object_list(data.get("batteries"))],
        heat_pumps=[_parse_heat_pump(hp) for hp in _parse_object_list(data.get("heatPumps"))],
        ev_charging_stations=[
            _parse_ev_charging_station(ev)
            for ev in _parse_object_list(data.get("evChargingStations"))
        ],
        heaters=[_parse_heater(h) for h in _parse_object_list(data.get("heaters"))],
    )
