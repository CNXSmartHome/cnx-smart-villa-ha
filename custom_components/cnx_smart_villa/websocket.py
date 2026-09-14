"""Admin-only websocket API for CNX Smart Villa commissioning."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.websocket_api import ActiveConnection
from homeassistant.core import HomeAssistant, split_entity_id
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .api import SmartVillaApiClient, SmartVillaApiConnectionError
from .const import (
    CATEGORY_VALUES,
    CRITICALITY_VALUES,
    DATA_API,
    DATA_STORE,
    DOMAIN,
    GUEST_CONTROLLABLE_DOMAINS,
    SUPPORTED_DOMAINS,
)
from .helpers import canonical_entity_id, normalize_code
from .store import MappingRecord, MappingStore


def _runtime(hass: HomeAssistant) -> tuple[MappingStore, SmartVillaApiClient]:
    domain_data = hass.data.get(DOMAIN, {})
    store = domain_data.get(DATA_STORE)
    api = domain_data.get(DATA_API)
    if not isinstance(store, MappingStore) or not isinstance(api, SmartVillaApiClient):
        raise RuntimeError("CNX Smart Villa config entry is not loaded")
    return store, api


def _send_not_loaded(connection: ActiveConnection, msg_id: int) -> None:
    connection.send_error(msg_id, "not_loaded", "CNX Smart Villa is not loaded")


def _default_category(domain: str) -> str:
    return {
        "light": "LIGHTING",
        "switch": "SMART_PLUG",
        "climate": "AIR_CONDITIONER",
        "cover": "CURTAIN",
        "media_player": "TV_MEDIA",
        "binary_sensor": "OTHER",
        "sensor": "OTHER",
        "scene": "OTHER",
    }.get(domain, "OTHER")


def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register commissioning websocket commands once per HA process."""
    websocket_api.async_register_command(hass, websocket_list_entities)
    websocket_api.async_register_command(hass, websocket_save_mapping)
    websocket_api.async_register_command(hass, websocket_delete_mapping)
    websocket_api.async_register_command(hass, websocket_status)


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/list_entities"})
@websocket_api.require_admin
def websocket_list_entities(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """List supported HA entities enriched with CNX mapping and hardware metadata."""
    try:
        store, _ = _runtime(hass)
    except RuntimeError:
        _send_not_loaded(connection, msg["id"])
        return

    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    area_registry = ar.async_get(hass)

    result: list[dict[str, Any]] = []
    for entry in entity_registry.entities.values():
        domain, _ = split_entity_id(entry.entity_id)
        if domain not in SUPPORTED_DOMAINS or entry.disabled:
            continue

        state = hass.states.get(entry.entity_id)
        device = device_registry.async_get(entry.device_id) if entry.device_id else None
        area_id = entry.area_id or (device.area_id if device else None)
        area = area_registry.async_get_area(area_id) if area_id else None
        mapping = store.get(entry.id)

        suggested_category = _default_category(domain)
        result.append(
            {
                "entity_id": entry.entity_id,
                "registry_entry_id": entry.id,
                "domain": domain,
                "platform": entry.platform,
                "friendly_name": (
                    state.attributes.get("friendly_name")
                    if state is not None
                    else entry.name or entry.original_name or entry.entity_id
                ),
                "state": state.state if state is not None else "unavailable",
                "available": state is not None and state.state not in {"unavailable", "unknown"},
                "area_id": area_id,
                "area_name": area.name if area else None,
                "device_id": entry.device_id,
                "device_name": (
                    (device.name_by_user or device.name) if device is not None else None
                ),
                "manufacturer": device.manufacturer if device is not None else None,
                "model": device.model if device is not None else None,
                "serial_number": device.serial_number if device is not None else None,
                "suggested_category": suggested_category,
                "mapping": asdict(mapping) if mapping else None,
            }
        )

    result.sort(key=lambda item: (item["mapping"] is not None, item["entity_id"]))
    connection.send_result(msg["id"], result)


SAVE_SCHEMA = {
    vol.Required("type"): f"{DOMAIN}/save_mapping",
    vol.Required("entity_id"): str,
    vol.Required("display_name"): str,
    vol.Required("villa_code"): str,
    vol.Required("zone_code"): str,
    vol.Required("function_code"): str,
    vol.Required("category"): vol.In(CATEGORY_VALUES),
    vol.Required("criticality"): vol.In(CRITICALITY_VALUES),
    vol.Required("guest_controllable"): bool,
    vol.Optional("hardware_id", default=""): str,
    vol.Optional("notes", default=""): str,
    vol.Optional("apply_entity_id", default=True): bool,
}


@websocket_api.websocket_command(SAVE_SCHEMA)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_save_mapping(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Validate, optionally rename, and persist one CNX logical mapping."""
    try:
        store, _ = _runtime(hass)
    except RuntimeError:
        _send_not_loaded(connection, msg["id"])
        return

    current_entity_id = msg["entity_id"]
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(current_entity_id)
    if entry is None:
        connection.send_error(msg["id"], "entity_not_found", "Entity does not exist")
        return

    domain, _ = split_entity_id(current_entity_id)
    if domain not in SUPPORTED_DOMAINS:
        connection.send_error(msg["id"], "unsupported_domain", "Unsupported entity domain")
        return

    villa_code = normalize_code(msg["villa_code"])
    zone_code = normalize_code(msg["zone_code"])
    function_code = normalize_code(msg["function_code"])
    try:
        canonical_id = canonical_entity_id(
            current_entity_id, villa_code, zone_code, function_code
        )
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_mapping", str(err))
        return

    criticality = msg["criticality"]
    guest_controllable = msg["guest_controllable"]
    if guest_controllable and criticality != "COMFORT":
        connection.send_error(
            msg["id"],
            "unsafe_guest_mapping",
            "Guest control is allowed only for COMFORT devices",
        )
        return
    if guest_controllable and domain not in GUEST_CONTROLLABLE_DOMAINS:
        connection.send_error(
            msg["id"],
            "unsafe_guest_mapping",
            f"{domain} entities cannot be guest-controllable",
        )
        return

    target_entity_id = current_entity_id
    if msg["apply_entity_id"] and canonical_id != current_entity_id:
        try:
            updated = entity_registry.async_update_entity(
                current_entity_id, new_entity_id=canonical_id
            )
        except ValueError as err:
            connection.send_error(msg["id"], "rename_failed", str(err))
            return
        target_entity_id = updated.entity_id

    record = MappingRecord(
        registry_entry_id=entry.id,
        entity_id=target_entity_id,
        display_name=msg["display_name"].strip() or target_entity_id,
        villa_code=villa_code,
        zone_code=zone_code,
        function_code=function_code,
        category=msg["category"],
        criticality=criticality,
        guest_controllable=guest_controllable,
        hardware_id=msg["hardware_id"].strip(),
        notes=msg["notes"].strip(),
    )
    await store.async_save(record)
    connection.send_result(
        msg["id"],
        {
            "mapping": asdict(record),
            "canonical_entity_id": canonical_id,
            "renamed": target_entity_id != current_entity_id,
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/delete_mapping",
        vol.Required("entity_id"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_delete_mapping(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Delete a local mapping without altering the HA entity."""
    try:
        store, _ = _runtime(hass)
    except RuntimeError:
        _send_not_loaded(connection, msg["id"])
        return
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(msg["entity_id"])
    if entry is None:
        connection.send_error(msg["id"], "entity_not_found", "Entity does not exist")
        return
    deleted = await store.async_delete(entry.id)
    connection.send_result(msg["id"], {"deleted": deleted})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/status"})
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_status(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Return commissioning and Smart Villa OS connectivity status."""
    try:
        store, api = _runtime(hass)
    except RuntimeError:
        _send_not_loaded(connection, msg["id"])
        return

    health: dict[str, Any] = {"configured": api.configured, "ok": None}
    if api.configured:
        try:
            response = await api.async_health()
        except SmartVillaApiConnectionError as err:
            health.update({"ok": False, "error": str(err)})
        else:
            health.update(
                {"ok": response.ok, "db": response.db, "redis": response.redis}
            )

    connection.send_result(
        msg["id"],
        {"mapping_count": len(store.all()), "smart_villa_os": health},
    )
