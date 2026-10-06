"""Time platform for the gridX integration."""

from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import COORDINATOR_LIVE
from .coordinator import GridxCoordinator
from .entity import GridxEVEntity, iter_ev_stations, next_departure


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up gridX time entities from a config entry."""
    coordinator: GridxCoordinator = entry.runtime_data[COORDINATOR_LIVE]
    async_add_entities(
        GridxEVDepartureTime(
            coordinator, system_id, appliance_id, device_name, "ev_departure_time"
        )
        for system_id, appliance_id, device_name in iter_ev_stations(coordinator)
    )


class GridxEVDepartureTime(GridxEVEntity, TimeEntity):
    """Departure time for the departure time charge mode.

    gridX stores a full timestamp but only uses its time of day.
    """

    @property
    def native_value(self) -> time | None:
        value = (self.ev_config or {}).get("departureTimestamp")
        parsed = dt_util.parse_datetime(value) if isinstance(value, str) else None
        if parsed is None:
            return None
        return dt_util.as_local(parsed).time().replace(second=0, microsecond=0)

    async def async_set_value(self, value: time) -> None:
        await self._async_patch({"departureTimestamp": next_departure(value)})
