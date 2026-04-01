"""Sensor platform for the gridX integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.sensor import RestoreSensor
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COORDINATOR_HISTORICAL, COORDINATOR_LIVE, DOMAIN, SG_READY_STATES
from .coordinator import GridxCoordinator, GridxHistoricalCoordinator
from .models import GridxSystemData


# ---------------------------------------------------------------------------
# Entity description dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GridxSystemSensorDescription(SensorEntityDescription):
    """Describes a system-level gridX sensor."""

    value_fn: Callable[[GridxSystemData], StateType] = lambda _: None


@dataclass(frozen=True)
class GridxApplianceSensorDescription(SensorEntityDescription):
    """Describes an appliance-level gridX sensor."""

    value_fn: Callable[[Any], StateType] = lambda _: None


@dataclass(frozen=True)
class GridxHistoricalSystemSensorDescription(SensorEntityDescription):
    """Describes a historical system-level gridX sensor."""

    value_fn: Callable[[dict[str, Any]], StateType] = lambda _: None


# ---------------------------------------------------------------------------
# System-level sensor descriptions (17 total)
# ---------------------------------------------------------------------------

SYSTEM_SENSOR_DESCRIPTIONS: tuple[GridxSystemSensorDescription, ...] = (
    GridxSystemSensorDescription(
        key="production",
        translation_key="production",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda d: d.production,
    ),
    GridxSystemSensorDescription(
        key="photovoltaic",
        translation_key="photovoltaic",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda d: d.photovoltaic,
    ),
    GridxSystemSensorDescription(
        key="consumption",
        translation_key="consumption",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda d: d.consumption,
    ),
    GridxSystemSensorDescription(
        key="total_consumption",
        translation_key="total_consumption",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda d: d.total_consumption,
    ),
    GridxSystemSensorDescription(
        key="grid",
        translation_key="grid",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda d: d.grid,
    ),
    GridxSystemSensorDescription(
        key="self_consumption",
        translation_key="self_consumption",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda d: d.self_consumption,
    ),
    GridxSystemSensorDescription(
        key="self_supply",
        translation_key="self_supply",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda d: d.self_supply,
    ),
    GridxSystemSensorDescription(
        key="self_consumption_rate",
        translation_key="self_consumption_rate",
        native_unit_of_measurement=PERCENTAGE,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: round(d.self_consumption_rate * 100, 10),
    ),
    GridxSystemSensorDescription(
        key="self_sufficiency_rate",
        translation_key="self_sufficiency_rate",
        native_unit_of_measurement=PERCENTAGE,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: round(d.self_sufficiency_rate * 100, 10),
    ),
    GridxSystemSensorDescription(
        key="direct_consumption_household",
        translation_key="direct_consumption_household",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda d: d.direct_consumption_household,
    ),
    GridxSystemSensorDescription(
        key="direct_consumption_heat_pump",
        translation_key="direct_consumption_heat_pump",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda d: d.direct_consumption_heat_pump,
    ),
    GridxSystemSensorDescription(
        key="direct_consumption_ev",
        translation_key="direct_consumption_ev",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda d: d.direct_consumption_ev,
    ),
    GridxSystemSensorDescription(
        key="direct_consumption_heater",
        translation_key="direct_consumption_heater",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda d: d.direct_consumption_heater,
    ),
    GridxSystemSensorDescription(
        key="direct_consumption_rate",
        translation_key="direct_consumption_rate",
        native_unit_of_measurement=PERCENTAGE,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        entity_registry_visible_default=False,
        value_fn=lambda d: round(d.direct_consumption_rate * 100, 10),
    ),
    GridxSystemSensorDescription(
        key="heat_pump",
        translation_key="heat_pump",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda d: d.heat_pump,
    ),
    # NOTE: The gridX API returns meter readings in Ws (watt-seconds / joules),
    # not Wh. See OpenAPI spec: "Meter reading for grid in Ws".
    # Convert Ws → Wh by dividing by 3600.
    GridxSystemSensorDescription(
        key="grid_meter_reading_negative",
        translation_key="grid_meter_reading_negative",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        value_fn=lambda d: d.grid_meter_reading_negative / 3600,
    ),
    GridxSystemSensorDescription(
        key="grid_meter_reading_positive",
        translation_key="grid_meter_reading_positive",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        value_fn=lambda d: d.grid_meter_reading_positive / 3600,
    ),
)

HISTORICAL_SYSTEM_SENSOR_DESCRIPTIONS: tuple[
    GridxHistoricalSystemSensorDescription, ...
] = (
    GridxHistoricalSystemSensorDescription(
        key="hist_battery_charge",
        translation_key="hist_battery_charge",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=0,
        entity_registry_enabled_default=False,
        value_fn=lambda data: _nested_float(data, "battery", "charge"),
    ),
    GridxHistoricalSystemSensorDescription(
        key="hist_battery_discharge",
        translation_key="hist_battery_discharge",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=0,
        entity_registry_enabled_default=False,
        value_fn=lambda data: _nested_float(data, "battery", "discharge"),
    ),
    GridxHistoricalSystemSensorDescription(
        key="hist_heat_pump_energy",
        translation_key="hist_heat_pump_energy",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=0,
        entity_registry_enabled_default=False,
        value_fn=lambda data: _nested_float(data, "heatPump"),
    ),
    GridxHistoricalSystemSensorDescription(
        key="hist_direct_consumption_heat_pump",
        translation_key="hist_direct_consumption_heat_pump",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=0,
        entity_registry_enabled_default=False,
        value_fn=lambda data: _nested_float(data, "directConsumptionHeatPump"),
    ),
)

# ---------------------------------------------------------------------------
# Battery sensor descriptions (7 total)
# ---------------------------------------------------------------------------

BATTERY_SENSOR_DESCRIPTIONS: tuple[GridxApplianceSensorDescription, ...] = (
    GridxApplianceSensorDescription(
        key="battery_state_of_charge",
        translation_key="battery_state_of_charge",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda b: round(b.state_of_charge * 100, 10),
    ),
    GridxApplianceSensorDescription(
        key="battery_power",
        translation_key="battery_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda b: b.power,
    ),
    GridxApplianceSensorDescription(
        key="battery_charge",
        translation_key="battery_charge",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda b: b.charge,
    ),
    GridxApplianceSensorDescription(
        key="battery_discharge",
        translation_key="battery_discharge",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda b: b.discharge,
    ),
    GridxApplianceSensorDescription(
        key="battery_remaining_charge",
        translation_key="battery_remaining_charge",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda b: b.remaining_charge,
    ),
    GridxApplianceSensorDescription(
        key="battery_capacity",
        translation_key="battery_capacity",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda b: b.capacity,
    ),
    GridxApplianceSensorDescription(
        key="battery_nominal_capacity",
        translation_key="battery_nominal_capacity",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda b: b.nominal_capacity,
    ),
)

# ---------------------------------------------------------------------------
# Heat pump sensor descriptions (2 total)
# ---------------------------------------------------------------------------

HEAT_PUMP_SENSOR_DESCRIPTIONS: tuple[GridxApplianceSensorDescription, ...] = (
    GridxApplianceSensorDescription(
        key="heat_pump_power",
        translation_key="heat_pump_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda hp: hp.power,
    ),
    GridxApplianceSensorDescription(
        key="heat_pump_sg_ready_state",
        translation_key="heat_pump_sg_ready_state",
        native_unit_of_measurement=None,
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        options=SG_READY_STATES,
        value_fn=lambda hp: (
            hp.sg_ready_state if hp.sg_ready_state in SG_READY_STATES else None
        ),
    ),
)

# ---------------------------------------------------------------------------
# EV charger sensor descriptions (6 total)
# ---------------------------------------------------------------------------

EV_CHARGER_SENSOR_DESCRIPTIONS: tuple[GridxApplianceSensorDescription, ...] = (
    GridxApplianceSensorDescription(
        key="ev_charger_power",
        translation_key="ev_charger_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda ev: ev.power,
    ),
    GridxApplianceSensorDescription(
        key="ev_charger_state_of_charge",
        translation_key="ev_charger_state_of_charge",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda ev: round(ev.state_of_charge * 100, 10),
    ),
    GridxApplianceSensorDescription(
        key="ev_charger_current_l1",
        translation_key="ev_charger_current_l1",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda ev: ev.current_l1,
    ),
    GridxApplianceSensorDescription(
        key="ev_charger_current_l2",
        translation_key="ev_charger_current_l2",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda ev: ev.current_l2,
    ),
    GridxApplianceSensorDescription(
        key="ev_charger_current_l3",
        translation_key="ev_charger_current_l3",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda ev: ev.current_l3,
    ),
    GridxApplianceSensorDescription(
        key="ev_charger_reading_total",
        translation_key="ev_charger_reading_total",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        value_fn=lambda ev: ev.reading_total,
    ),
)

# ---------------------------------------------------------------------------
# Heater sensor descriptions (2 total)
# ---------------------------------------------------------------------------

HEATER_SENSOR_DESCRIPTIONS: tuple[GridxApplianceSensorDescription, ...] = (
    GridxApplianceSensorDescription(
        key="heater_power",
        translation_key="heater_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda h: h.power,
    ),
    GridxApplianceSensorDescription(
        key="heater_temperature",
        translation_key="heater_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda h: h.temperature,
    ),
)


# ---------------------------------------------------------------------------
# Helper: appliance device naming
# ---------------------------------------------------------------------------


def _appliance_device_name(base_name: str, index: int, total: int) -> str:
    """Return the device name for an appliance at the given index."""
    if total == 1 or index == 0:
        return base_name
    return f"{base_name} {index + 1}"


def _nested_float(data: dict[str, Any], *keys: str) -> float:
    """Read a nested numeric value from a dictionary."""
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return 0.0
        current = current.get(key)

    try:
        return float(current)
    except (TypeError, ValueError):
        return 0.0


# ---------------------------------------------------------------------------
# Entity classes
# ---------------------------------------------------------------------------


class GridxSystemSensor(CoordinatorEntity[GridxCoordinator], SensorEntity):
    """A sensor representing a system-level gridX metric."""

    _attr_has_entity_name = True
    entity_description: GridxSystemSensorDescription

    def __init__(
        self,
        coordinator: GridxCoordinator,
        system_id: str,
        description: GridxSystemSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._system_id = system_id
        self._attr_unique_id = f"{system_id}_{description.key}"

    @property
    def native_value(self) -> StateType:
        data = self.coordinator.data.get(self._system_id)
        if data is None:
            return None
        return self.entity_description.value_fn(data)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._system_id)},
            name="gridX",
            manufacturer="gridX",
            model="Gateway",
        )


class GridxApplianceSensor(CoordinatorEntity[GridxCoordinator], SensorEntity):
    """A sensor representing an individual appliance metric."""

    _attr_has_entity_name = True
    entity_description: GridxApplianceSensorDescription

    def __init__(
        self,
        coordinator: GridxCoordinator,
        system_id: str,
        appliance_id: str,
        appliance_type: str,
        device_name: str,
        description: GridxApplianceSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._system_id = system_id
        self._appliance_id = appliance_id
        self._appliance_type = appliance_type
        self._attr_unique_id = f"{appliance_id}_{description.key}"
        self._device_name = device_name

    @property
    def native_value(self) -> StateType:
        data = self.coordinator.data.get(self._system_id)
        if data is None:
            return None
        appliances: list[Any] = getattr(data, self._appliance_type, [])
        for appliance in appliances:
            if appliance.appliance_id == self._appliance_id:
                return self.entity_description.value_fn(appliance)
        return None

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._appliance_id)},
            name=self._device_name,
            via_device=(DOMAIN, self._system_id),
        )


class GridxSystemEnergySensor(CoordinatorEntity[GridxCoordinator], RestoreSensor):
    """Accumulates energy (kWh) from a system-level power sensor."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 3

    def __init__(
        self,
        coordinator: GridxCoordinator,
        system_id: str,
        key: str,
        translation_key: str,
        power_fn: Callable[[GridxSystemData], float],
    ) -> None:
        super().__init__(coordinator)
        self._system_id = system_id
        self._power_fn = power_fn
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{system_id}_{key}"
        self._accumulated: float = 0.0
        self._last_update: datetime | None = None

    async def async_added_to_hass(self) -> None:
        """Restore accumulated energy after restart."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_sensor_data()) is not None:
            if last_state.native_value is not None:
                self._accumulated = float(last_state.native_value)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Accumulate energy from power reading."""
        data = self.coordinator.data.get(self._system_id)
        if data is None:
            super()._handle_coordinator_update()
            return

        power_w = self._power_fn(data)
        now = datetime.now(timezone.utc)
        if power_w is not None and self._last_update is not None:
            delta_h = (now - self._last_update).total_seconds() / 3600
            self._accumulated += (abs(power_w) / 1000) * delta_h
        self._last_update = now

        super()._handle_coordinator_update()

    @property
    def native_value(self) -> StateType:
        return round(self._accumulated, 3)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._system_id)},
            name="gridX",
            manufacturer="gridX",
        )


