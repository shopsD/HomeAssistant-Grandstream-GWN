import logging
import os
from dataclasses import dataclass
from typing import Any

import aiohttp

from gwn.constants import Constants
from mqtt.config import AppConfig

_LOGGER = logging.getLogger(Constants.LOG)

@dataclass(slots=True, frozen=True)
class ReleaseInfo:
    version: str
    created_at: str
    is_prerelease: bool
    url: str

class VersionManager:
    def __init__(self, config: AppConfig) -> None:
        self._config: AppConfig = config
        self._update_url: str = "https://api.github.com/repos/shopsD/homeassistant-grandstream-gwn/releases"
        self._container_update_url: str = "https://api.github.com/users/shopsD/packages/container/homeassistant-grandstream-gwn/versions"
        self._session: aiohttp.ClientSession = aiohttp.ClientSession()
        self._timeout = aiohttp.ClientTimeout(total=15)
        self._is_container: bool = os.getenv("GWN_MQTT_CONTAINER", "").lower() == "true"
        self._pre_release_list: set[str] = set(["alpha","beta","pre-release","release-candidate","a","b","pr","rc"])

    async def _fetch_release_data(self, url: str) -> list[dict[str, Any]]:
        headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "User-Agent": f"gwn-mqtt/{Constants.APP_VERSION}",
        }
        async with self._session.get(url, headers=headers, timeout=self._timeout) as response:
            if response.status != 200:
                _LOGGER.warning(f"Failed to get update version {response.status}")
                return []
            data = await response.json()

        if not isinstance(data, list):
            _LOGGER.warning("Unexpected release response")
        return [item for item in data if isinstance(item, dict)]

    async def _fetch_releases(self) -> list[dict[str, Any]]:
        return await self._fetch_release_data(self._update_url)

    async def _fetch_container_releases(self) -> list[dict[str, Any]]:
        return await self._fetch_release_data(self._container_update_url)

    def _parse_release(self, release: dict[str, Any]) -> ReleaseInfo | None:
        try:
            # if some of these are missing, it is invalid so let it throw and log
            tag: str = release["tag_name"]
            is_prerelease: bool = any(substring in tag for substring in self._pre_release_list)
            url: str = release.get("html_url", "")

            if is_prerelease and not self._config.allow_pre_release_update:
                return None

            return ReleaseInfo(version=tag, created_at="", is_prerelease=is_prerelease, url=url)
        except Exception as e:
            _LOGGER.warn(f"Failed to parse release info: {e}")
        return None

    async def _get_latest_release(self) -> ReleaseInfo | None:
        _LOGGER.debug(f"Fetching releases from {self._update_url}")
        releases: list[dict[str, Any]] = await self._fetch_releases()
        for raw_release in releases: # need to confirm this shows in order
            release = self._parse_release(raw_release)
            if release is not None:
                _LOGGER.debug(f"Found latest release {release.version}")
                return release
        _LOGGER.debug("No releases were found")
        return None

    def _parse_container_release(self, raw: dict[str, Any]) -> ReleaseInfo | None:
        try:
            created_at: str = str(raw.get("created_at", "")).strip()
            html_url: str = str(raw.get("html_url", "")).strip()

            metadata = raw.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}

            container = metadata.get("container", {})
            if not isinstance(container, dict):
                container = {}

            raw_tags = container.get("tags", [])
            if not isinstance(raw_tags, list):
                raw_tags = []

            tags: set[str] = set(str(tag).strip() for tag in raw_tags if str(tag).strip())
            tags.discard("latest")
            if len(tags) != 1:
                return None
            version: str = tags.pop()

            is_prerelease: bool = any(substring in version for substring in self._pre_release_list)
            if is_prerelease and not self._config.allow_pre_release_update:
                return None

            return ReleaseInfo(
                version=version,
                created_at=created_at,
                is_prerelease=is_prerelease,
                url=html_url
            )
        except Exception as e:
            _LOGGER.warning(f"Failed to parse container version: {e}")
            return None

    async def _get_latest_container_release(self) -> ReleaseInfo | None:
        _LOGGER.debug(f"Fetching releases from {self._container_update_url}")
        raw_versions = await self._fetch_container_releases()
        parsed = [item for raw in raw_versions if (item := self._parse_container_release(raw)) is not None]
        if len(parsed) == 0:
            return None
        _LOGGER.debug("Fetched new releases")
        parsed.sort(key=lambda item: item.created_at, reverse=True)
        return parsed[0]

    async def get_latest_version(self) -> str:
        if not self._config.check_for_updates:
            return Constants.APP_VERSION

        if self._is_container:
            version: ReleaseInfo | None = await self._get_latest_container_release()
            return version.version if version is not None else Constants.APP_VERSION

        release: ReleaseInfo | None = await self._get_latest_release()
        return release.version if release is not None else Constants.APP_VERSION

    async def close(self) -> None:
        await self._session.close()
