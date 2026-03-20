"""Diagnostics for gridX integration."""

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

REDACT_KEYS = {"email", "password", "access_token", "refresh_token", "id_token"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    return async_redact_data(
        {
            "config_entry": entry.as_dict(),
            "coordinator_data": {
                system_id: {
                    "production": data.production,
                    "consumption": data.consumption,
                    "grid": data.grid,
                    "photovoltaic": data.photovoltaic,
                    "batteries": len(data.batteries),
                    "heat_pumps": len(data.heat_pumps),
                    "ev_charging_stations": len(data.ev_charging_stations),
                    "heaters": len(data.heaters),
                }
                for system_id, data in coordinator.data.items()
            },
        },
        REDACT_KEYS,
    )
