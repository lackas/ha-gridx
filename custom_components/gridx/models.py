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
    # Python 3.11+ supports Z suffix; for older versions replace it
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_battery(raw: dict[str, Any]) -> GridxBattery:
    return GridxBattery(
        appliance_id=raw.get("applianceID", ""),
        capacity=float(raw.get("capacity", 0.0)),
        charge=float(raw.get("charge", 0.0)),
        discharge=float(raw.get("discharge", 0.0)),
        nominal_capacity=float(raw.get("nominalCapacity", 0.0)),
        power=float(raw.get("power", 0.0)),
        remaining_charge=float(raw.get("remainingCharge", 0.0)),
        state_of_charge=float(raw.get("stateOfCharge", 0.0)),
    )


def _parse_heat_pump(raw: dict[str, Any]) -> GridxHeatPump:
    return GridxHeatPump(
        appliance_id=raw.get("applianceID", ""),
        power=float(raw.get("power", 0.0)),
        sg_ready_state=raw.get("sgReadyState", ""),
    )


def _parse_ev_charging_station(raw: dict[str, Any]) -> GridxEVChargingStation:
    return GridxEVChargingStation(
        appliance_id=raw.get("applianceID", ""),
        power=float(raw.get("power", 0.0)),
        state_of_charge=float(raw.get("stateOfCharge", 0.0)),
        current_l1=float(raw.get("currentL1", 0.0)),
        current_l2=float(raw.get("currentL2", 0.0)),
        current_l3=float(raw.get("currentL3", 0.0)),
        reading_total=float(raw.get("readingTotal", 0.0)),
    )


def _parse_heater(raw: dict[str, Any]) -> GridxHeater:
    return GridxHeater(
        appliance_id=raw.get("applianceID", ""),
        power=float(raw.get("power", 0.0)),
        temperature=float(raw.get("temperature", 0.0)),
    )


def parse_live_data(data: dict[str, Any]) -> GridxSystemData:
    """Parse a raw gridX /live API response into a GridxSystemData instance."""

    # Aggregate battery
    bat = data.get("battery") or {}

    return GridxSystemData(
        measured_at=_parse_datetime(data.get("measuredAt")),
        consumption=float(data.get("consumption", 0.0)),
        direct_consumption=float(data.get("directConsumption", 0.0)),
        direct_consumption_ev=float(data.get("directConsumptionEV", 0.0)),
        direct_consumption_heat_pump=float(data.get("directConsumptionHeatPump", 0.0)),
        direct_consumption_heater=float(data.get("directConsumptionHeater", 0.0)),
        direct_consumption_household=float(data.get("directConsumptionHousehold", 0.0)),
        direct_consumption_rate=float(data.get("directConsumptionRate", 0.0)),
        grid=float(data.get("grid", 0.0)),
        heat_pump=float(data.get("heatPump", 0.0)),
        photovoltaic=float(data.get("photovoltaic", 0.0)),
        production=float(data.get("production", 0.0)),
        self_consumption=float(data.get("selfConsumption", 0.0)),
        self_consumption_rate=float(data.get("selfConsumptionRate", 0.0)),
        self_sufficiency_rate=float(data.get("selfSufficiencyRate", 0.0)),
        self_supply=float(data.get("selfSupply", 0.0)),
        total_consumption=float(data.get("totalConsumption", 0.0)),
        grid_meter_reading_negative=float(data.get("gridMeterReadingNegative", 0.0)),
        grid_meter_reading_positive=float(data.get("gridMeterReadingPositive", 0.0)),
        battery_capacity=float(bat.get("capacity", 0.0)),
        battery_charge=float(bat.get("charge", 0.0)),
        battery_discharge=float(bat.get("discharge", 0.0)),
        battery_nominal_capacity=float(bat.get("nominalCapacity", 0.0)),
        battery_power=float(bat.get("power", 0.0)),
        battery_remaining_charge=float(bat.get("remainingCharge", 0.0)),
        battery_state_of_charge=float(bat.get("stateOfCharge", 0.0)),
        batteries=[_parse_battery(b) for b in data.get("batteries", [])],
        heat_pumps=[_parse_heat_pump(hp) for hp in data.get("heatPumps", [])],
        ev_charging_stations=[
            _parse_ev_charging_station(ev) for ev in data.get("evChargingStations", [])
        ],
        heaters=[_parse_heater(h) for h in data.get("heaters", [])],
    )
