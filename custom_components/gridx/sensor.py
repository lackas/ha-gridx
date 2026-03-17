"""Sensor platform for the gridX integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
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
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SG_READY_STATES
from .coordinator import GridxCoordinator
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
    GridxSystemSensorDescription(
        key="grid_meter_reading_negative",
        translation_key="grid_meter_reading_negative",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        value_fn=lambda d: d.grid_meter_reading_negative,
    ),
    GridxSystemSensorDescription(
        key="grid_meter_reading_positive",
        translation_key="grid_meter_reading_positive",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        value_fn=lambda d: d.grid_meter_reading_positive,
    ),
)

# ---------------------------------------------------------------------------
# Battery sensor descriptions (7 total)
# ---------------------------------------------------------------------------

BATTERY_SENSOR_DESCRIPTIONS: tuple[GridxApplianceSensorDescription, ...] = (
    GridxApplianceSensorDescription(
        key="state_of_charge",
        translation_key="battery_state_of_charge",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda b: round(b.state_of_charge * 100, 10),
    ),
    GridxApplianceSensorDescription(
        key="power",
        translation_key="battery_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda b: b.power,
    ),
    GridxApplianceSensorDescription(
        key="charge",
        translation_key="battery_charge",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda b: b.charge,
    ),
    GridxApplianceSensorDescription(
        key="discharge",
        translation_key="battery_discharge",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda b: b.discharge,
    ),
    GridxApplianceSensorDescription(
        key="remaining_charge",
        translation_key="battery_remaining_charge",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda b: b.remaining_charge,
    ),
    GridxApplianceSensorDescription(
        key="capacity",
        translation_key="battery_capacity",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda b: b.capacity,
    ),
    GridxApplianceSensorDescription(
        key="nominal_capacity",
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
        key="power",
        translation_key="heat_pump_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda hp: hp.power,
    ),
    GridxApplianceSensorDescription(
        key="sg_ready_state",
        translation_key="heat_pump_sg_ready_state",
        native_unit_of_measurement=None,
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        options=SG_READY_STATES,
        value_fn=lambda hp: hp.sg_ready_state,
    ),
)

# ---------------------------------------------------------------------------
# EV charger sensor descriptions (6 total)
# ---------------------------------------------------------------------------

EV_CHARGER_SENSOR_DESCRIPTIONS: tuple[GridxApplianceSensorDescription, ...] = (
    GridxApplianceSensorDescription(
        key="power",
        translation_key="ev_charger_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda ev: ev.power,
    ),
    GridxApplianceSensorDescription(
        key="state_of_charge",
        translation_key="ev_charger_state_of_charge",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda ev: round(ev.state_of_charge * 100, 10),
    ),
    GridxApplianceSensorDescription(
        key="current_l1",
        translation_key="ev_charger_current_l1",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda ev: ev.current_l1,
    ),
    GridxApplianceSensorDescription(
        key="current_l2",
        translation_key="ev_charger_current_l2",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda ev: ev.current_l2,
    ),
    GridxApplianceSensorDescription(
        key="current_l3",
        translation_key="ev_charger_current_l3",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda ev: ev.current_l3,
    ),
    GridxApplianceSensorDescription(
        key="reading_total",
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
        key="power",
        translation_key="heater_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda h: h.power,
    ),
    GridxApplianceSensorDescription(
        key="temperature",
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


# ---------------------------------------------------------------------------
# Entity builder (extracted for testability)
# ---------------------------------------------------------------------------

_APPLIANCE_CONFIG: list[tuple[str, str, tuple, str]] = [
    ("batteries", "Battery", BATTERY_SENSOR_DESCRIPTIONS, "batteries"),
    ("heat_pumps", "Heat Pump", HEAT_PUMP_SENSOR_DESCRIPTIONS, "heat_pumps"),
    (
        "ev_charging_stations",
        "EV Charger",
        EV_CHARGER_SENSOR_DESCRIPTIONS,
        "ev_charging_stations",
    ),
    ("heaters", "Heater", HEATER_SENSOR_DESCRIPTIONS, "heaters"),
]


def _build_entities(coordinator: GridxCoordinator) -> list:
    """Build all sensor entities from coordinator data."""
    entities: list = []

    for system_id, system_data in coordinator.data.items():
        # System-level sensors
        for description in SYSTEM_SENSOR_DESCRIPTIONS:
            entities.append(GridxSystemSensor(coordinator, system_id, description))

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
    coordinator: GridxCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(_build_entities(coordinator))
