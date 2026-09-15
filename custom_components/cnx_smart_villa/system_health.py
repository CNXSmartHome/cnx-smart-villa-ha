"""System health information for CNX Smart Villa."""
from __future__ import annotations

from typing import Any

from homeassistant.components import system_health
from homeassistant.core import HomeAssistant, callback

from .api import SmartVillaApiClient, SmartVillaApiConnectionError
from .const import DATA_API, DATA_STORE, DOMAIN, VERSION
from .store import MappingStore
from .version_guard import evaluate_version


@callback
def async_register(
    hass: HomeAssistant, register: system_health.SystemHealthRegistration
) -> None:
    """Register CNX Smart Villa system health callbacks."""
    register.async_register_info(system_health_info)


async def _smart_villa_status(api: SmartVillaApiClient | None) -> str:
    if api is None or not api.configured:
        return "local_commissioning"
    try:
        health = await api.async_health()
    except SmartVillaApiConnectionError:
        return "unreachable"
    return "connected" if health.ok else "unhealthy"


async def system_health_info(hass: HomeAssistant) -> dict[str, Any]:
    """Return diagnostics visible in Settings -> System -> Repairs -> System information."""
    domain_data = hass.data.get(DOMAIN, {})
    store = domain_data.get(DATA_STORE)
    api = domain_data.get(DATA_API)
    compatibility = evaluate_version()

    mapping_count = len(store.all()) if isinstance(store, MappingStore) else 0
    client = api if isinstance(api, SmartVillaApiClient) else None

    return {
        "integration_version": VERSION,
        "home_assistant_version": compatibility.home_assistant_version,
        "compatibility_status": compatibility.status,
        "tested_home_assistant_series": compatibility.tested_series,
        "production_policy": compatibility.policy,
        "mapping_count": mapping_count,
        "smart_villa_os": await _smart_villa_status(client),
    }
