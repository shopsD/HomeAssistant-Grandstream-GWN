import logging
from dataclasses import dataclass
from typing import Any

import aiohttp

from gwn.constants import Constants
from mqtt.config import AppConfig

_LOGGER = logging.getLogger(Constants.LOG)

@dataclass(slots=True, frozen=True)
class ReleaseInfo:
    tag: str
    items: frozenset[str]
    prerelease: bool
    url: str

class VersionManager:
    def __init__(self, config: AppConfig) -> None:
        self._config: AppConfig = config
        self._update_url: str = "https://github.com/shopsD/homeassistant-grandstream-gwn"
        self._session: aiohttp.ClientSession = aiohttp.ClientSession()
        self._timeout = aiohttp.ClientTimeout(total=15)

        self._is_container: bool = False ##CI-EDIT## This line is modified by the CI workflow

    async def _fetch_releases(self) -> list[dict[str, Any]]:
        headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "User-Agent": f"gwn-mqtt/{Constants.APP_VERSION}",
        }
        async with self._session.get(self._update_url, headers=headers, timeout=self._timeout) as response:
            if response.status != 200:
                _LOGGER.warning(f"Failed to get update version {response.status}")
                return []
            data = await response.json()

        if not isinstance(data, list):
            _LOGGER.warning("Unexpected release response")
        return [item for item in data if isinstance(item, dict)]

    async def _get_latest_release(self) -> ReleaseInfo | None:
        _LOGGER.debug(f"Fetching releases from {self._update_url}")
        releases: list[dict[str, Any]] = await self._fetch_releases()
        for raw_release in releases:
            release = self._parse_release(raw_release)
            if release is not None and self._is_relevant_release(release):
                _LOGGER.debug(f"Found latest release {release}")
                return release
        _LOGGER.debug("No releases were found")
        return None

    def _parse_release(self, release: dict[str, Any]) -> ReleaseInfo | None:
        try:
            _LOGGER.debug("Parsing release data")
            tag: str = release["tag_name"]
            is_prerelease: bool = bool(release.get("prerelease"))
            url: str = release.get("html_url", "")
            body: str = release["body"]

            if is_prerelease and not self._config.allow_pre_release_update:
                return None

            items = self._parse_release_items(body)

            return ReleaseInfo( tag=tag, items=frozenset(items), prerelease=is_prerelease, url=url)
        except Exception as e:
            _LOGGER.warn(f"Failed to parse release info: {e}")
        return None

    def _parse_release_items(self, body: str) -> set[str]:
        for line in body.splitlines():
            if line.startswith("Release Items:"):
                raw_items: str = line.split(":", 1)[1].strip()
                if not raw_items:
                    return set()
                _LOGGER.debug(f"Found release info {raw_items}")
                return { item.strip().lower() for item in raw_items.split(",") if item.strip() }

        return set()

    def _is_relevant_release(self, release: ReleaseInfo) -> bool:
        if not self._is_container and "mqtt-bridge" not in release.items:
            return False

        if self._is_container and "docker" not in release.items:
            return False

        return True

    async def get_latest_version(self) -> str:
        release: ReleaseInfo | None = await self._get_latest_release() if self._config.check_for_updates else None
        return release.tag if release is not None else Constants.APP_VERSION

    async def close(self) -> None:
        await self._session.close()