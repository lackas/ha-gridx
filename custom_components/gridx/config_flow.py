"""Config flow for gridX integration."""

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import GridxApi, GridxAuthenticationError, GridxConnectionError
from .const import DOMAIN


class GridxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for gridX."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            api = GridxApi(
                async_get_clientsession(self.hass),
                user_input["email"],
                user_input["password"],
            )
            try:
                await api.authenticate()
                system_ids = await api.async_get_gateways()
            except GridxAuthenticationError:
                errors["base"] = "invalid_auth"
            except GridxConnectionError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(system_ids[0])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="gridX Energy Management",
                    data={
                        "email": user_input["email"],
                        "password": user_input["password"],
                        "system_ids": system_ids,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("email"): str,
                    vol.Required("password"): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data) -> ConfigFlowResult:
        """Handle reauth initiation."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None) -> ConfigFlowResult:
        """Handle re-authentication."""
        errors = {}
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])

        if user_input is not None:
            api = GridxApi(
                async_get_clientsession(self.hass),
                entry.data["email"],
                user_input["password"],
            )
            try:
                await api.authenticate()
            except GridxAuthenticationError:
                errors["base"] = "invalid_auth"
            except GridxConnectionError:
                errors["base"] = "cannot_connect"
            else:
                self.hass.config_entries.async_update_entry(
                    entry, data={**entry.data, "password": user_input["password"]}
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required("password"): str}),
            errors=errors,
        )
