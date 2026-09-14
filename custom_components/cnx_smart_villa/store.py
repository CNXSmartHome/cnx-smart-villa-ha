"""Persistent commissioning mappings for CNX Smart Villa."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION


@dataclass(slots=True)
class MappingRecord:
    """One Home Assistant registry entity mapped into the CNX logical model."""

    registry_entry_id: str
    entity_id: str
    display_name: str
    villa_code: str
    zone_code: str
    function_code: str
    category: str
    criticality: str
    guest_controllable: bool
    hardware_id: str = ""
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any], storage_key: str) -> "MappingRecord":
        """Build a record from persisted JSON-compatible data."""
        return cls(
            registry_entry_id=str(data.get("registry_entry_id") or storage_key),
            entity_id=str(data["entity_id"]),
            display_name=str(data.get("display_name", "")),
            villa_code=str(data.get("villa_code", "")),
            zone_code=str(data.get("zone_code", "")),
            function_code=str(data.get("function_code", "")),
            category=str(data.get("category", "OTHER")),
            criticality=str(data.get("criticality", "COMFORT")),
            guest_controllable=bool(data.get("guest_controllable", False)),
            hardware_id=str(data.get("hardware_id", "")),
            notes=str(data.get("notes", "")),
        )


class MappingStore:
    """Home Assistant storage wrapper for commissioning data."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._mappings: dict[str, MappingRecord] = {}

    async def async_load(self) -> None:
        """Load mappings from .storage."""
        raw = await self._store.async_load() or {}
        records = raw.get("mappings", {})
        if not isinstance(records, dict):
            records = {}
        self._mappings = {
            storage_key: MappingRecord.from_dict(value, storage_key)
            for storage_key, value in records.items()
            if isinstance(value, dict) and value.get("entity_id")
        }

    def get(self, registry_entry_id: str) -> MappingRecord | None:
        """Get one mapping by stable HA entity-registry entry id."""
        return self._mappings.get(registry_entry_id)

    def all(self) -> dict[str, MappingRecord]:
        """Return a copy of all mappings."""
        return dict(self._mappings)

    async def async_save(self, record: MappingRecord) -> None:
        """Upsert a mapping and persist it."""
        self._mappings[record.registry_entry_id] = record
        await self._persist()

    async def async_delete(self, registry_entry_id: str) -> bool:
        """Delete a mapping; return True if it existed."""
        existed = self._mappings.pop(registry_entry_id, None) is not None
        if existed:
            await self._persist()
        return existed

    async def _persist(self) -> None:
        await self._store.async_save(
            {"mappings": {key: asdict(value) for key, value in self._mappings.items()}}
        )
