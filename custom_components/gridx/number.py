"""Number platform for the gridX integration."""

from __future__ import annotations

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import COORDINATOR_LIVE
from .coordinator import GridxCoordinator
from .entity import GridxEVEntity, iter_ev_stations


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up gridX number entities from a config entry."""
    coordinator: GridxCoordinator = entry.runtime_data[COORDINATOR_LIVE]
    entities: list[NumberEntity] = []
    for system_id, appliance_id, device_name in iter_ev_stations(coordinator):
        entities.append(
            GridxEVMinSocNumber(
                coordinator,
                system_id,
                appliance_id,
                device_name,
                "ev_min_requested_soc",
            )
        )
        entities.append(
            GridxEVMaxChargePowerNumber(
                coordinator,
                system_id,
                appliance_id,
                device_name,
                "ev_max_charge_power",
            )
        )
    async_add_entities(entities)


class GridxEVMinSocNumber(GridxEVEntity, NumberEntity):
    """Target SoC for the minimum SoC and departure time charge modes."""

    _attr_device_class = NumberDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 5
    _attr_mode = NumberMode.BOX

    @property
    def native_value(self) -> float | None:
        return (self.ev_config or {}).get("minRequestedSoc")

    async def async_set_native_value(self, value: float) -> None:
        await self._async_patch(await self._async_soc_changes(int(value)))


class GridxEVMaxChargePowerNumber(GridxEVEntity, NumberEntity):
    """Charge power limit, 0 means no limit."""

    _attr_device_class = NumberDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_native_min_value = 0
    _attr_native_max_value = 22000
    _attr_native_step = 100
    _attr_mode = NumberMode.BOX
    _attr_entity_registry_enabled_default = False

    @property
    def native_value(self) -> float | None:
        return (self.ev_config or {}).get("maxChargePower") or 0

    async def async_set_native_value(self, value: float) -> None:
        await self._async_patch({"maxChargePower": int(value) or None})
