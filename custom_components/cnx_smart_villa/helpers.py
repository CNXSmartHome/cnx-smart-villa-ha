"""Helper functions for CNX Smart Villa commissioning."""
from __future__ import annotations

import re

from homeassistant.core import split_entity_id

_CODE_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
_VILLA_RE = re.compile(r"^v[0-9]{2,3}$")


def normalize_code(value: str) -> str:
    """Normalize an installer-supplied code into an entity-safe token."""
    value = value.strip().lower().replace(" ", "_").replace("-", "_")
    value = re.sub(r"[^a-z0-9_]", "", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value


def validate_mapping_codes(villa_code: str, zone_code: str, function_code: str) -> None:
    """Validate codes used to generate the canonical entity ID."""
    if not _VILLA_RE.fullmatch(villa_code):
        raise ValueError("villa_code must match v01, v02, ...")
    if not zone_code or not _CODE_RE.fullmatch(zone_code):
        raise ValueError("zone_code must contain lowercase letters/numbers/underscore")
    if not function_code or not _CODE_RE.fullmatch(function_code):
        raise ValueError("function_code must contain lowercase letters/numbers/underscore")


def canonical_entity_id(
    current_entity_id: str, villa_code: str, zone_code: str, function_code: str
) -> str:
    """Build CNX canonical entity ID while preserving the HA domain."""
    domain, _ = split_entity_id(current_entity_id)
    villa = normalize_code(villa_code)
    zone = normalize_code(zone_code)
    function = normalize_code(function_code)
    validate_mapping_codes(villa, zone, function)
    return f"{domain}.{villa}_{zone}_{function}"