class GridxApplianceEnergySensor(CoordinatorEntity[GridxCoordinator], RestoreSensor):
    """Accumulates energy (kWh) from a power sensor by integrating over time."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 3

    def __init__(
        self,
        coordinator: GridxCoordinator,
        system_id: str,
        appliance_id: str,
        appliance_type: str,
        device_name: str,
        key: str,
        translation_key: str,
        power_fn: Callable[[Any], float],
    ) -> None:
        super().__init__(coordinator)
        self._system_id = system_id
        self._appliance_id = appliance_id
        self._appliance_type = appliance_type
        self._device_name = device_name
        self._power_fn = power_fn
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{appliance_id}_{key}"
        self._accumulated: float = 0.0
        self._last_update: datetime | None = None

    async def async_added_to_hass(self) -> None:
        """Restore accumulated energy after restart."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_sensor_data()) is not None:
            if last_state.native_value is not None:
                self._accumulated = float(last_state.native_value)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Accumulate energy from power reading."""
        data = self.coordinator.data.get(self._system_id)
        if data is None:
            super()._handle_coordinator_update()
            return

        appliances: list[Any] = getattr(data, self._appliance_type, [])
        power_w: float | None = None
        for appliance in appliances:
            if appliance.appliance_id == self._appliance_id:
                power_w = self._power_fn(appliance)
                break

        now = datetime.now(timezone.utc)
        if power_w is not None and self._last_update is not None:
            delta_h = (now - self._last_update).total_seconds() / 3600
            self._accumulated += (power_w / 1000) * delta_h
        self._last_update = now

        super()._handle_coordinator_update()

    @property
    def native_value(self) -> StateType:
        return round(self._accumulated, 3)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._appliance_id)},
            name=self._device_name,
            via_device=(DOMAIN, self._system_id),
        )


class GridxHistoricalSystemSensor(
    CoordinatorEntity[GridxHistoricalCoordinator], SensorEntity
):
    """A sensor representing a historical system-level gridX metric."""

    _attr_has_entity_name = True
    entity_description: GridxHistoricalSystemSensorDescription

    def __init__(
        self,
        coordinator: GridxHistoricalCoordinator,
        system_id: str,
        description: GridxHistoricalSystemSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._system_id = system_id
        self._attr_unique_id = f"{system_id}_{description.key}"

    @property
    def native_value(self) -> StateType:
        data = self.coordinator.data.get(self._system_id)
        if data is None:
            return None
        return self.entity_description.value_fn(data)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._system_id)},
            name="gridX",
            manufacturer="gridX",
            model="Gateway",
        )


# ---------------------------------------------------------------------------
# Entity builder (extracted for testability)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# System-level energy accumulator definitions
# (key, translation_key, power_fn)
# These integrate power (W) into energy (kWh) for the Energy Dashboard.
# Grid uses abs() since grid_import/grid_export are separate sensors
# tracking positive and negative flow independently.
# ---------------------------------------------------------------------------

_SYSTEM_ENERGY_SENSORS: list[tuple[str, str, Callable[[GridxSystemData], float]]] = [
    ("photovoltaic_energy", "photovoltaic_energy", lambda d: d.photovoltaic),
    ("production_energy", "production_energy", lambda d: d.production),
    ("consumption_energy", "consumption_energy", lambda d: d.consumption),
    (
        "total_consumption_energy",
        "total_consumption_energy",
        lambda d: d.total_consumption,
    ),
    ("grid_import_energy", "grid_import_energy", lambda d: max(0.0, d.grid)),
    ("grid_export_energy", "grid_export_energy", lambda d: max(0.0, -d.grid)),
    (
        "self_consumption_energy",
        "self_consumption_energy",
        lambda d: d.self_consumption,
    ),
    ("self_supply_energy", "self_supply_energy", lambda d: d.self_supply),
]


_APPLIANCE_CONFIG: list[tuple[str, str, tuple, str]] = [
    ("batteries", "gridX Battery", BATTERY_SENSOR_DESCRIPTIONS, "batteries"),
    ("heat_pumps", "gridX Heat Pump", HEAT_PUMP_SENSOR_DESCRIPTIONS, "heat_pumps"),
    (
        "ev_charging_stations",
        "gridX EV Charger",
        EV_CHARGER_SENSOR_DESCRIPTIONS,
        "ev_charging_stations",
    ),
    ("heaters", "gridX Heater", HEATER_SENSOR_DESCRIPTIONS, "heaters"),
]


def _build_entities(coordinator: GridxCoordinator) -> list:
    """Build all sensor entities from coordinator data."""
    entities: list = []

    for system_id, system_data in coordinator.data.items():
        # System-level sensors
        for description in SYSTEM_SENSOR_DESCRIPTIONS:
            entities.append(GridxSystemSensor(coordinator, system_id, description))

        # System-level energy accumulators (Riemann integration from power)
        for key, translation_key, power_fn in _SYSTEM_ENERGY_SENSORS:
            entities.append(
                GridxSystemEnergySensor(
                    coordinator=coordinator,
                    system_id=system_id,
                    key=key,
                    translation_key=translation_key,
                    power_fn=power_fn,
                )
            )

        # Appliance-level sensors
        for attr_name, base_name, descriptions, _ in _APPLIANCE_CONFIG:
            appliances: list[Any] = getattr(system_data, attr_name, [])
            total = len(appliances)
            for index, appliance in enumerate(appliances):
                device_name = _appliance_device_name(base_name, index, total)
                for description in descriptions:
                    entities.append(
                        GridxApplianceSensor(
                            coordinator=coordinator,
                            system_id=system_id,
                            appliance_id=appliance.appliance_id,
                            appliance_type=attr_name,
                            device_name=device_name,
                            description=description,
                        )
                    )

        # Energy accumulator sensors for heat pumps
        for index, hp in enumerate(system_data.heat_pumps):
            device_name = _appliance_device_name(
                "gridX Heat Pump", index, len(system_data.heat_pumps)
            )
            entities.append(
                GridxApplianceEnergySensor(
                    coordinator=coordinator,
                    system_id=system_id,
                    appliance_id=hp.appliance_id,
                    appliance_type="heat_pumps",
                    device_name=device_name,
                    key="heat_pump_energy",
                    translation_key="heat_pump_energy",
                    power_fn=lambda h: h.power,
                )
            )

    return entities


def _build_historical_entities(
    coordinator: GridxHistoricalCoordinator,
) -> list[GridxHistoricalSystemSensor]:
    """Build all historical sensor entities from coordinator data."""
    entities: list[GridxHistoricalSystemSensor] = []

    for system_id in coordinator.data:
        for description in HISTORICAL_SYSTEM_SENSOR_DESCRIPTIONS:
            entities.append(
                GridxHistoricalSystemSensor(coordinator, system_id, description)
            )

    return entities


# ---------------------------------------------------------------------------
# Platform setup
# ---------------------------------------------------------------------------


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up gridX sensor entities from a config entry."""
    live_coordinator: GridxCoordinator = entry.runtime_data[COORDINATOR_LIVE]
    historical_coordinator: GridxHistoricalCoordinator = entry.runtime_data[
        COORDINATOR_HISTORICAL
    ]
    async_add_entities(
        _build_entities(live_coordinator)
        + _build_historical_entities(historical_coordinator)
    )
