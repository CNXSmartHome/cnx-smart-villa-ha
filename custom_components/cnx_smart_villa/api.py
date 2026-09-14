"""Smart Villa OS API client used by the CNX Home Assistant integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout
from yarl import URL


class SmartVillaApiError(Exception):
    """Base Smart Villa OS API error."""


class SmartVillaApiConnectionError(SmartVillaApiError):
    """Raised when Smart Villa OS is unreachable."""


@dataclass(slots=True)
class SmartVillaHealth:
    """Health response from Smart Villa OS."""

    ok: bool
    db: bool | None = None
    redis: bool | None = None


class SmartVillaApiClient:
    """Minimal async client for Smart Villa OS.

    M10.1 intentionally validates only the public health endpoint. Authenticated
    mapping sync will be added when the server-side integration-token endpoint
    lands; keeping the token here avoids changing the HA config-entry shape later.
    """

    def __init__(self, session: ClientSession, base_url: str, token: str = "") -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._token = token

    @property
    def configured(self) -> bool:
        """Return whether a Smart Villa OS URL is configured."""
        return bool(self._base_url)

    @property
    def base_url(self) -> str:
        """Return configured base URL without credentials."""
        return self._base_url

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def async_health(self) -> SmartVillaHealth:
        """Check Smart Villa OS health."""
        if not self._base_url:
            return SmartVillaHealth(ok=False)

        try:
            url = URL(self._base_url).join(URL("/api/health"))
            async with self._session.get(
                url,
                headers=self._headers(),
                timeout=ClientTimeout(total=5),
            ) as response:
                payload: Any = await response.json(content_type=None)
                if response.status >= 400:
                    raise SmartVillaApiConnectionError(
                        f"Smart Villa OS health returned HTTP {response.status}"
                    )
                if not isinstance(payload, dict):
                    raise SmartVillaApiConnectionError("Invalid health response")
                return SmartVillaHealth(
                    ok=bool(payload.get("ok")),
                    db=payload.get("db") if isinstance(payload.get("db"), bool) else None,
                    redis=(
                        payload.get("redis")
                        if isinstance(payload.get("redis"), bool)
                        else None
                    ),
                )
        except (ClientError, TimeoutError, ValueError) as err:
            raise SmartVillaApiConnectionError(str(err)) from err
