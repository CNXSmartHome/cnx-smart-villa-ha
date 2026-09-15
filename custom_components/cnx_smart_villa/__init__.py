"""CNX Smart Villa Home Assistant integration."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SmartVillaApiClient
from .const import (
    CONF_API_TOKEN,
    CONF_SMART_VILLA_URL,
    DATA_API,
    DATA_COMPATIBILITY,
    DATA_PANEL_REGISTERED,
    DATA_STORE,
    DATA_WS_REGISTERED,
    DOMAIN,
    PANEL_ELEMENT,
    PANEL_ICON,
    PANEL_MODULE_URL,
    PANEL_TITLE,
    PANEL_URL,
    VERSION,
)
from .store import MappingStore
from .version_guard import update_version_repair
from .websocket import async_register_websocket_commands


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up integration-global frontend and websocket resources once."""
    domain_data = hass.data.setdefault(DOMAIN, {})

    if not domain_data.get("static_registered"):
        frontend_file = Path(__file__).parent / "frontend" / "cnx-smart-villa-panel.js"
        await hass.http.async_register_static_paths(
            [StaticPathConfig(PANEL_MODULE_URL, str(frontend_file), False)]
        )
        domain_data["static_registered"] = True

    if not domain_data.get(DATA_WS_REGISTERED):
        async_register_websocket_commands(hass)
        domain_data[DATA_WS_REGISTERED] = True

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up CNX Smart Villa from a config entry."""
    domain_data = hass.data.setdefault(DOMAIN, {})

    store = MappingStore(hass)
    await store.async_load()
    domain_data[DATA_STORE] = store

    domain_data[DATA_API] = SmartVillaApiClient(
        async_get_clientsession(hass),
        str(entry.data.get(CONF_SMART_VILLA_URL, "")),
        str(entry.data.get(CONF_API_TOKEN, "")),
    )

    # Fail-open compatibility guard: never disable a running villa merely because
    # Home Assistant is newer than the CNX-validated series. Surface a Repair and
    # health warning instead so operators can hold or roll back the Core update.
    domain_data[DATA_COMPATIBILITY] = update_version_repair(hass)

    if not frontend.async_panel_exists(hass, PANEL_URL):
        await panel_custom.async_register_panel(
            hass=hass,
            frontend_url_path=PANEL_URL,
            webcomponent_name=PANEL_ELEMENT,
            sidebar_title=PANEL_TITLE,
            sidebar_icon=PANEL_ICON,
            module_url=f"{PANEL_MODULE_URL}?v={VERSION}",
            require_admin=True,
            config_panel_domain=DOMAIN,
            config={"version": VERSION},
        )
    domain_data[DATA_PANEL_REGISTERED] = True
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the config entry while leaving global websocket/static resources loaded."""
    domain_data = hass.data.get(DOMAIN, {})
    domain_data.pop(DATA_STORE, None)
    domain_data.pop(DATA_API, None)
    domain_data.pop(DATA_COMPATIBILITY, None)

    if frontend.async_panel_exists(hass, PANEL_URL):
        frontend.async_remove_panel(hass, PANEL_URL, warn_if_unknown=False)
    domain_data[DATA_PANEL_REGISTERED] = False
    return True
