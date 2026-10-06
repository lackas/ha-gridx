"""DataUpdateCoordinator for gridX."""

import logging
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    GridxApi,
    GridxApiError,
    GridxAuthenticationError,
    GridxConnectionError,
    GridxError,
)
from .const import (
    DEFAULT_SCAN_INTERVAL,
    ERROR_SCAN_INTERVAL_BASE,
    ERROR_SCAN_INTERVAL_MAX,
)
from .models import GridxSystemData

_LOGGER = logging.getLogger(__name__)
HISTORICAL_SCAN_INTERVAL = timedelta(hours=1)


async def _async_handle_update_errors(
    coordinator: DataUpdateCoordinator[Any],
    entry: ConfigEntry,
    update_method: Callable[[], Awaitable[Any]],
) -> Any:
    """Run a coordinator update with shared gridX error handling."""
    try:
        return await update_method()
    except GridxAuthenticationError as err:
        entry.async_start_reauth(coordinator.hass)
        raise UpdateFailed(f"Authentication failed: {err}") from err
    except (GridxConnectionError, GridxApiError) as err:
        if hasattr(coordinator, "_consecutive_errors"):
            coordinator._consecutive_errors += 1
            backoff = min(
                ERROR_SCAN_INTERVAL_BASE * (2 ** (coordinator._consecutive_errors - 1)),
                ERROR_SCAN_INTERVAL_MAX,
            )
            coordinator.update_interval = timedelta(seconds=backoff)
        raise UpdateFailed(f"Error fetching data: {err}") from err


class GridxCoordinator(DataUpdateCoordinator[dict[str, GridxSystemData]]):
    """Coordinate gridX API polling."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, api: GridxApi, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="gridX",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
            config_entry=entry,
        )
        self.api = api
        self._consecutive_errors = 0
        self._gateway_ids: dict[str, str] | None = None
        self._ev_config_failed = False

    async def _async_update_data(self) -> dict[str, GridxSystemData]:
        async def _fetch() -> dict[str, GridxSystemData]:
            system_ids = self.config_entry.data["system_ids"]
            result: dict[str, GridxSystemData] = {}
            for system_id in system_ids:
                result[system_id] = await self.api.async_get_live_data(system_id)
                if result[system_id].ev_charging_stations:
                    await self._async_fetch_ev_configurations(
                        system_id, result[system_id]
                    )
            self._consecutive_errors = 0
            self.update_interval = timedelta(seconds=DEFAULT_SCAN_INTERVAL)
            return result

        return await _async_handle_update_errors(self, self.config_entry, _fetch)

    async def _async_gateway_id(self, system_id: str) -> str:
        """Return the gateway ID of a system, resolved once and cached."""
        if self._gateway_ids is None:
            self._gateway_ids = await self.api.async_get_gateway_ids()
        if system_id not in self._gateway_ids:
            raise GridxApiError(f"No gateway found for system {system_id}")
        return self._gateway_ids[system_id]

    async def _async_fetch_ev_configurations(
        self, system_id: str, data: GridxSystemData
    ) -> None:
        """Attach the EV configurations to the live data.

        A failure leaves the configurations out (control entities become
        unavailable) instead of failing the whole live update.
        """
        try:
            gateway_id = await self._async_gateway_id(system_id)
            for station in data.ev_charging_stations:
                data.ev_configurations[
                    station.appliance_id
                ] = await self.api.async_get_ev_configuration(
                    gateway_id, station.appliance_id
                )
        except GridxError as err:
            _LOGGER.log(
                logging.DEBUG if self._ev_config_failed else logging.WARNING,
                "Could not fetch gridX EV configuration: %s",
                err,
            )
            self._ev_config_failed = True
            return
        self._ev_config_failed = False

    async def async_set_ev_configuration(
        self, system_id: str, appliance_id: str, changes: dict[str, Any]
    ) -> None:
        """Patch the EV configuration and publish the returned state."""
        gateway_id = await self._async_gateway_id(system_id)
        config = await self.api.async_patch_ev_configuration(
            gateway_id, appliance_id, changes
        )
        if (data := self.data.get(system_id)) is not None:
            data.ev_configurations[appliance_id] = config
        self.async_update_listeners()

    async def async_get_ev_capacity(
        self, system_id: str, appliance_id: str
    ) -> float | None:
        """Return the battery capacity (Wh) of the EV profile of a station."""
        for profile in await self.api.async_get_ev_profiles(system_id):
            if appliance_id in (profile.get("chargingStationApplianceIDs") or []):
                return profile.get("capacity")
        return None


class GridxHistoricalCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Coordinate gridX historical API polling."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, api: GridxApi, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="gridX historical",
            update_interval=HISTORICAL_SCAN_INTERVAL,
            config_entry=entry,
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        async def _fetch() -> dict[str, dict[str, Any]]:
            now = dt_util.now()
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

            result: dict[str, dict[str, Any]] = {}
            for system_id in self.config_entry.data["system_ids"]:
                data = await self.api.async_get_historical_data(
                    system_id,
                    start_of_day.astimezone(dt_util.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    now.astimezone(dt_util.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    resolution="1h",
                )
                total = data.get("total")
                if not isinstance(total, dict):
                    raise GridxApiError("Unexpected historical data payload")
                result[system_id] = total

            self.update_interval = HISTORICAL_SCAN_INTERVAL
            return result

        return await _async_handle_update_errors(self, self.config_entry, _fetch)
