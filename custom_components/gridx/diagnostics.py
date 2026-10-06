"""Diagnostics for gridX integration."""

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import COORDINATOR_LIVE

REDACT_KEYS = {"email", "password", "access_token", "refresh_token", "id_token"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data[COORDINATOR_LIVE]
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
                    "ev_charge_modes": [
                        config.get("chargeMode")
                        for config in data.ev_configurations.values()
                    ],
                }
                for system_id, data in coordinator.data.items()
            },
        },
        REDACT_KEYS,
    )
