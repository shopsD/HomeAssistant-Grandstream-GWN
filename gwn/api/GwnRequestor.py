import hashlib
import json
import logging
import time
from typing import Any

import aiohttp

from gwn.authentication import GwnConfig, GwnToken
from gwn.constants import Constants

_LOGGER = logging.getLogger(Constants.LOG)

class GwnRequestor:
    def __init__(self, config: GwnConfig) -> None:
        self._config:GwnConfig = config
        self._session: aiohttp.ClientSession = aiohttp.ClientSession()
        self._token: GwnToken | None = None

    async def __aenter__(self) -> "GwnRequestor":
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self._session.close()

    def _build_signature(self, body: str, access_token: str, timestamp_ms: int) -> str:
        """
        This is used to build the signature that is required for GWN Manager requests
        """
        body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        params = (
            f"access_token={access_token}"
            f"&appID={self._config.app_id}"
            f"&secretKey={self._config.secret_key}"
            f"&timestamp={timestamp_ms}"
        )
        final = f"&{params}&{body_hash}&"
        return hashlib.sha256(final.encode("utf-8")).hexdigest()

    async def _ensure_token_valid(self) -> None:
        if self._token is None or self._token.is_expired():
            if not await self.authenticate():
                self._token = None

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any] | None:
        await self._ensure_token_valid()

        if self._token is None:
            _LOGGER.error("No access token available")
            return None

        timestamp_ms = int(time.time() * 1000)
        body_json = json.dumps(body, separators=(",", ":"))
        signature = self._build_signature(
            body=body_json,
            access_token=self._token.access_token,
            timestamp_ms=timestamp_ms,
        )

        url = f"{self._config.base_url.rstrip('/')}/{path.lstrip('/')}"
        params = {
            "access_token": self._token.access_token,
            "appID": self._config.app_id,
            "timestamp": str(timestamp_ms),
            "signature": signature,
        }

        async with self._session.post(url, params=params, data=body_json,headers={"Content-Type": "application/json"} ) as response:
            data = await response.json(content_type=None)

            if response.status != 200:
                _LOGGER.warning(f"Request failed with status {response.status}: {data}")
                return None
            retCode = data.get("retCode")
            if retCode and int(retCode) != 0:
                _LOGGER.warning(f"Request failed with code {retCode}: {data.get('msg')}")
                return None
            return data

    async def _post_paginated(self, path: str, body: dict[str, Any]) -> list[dict[str, Any]] | None:
        page_num = 1
        results: list[dict[str, Any]] = []
        page_count = 0
        page_size = self._config.page_size
        while self._config.max_pages < 1 or page_count < self._config.max_pages:
            page_body = dict(body)
            page_body["pageNum"] = page_num
            page_body["pageSize"] = page_size

            response = await self._post(path, page_body)
            if response is None:
                return None
            data = response.get("data", {})
            page_results = data.get("result", [])

            if not isinstance(page_results, list):
                _LOGGER.warning(f"Unexpected paginated response message: {response}")
                return None

            results.extend(page_results)

            if len(page_results) != page_size:
                break

            page_num += 1
            page_count += 1
            
        return results

    @property
    def refresh_period(self) -> int:
        return self._config.refresh_period_s

    async def authenticate(self) -> bool:
        url = f"{self._config.base_url.rstrip('/')}/oauth/token"
        params = {
            "client_id": self._config.app_id,
            "client_secret": self._config.secret_key,
            "grant_type": "client_credentials",
        }

        async with self._session.get(url, params=params) as response:
            data = await response.json(content_type=None)

            if response.status != 200:
                _LOGGER.error(f"Token request failed with status {response.status}: {data}")
                return False

            if "access_token" not in data:
                _LOGGER.error(f"Token response missing access_token: {data}")
                return False

            self._token = GwnToken.from_response(data)
            return self._token is not None

    async def get_all_networks(self) -> list[dict[str, Any]] | None:
        return await self._post_paginated("oapi/v1.0.0/network/list",{})

    async def get_all_ssids(self, network_id: str) -> list[dict[str, Any]] | None:
        return await self._post_paginated("oapi/v1.0.0/ssid/list",{ "networkId": network_id})

    async def get_ssid_configuration(self, ssid_id: int) -> dict[str, Any] | None:
        return await self._post("oapi/v1.0.0/ssid/configuration",{ "id": ssid_id})

    async def get_all_devices(self, network_id: str) -> list[dict[str, Any]] | None:
        return await self._post_paginated("oapi/v1.0.0/ap/list",{
            "networkId": network_id,
            "filter": {
                "showType": "all"
            }
        })

    async def get_device_list_info(self, macs: list[str]) -> dict[str, Any] | None:
        return await self._post("oapi/v1.0.0/ap/info",{"mac": macs})
