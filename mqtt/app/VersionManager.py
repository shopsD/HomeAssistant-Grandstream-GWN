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
    url: str
    is_docker: bool
    is_app: bool
    is_library: bool
    is_hacs: bool

class VersionManager:
    def __init__(self, config: AppConfig) -> None:
        self._config: AppConfig = config
        self._update_url: str = "https://api.github.com/repos/shopsD/homeassistant-grandstream-gwn/releases"        
        self._session: aiohttp.ClientSession = aiohttp.ClientSession()
        self._timeout = aiohttp.ClientTimeout(total=15)
        self._is_container: bool = os.getenv("GWN_MQTT_CONTAINER", "").lower() == "true"
        self._pre_release_list: set[str] = set(["alpha","beta","pre-release","release-candidate","a","b","pr","rc"])

    async def _fetch_release_data(self, url: str) -> list[dict[str, Any]]:
        headers: dict[str, str] = {
            "Accept": "application/vnd.github+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json",
            "User-Agent": f"gwn-mqtt/{Constants.APP_VERSION}"
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

    def _parse_release(self, release: dict[str, Any]) -> ReleaseInfo | None:
        try:
            # if some of these are missing, it is invalid so let it throw and log
            name: str = release["name"]
            tag: str = release["tag_name"]
            is_prerelease: bool = bool(release["prerelease"])
            url: str = release.get("html_url", "")

            if is_prerelease and not self._config.allow_pre_release_update:
                return None
            tags: list[str] = tags.lower().split("-")
            targets: str = tags[len(tags)-1] if len(tags) > 1 else ""
            return ReleaseInfo(
                version=tags[0], 
                is_prerelease=is_prerelease, 
                url=url,
                is_docker=targets.contains("d"),
                is_app=targets.contains("a"),
                is_library=targets.contains("l"),
                is_hacs=targets.contains("h")
            )
        except Exception as e:
            _LOGGER.warn(f"Failed to parse release info: {e}")
        return None

    async def _get_latest_release(self) -> ReleaseInfo | None:
        _LOGGER.debug(f"Fetching releases from {self._update_url}")
        releases: list[dict[str, Any]] = await self._fetch_releases()
        for raw_release in releases: # need to confirm this shows in order
            release = self._parse_release(raw_release)
            if release is not None and ((not self._is_container and release.is_app) or (self._is_container and release.is_docker)):                    
                _LOGGER.debug(f"Found latest release {release.version}")
                return release
        _LOGGER.debug("No releases were found")
        return None

    async def get_latest_version(self) -> str:
        if not self._config.check_for_updates:
            return Constants.APP_VERSION

        release: ReleaseInfo | None = await self._get_latest_release()
        return release.version if release is not None else Constants.APP_VERSION

    async def close(self) -> None:
        await self._session.close()
