"""Shared entity helpers for the gridX integration."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import time, timedelta
from typing import Any

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .api import GridxError
from .const import DOMAIN
from .coordinator import GridxCoordinator

EV_DEVICE_NAME = "gridX EV Charger"


def _appliance_device_name(base_name: str, index: int, total: int) -> str:
    """Return the device name for an appliance at the given index."""
    if total == 1 or index == 0:
        return base_name
    return f"{base_name} {index + 1}"


def _appliance_device_info(
    entity: CoordinatorEntity,
    appliance_id: str,
    device_name: str,
    system_id: str,
) -> DeviceInfo:
    """Build appliance device info linked to its gridX system.

    The system device is registered in async_setup_entry, so the lookup here
    always finds it. If it ever does not, the appliance stays unlinked rather
    than aborting setup.
    """
    device_info = DeviceInfo(
        identifiers={(DOMAIN, appliance_id)},
        name=device_name,
    )
    config_entry = entity.platform.config_entry
    assert config_entry is not None
    system_device = dr.async_get(entity.hass).async_get_device_by_identifier(
        (DOMAIN, system_id), config_entry.entry_id
    )
    if system_device is not None:
        device_info["via_device_id"] = system_device.id
    return device_info


def iter_ev_stations(
    coordinator: GridxCoordinator,
) -> Iterator[tuple[str, str, str]]:
    """Yield (system_id, appliance_id, device_name) for every EV station."""
    for system_id, data in coordinator.data.items():
        total = len(data.ev_charging_stations)
        for index, station in enumerate(data.ev_charging_stations):
            yield (
                system_id,
                station.appliance_id,
                _appliance_device_name(EV_DEVICE_NAME, index, total),
            )


def next_departure(departure: time) -> str:
    """Return the next occurrence of a local time of day as UTC ISO string."""
    now = dt_util.now()
    result = now.replace(
        hour=departure.hour, minute=departure.minute, second=0, microsecond=0
    )
    if result <= now:
        result += timedelta(days=1)
    return result.astimezone(dt_util.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class GridxEVEntity(CoordinatorEntity[GridxCoordinator]):
    """Base for entities controlling the EV configuration of a station."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: GridxCoordinator,
        system_id: str,
        appliance_id: str,
        device_name: str,
        key: str,
    ) -> None:
        super().__init__(coordinator)
        self._system_id = system_id
        self._appliance_id = appliance_id
        self._device_name = device_name
        self._attr_translation_key = key
        self._attr_unique_id = f"{appliance_id}_{key}"

    @property
    def ev_config(self) -> dict[str, Any] | None:
        """Return the stored EV configuration, None if not fetched."""
        data = self.coordinator.data.get(self._system_id)
        if data is None:
            return None
        return data.ev_configurations.get(self._appliance_id)

    @property
    def available(self) -> bool:
        return super().available and self.ev_config is not None

    @property
    def device_info(self) -> DeviceInfo:
        return _appliance_device_info(
            self, self._appliance_id, self._device_name, self._system_id
        )

    async def _async_patch(self, changes: dict[str, Any]) -> None:
        """Send a partial EV configuration to gridX."""
        try:
            await self.coordinator.async_set_ev_configuration(
                self._system_id, self._appliance_id, changes
            )
        except GridxError as err:
            raise HomeAssistantError(
                f"Updating the gridX EV configuration failed: {err}"
            ) from err

    async def _async_soc_changes(self, soc: float) -> dict[str, Any]:
        """Return minRequestedSoc plus the userTotalCapacity gridX requires."""
        capacity = (self.ev_config or {}).get("userTotalCapacity")
        if capacity is None:
            try:
                capacity = await self.coordinator.async_get_ev_capacity(
                    self._system_id, self._appliance_id
                )
            except GridxError as err:
                raise HomeAssistantError(
                    f"Reading the gridX EV profiles failed: {err}"
                ) from err
        if capacity is None:
            raise HomeAssistantError(
                "The vehicle battery capacity is unknown, set up an EV profile "
                "in the gridX app first"
            )
        return {"minRequestedSoc": soc, "userTotalCapacity": capacity}
