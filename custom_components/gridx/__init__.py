"""The gridX Energy Management integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import GridxApi
from .coordinator import GridxCoordinator

type GridxConfigEntry = ConfigEntry[GridxCoordinator]

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: GridxConfigEntry) -> bool:
    """Set up gridX from a config entry."""
    api = GridxApi(
        async_get_clientsession(hass),
        entry.data["email"],
        entry.data["password"],
    )
    coordinator = GridxCoordinator(hass, api, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GridxConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
