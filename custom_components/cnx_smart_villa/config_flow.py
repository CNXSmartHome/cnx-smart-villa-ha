"""Config flow for CNX Smart Villa."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SmartVillaApiClient, SmartVillaApiConnectionError
from .const import CONF_API_TOKEN, CONF_SMART_VILLA_URL, DOMAIN, NAME


class CnxSmartVillaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure CNX Smart Villa from the Home Assistant UI."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle initial setup."""
        errors: dict[str, str] = {}

        if user_input is not None:
            url = str(user_input.get(CONF_SMART_VILLA_URL, "")).strip().rstrip("/")
            token = str(user_input.get(CONF_API_TOKEN, "")).strip()

            if url:
                client = SmartVillaApiClient(async_get_clientsession(self.hass), url, token)
                try:
                    await client.async_health()
                except SmartVillaApiConnectionError:
                    errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(DOMAIN)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=NAME,
                        data={CONF_SMART_VILLA_URL: url, CONF_API_TOKEN: token},
                    )
            else:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=NAME,
                    data={CONF_SMART_VILLA_URL: "", CONF_API_TOKEN: ""},
                )

        schema = vol.Schema(
            {
                vol.Optional(CONF_SMART_VILLA_URL, default=""): str,
                vol.Optional(CONF_API_TOKEN, default=""): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Reconfigure Smart Villa OS connection without removing mappings."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            url = str(user_input.get(CONF_SMART_VILLA_URL, "")).strip().rstrip("/")
            token = str(user_input.get(CONF_API_TOKEN, "")).strip()
            if url:
                client = SmartVillaApiClient(async_get_clientsession(self.hass), url, token)
                try:
                    await client.async_health()
                except SmartVillaApiConnectionError:
                    errors["base"] = "cannot_connect"
                else:
                    return self.async_update_reload_and_abort(
                        entry,
                        data_updates={CONF_SMART_VILLA_URL: url, CONF_API_TOKEN: token},
                    )
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={CONF_SMART_VILLA_URL: "", CONF_API_TOKEN: ""},
                )

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SMART_VILLA_URL,
                    default=entry.data.get(CONF_SMART_VILLA_URL, ""),
                ): str,
                vol.Optional(
                    CONF_API_TOKEN,
                    default=entry.data.get(CONF_API_TOKEN, ""),
                ): str,
            }
        )
        return self.async_show_form(
            step_id="reconfigure", data_schema=schema, errors=errors
        )
