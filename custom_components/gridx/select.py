"""Select platform for the gridX integration."""

from __future__ import annotations

from datetime import time

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    COORDINATOR_LIVE,
    EV_CHARGE_MODES,
    EV_DEFAULT_DEPARTURE_HOUR,
    EV_DEFAULT_MIN_SOC,
)
from .coordinator import GridxCoordinator
from .entity import GridxEVEntity, iter_ev_stations, next_departure


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up gridX select entities from a config entry."""
    coordinator: GridxCoordinator = entry.runtime_data[COORDINATOR_LIVE]
    async_add_entities(
        GridxEVChargeModeSelect(
            coordinator, system_id, appliance_id, device_name, "ev_charge_mode"
        )
        for system_id, appliance_id, device_name in iter_ev_stations(coordinator)
    )


class GridxEVChargeModeSelect(GridxEVEntity, SelectEntity):
    """Charge mode of an EV charging station."""

    _attr_options = list(EV_CHARGE_MODES)

    @property
    def current_option(self) -> str | None:
        mode = (self.ev_config or {}).get("chargeMode")
        for option, api_mode in EV_CHARGE_MODES.items():
            if api_mode == mode:
                return option
        return None

    async def async_select_option(self, option: str) -> None:
        config = self.ev_config or {}
        changes = {"chargeMode": EV_CHARGE_MODES[option]}
        # gridX rejects these modes without a target SoC and departure time
        if option in ("min", "departure_time"):
            soc = config.get("minRequestedSoc")
            changes |= await self._async_soc_changes(
                EV_DEFAULT_MIN_SOC if soc is None else soc
            )
        if option == "departure_time":
            changes["departureTimestamp"] = config.get(
                "departureTimestamp"
            ) or next_departure(time(EV_DEFAULT_DEPARTURE_HOUR))
        await self._async_patch(changes)
