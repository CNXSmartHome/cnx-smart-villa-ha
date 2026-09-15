"""Home Assistant compatibility guard for CNX Smart Villa."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Final

from homeassistant.const import MAJOR_VERSION, MINOR_VERSION, PATCH_VERSION, __version__
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN, VERSION

TESTED_HA_SERIES: Final = frozenset({(2026, 9)})
MIN_SUPPORTED_HA_SERIES: Final = (2026, 9)
POLICY_NAME: Final = "CNX validated production series"
REPAIR_ISSUE_ID: Final = "untested_home_assistant_version"
LEARN_MORE_URL: Final = "https://github.com/CNXSmartHome/cnx-smart-villa-ha#home-assistant-version-policy"


@dataclass(frozen=True, slots=True)
class CompatibilityInfo:
    """Compatibility result exposed to the panel and system health."""

    home_assistant_version: str
    integration_version: str
    status: str
    tested: bool
    stable: bool
    tested_series: str
    minimum_series: str
    policy: str

    def as_dict(self) -> dict[str, str | bool]:
        """Return a JSON-compatible compatibility payload."""
        return asdict(self)


def _series_label(series: tuple[int, int]) -> str:
    return f"{series[0]}.{series[1]}.x"


def _all_tested_series_label() -> str:
    return ", ".join(_series_label(series) for series in sorted(TESTED_HA_SERIES))


def evaluate_version(
    *,
    major: int = MAJOR_VERSION,
    minor: int = MINOR_VERSION,
    patch: str | int = PATCH_VERSION,
    version: str = __version__,
) -> CompatibilityInfo:
    """Evaluate the running Home Assistant version without blocking startup."""
    series = (int(major), int(minor))
    stable = str(patch).isdigit()

    if not stable:
        status = "development"
        tested = False
    elif series in TESTED_HA_SERIES:
        status = "tested"
        tested = True
    elif series < MIN_SUPPORTED_HA_SERIES:
        status = "unsupported_older"
        tested = False
    elif series > max(TESTED_HA_SERIES):
        status = "untested_newer"
        tested = False
    else:
        status = "untested"
        tested = False

    return CompatibilityInfo(
        home_assistant_version=version,
        integration_version=VERSION,
        status=status,
        tested=tested,
        stable=stable,
        tested_series=_all_tested_series_label(),
        minimum_series=_series_label(MIN_SUPPORTED_HA_SERIES),
        policy=POLICY_NAME,
    )


def update_version_repair(hass: HomeAssistant) -> CompatibilityInfo:
    """Create or clear a user-visible repair for an unvalidated HA version."""
    info = evaluate_version()
    if info.tested:
        ir.async_delete_issue(hass, DOMAIN, REPAIR_ISSUE_ID)
        return info

    severity = (
        ir.IssueSeverity.ERROR
        if info.status == "unsupported_older"
        else ir.IssueSeverity.WARNING
    )
    ir.async_create_issue(
        hass,
        DOMAIN,
        REPAIR_ISSUE_ID,
        is_fixable=False,
        severity=severity,
        translation_key=REPAIR_ISSUE_ID,
        translation_placeholders={
            "home_assistant_version": info.home_assistant_version,
            "integration_version": info.integration_version,
            "tested_series": info.tested_series,
        },
        learn_more_url=LEARN_MORE_URL,
    )
    return info
