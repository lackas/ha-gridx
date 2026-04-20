"""DataUpdateCoordinator for gridX."""

import logging
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import GridxApi, GridxApiError, GridxAuthenticationError, GridxConnectionError
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

    async def _async_update_data(self) -> dict[str, GridxSystemData]:
        async def _fetch() -> dict[str, GridxSystemData]:
            system_ids = self.config_entry.data["system_ids"]
            result: dict[str, GridxSystemData] = {}
            for system_id in system_ids:
                result[system_id] = await self.api.async_get_live_data(system_id)
            self._consecutive_errors = 0
            self.update_interval = timedelta(seconds=DEFAULT_SCAN_INTERVAL)
            return result

        return await _async_handle_update_errors(self, self.config_entry, _fetch)


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
                    start_of_day.isoformat(),
                    now.replace(microsecond=0).isoformat(),
                    resolution="1h",
                )
                total = data.get("total")
                if not isinstance(total, dict):
                    raise GridxApiError("Unexpected historical data payload")
                result[system_id] = total

            self.update_interval = HISTORICAL_SCAN_INTERVAL
            return result

        return await _async_handle_update_errors(self, self.config_entry, _fetch)
