"""Constants for CNX Smart Villa."""
from __future__ import annotations

from typing import Final

DOMAIN: Final = "cnx_smart_villa"
NAME: Final = "CNX Smart Villa"
VERSION: Final = "0.1.0"

CONF_SMART_VILLA_URL: Final = "smart_villa_url"
CONF_API_TOKEN: Final = "api_token"

DEFAULT_SMART_VILLA_URL: Final = ""

PANEL_URL: Final = "cnx-smart-villa"
PANEL_TITLE: Final = "CNX Smart Villa"
PANEL_ICON: Final = "mdi:home-automation"
PANEL_ELEMENT: Final = "cnx-smart-villa-panel"
PANEL_MODULE_URL: Final = "/cnx_smart_villa/cnx-smart-villa-panel.js"

STORAGE_KEY: Final = "cnx_smart_villa.mappings"
STORAGE_VERSION: Final = 1

DATA_STORE: Final = "store"
DATA_API: Final = "api"
DATA_WS_REGISTERED: Final = "ws_registered"
DATA_PANEL_REGISTERED: Final = "panel_registered"

SUPPORTED_DOMAINS: Final = frozenset(
    {
        "light",
        "switch",
        "climate",
        "cover",
        "media_player",
        "scene",
        "sensor",
        "binary_sensor",
    }
)

GUEST_CONTROLLABLE_DOMAINS: Final = frozenset(
    {"light", "switch", "climate", "cover", "media_player", "scene"}
)

CRITICALITY_VALUES: Final = ("COMFORT", "MONITOR", "CRITICAL")
CATEGORY_VALUES: Final = (
    "LIGHTING",
    "SMART_PLUG",
    "AIR_CONDITIONER",
    "CURTAIN",
    "TV_MEDIA",
    "DOOR_WINDOW_SENSOR",
    "MOTION_SENSOR",
    "LEAK_SENSOR",
    "SMOKE_DETECTOR",
    "OTHER",
)
