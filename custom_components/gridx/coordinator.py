"""DataUpdateCoordinator for gridX."""

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import GridxApi, GridxAuthenticationError, GridxConnectionError, GridxApiError
from .const import (
    DEFAULT_SCAN_INTERVAL,
    ERROR_SCAN_INTERVAL_BASE,
    ERROR_SCAN_INTERVAL_MAX,
)
from .models import GridxSystemData

_LOGGER = logging.getLogger(__name__)


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
        try:
            system_ids = self.config_entry.data["system_ids"]
            result = {}
            for system_id in system_ids:
                result[system_id] = await self.api.async_get_live_data(system_id)
            self._consecutive_errors = 0
            self.update_interval = timedelta(seconds=DEFAULT_SCAN_INTERVAL)
            return result
        except GridxAuthenticationError as err:
            self.config_entry.async_start_reauth(self.hass)
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except (GridxConnectionError, GridxApiError) as err:
            self._consecutive_errors += 1
            backoff = min(
                ERROR_SCAN_INTERVAL_BASE * (2 ** (self._consecutive_errors - 1)),
                ERROR_SCAN_INTERVAL_MAX,
            )
            self.update_interval = timedelta(seconds=backoff)
            raise UpdateFailed(f"Error fetching data: {err}") from err
