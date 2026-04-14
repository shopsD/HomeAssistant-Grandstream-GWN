import hashlib
import json
import time
from typing import Any

import aiohttp

from authentication.GwnAuthConfig import GwnAuthConfig
from authentication.GwnToken import GwnToken


class GwnAuthenticationError(Exception):
    pass


class GwnRequestError(Exception):
    pass


class GwnClient:
    def __init__(self, session: aiohttp.ClientSession, config: GwnAuthConfig) -> None:
        self._session = session
        self._config = config
        self._token: GwnToken | None = None

    def _build_signature(self, body: dict[str, Any], access_token: str, timestamp_ms: int) -> str:
        """
        This is used to build the signature that is required for GWN Manager requests
        """
        body_hash = self._body_hash(body)
        params = (
            f"access_token={access_token}"
            f"&appID={self._config.app_id}"
            f"&secretKey={self._config.secret_key}"
            f"&timestamp={timestamp_ms}"
        )
        final = f"&{params}&{body_hash}&"
        return hashlib.sha256(final.encode("utf-8")).hexdigest()

    def _body_hash(self, body: dict[str, Any]) -> str:
        # Use stable JSON encoding so hashing is deterministic.
        encoded = json.dumps(body, separators=(",", ":"), sort_keys=True)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    async def _ensure_token_valid(self) -> None:
        if self._token is None or self._token.is_expired():
            await self.authenticate()

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        await self._ensure_token_valid()

        if self._token is None:
            raise GwnAuthenticationError("No access token available")

        timestamp_ms = int(time.time() * 1000)
        signature = self._build_signature(
            body=body,
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

        async with self._session.post(url, params=params, json=body) as response:
            data = await response.json(content_type=None)

            if response.status != 200:
                raise GwnRequestError( f"Request failed with status {response.status}: {data}" )

            return data

    async def authenticate(self) -> GwnToken:
        url = f"{self._config.base_url.rstrip('/')}/oauth/token"
        params = {
            "client_id": self._config.client_id,
            "client_secret": self._config.client_secret,
            "grant_type": "client_credentials",
        }

        async with self._session.get(url, params=params) as response:
            data = await response.json(content_type=None)

            if response.status != 200:
                raise GwnAuthenticationError(f"Token request failed with status {response.status}: {data}")

            if "access_token" not in data:
                raise GwnAuthenticationError(f"Token response missing access_token: {data}")

            self._token = GwnToken.from_response(data)
            return self._token

    

    async def get_device_list(self,network_id: str, page_num: int = 1, page_size: int = 50,search: str = "") -> dict[str, Any]:
        return await self._post(
            "oapi/v1.0.0/ap/list",
            {
                "search": search,
                "pageNum": page_num,
                "pageSize": page_size,
                "networkId": network_id,
                "filter": {
                    "showType": "all",
                }
            }
        )

    async def get_network_list(self, page_num: int = 1, page_size: int = 50) -> dict[str, Any]:
        return await self._post(
            "oapi/v1.0.0/network/list",
            {
                "pageNum": page_num,
                "pageSize": page_size,
            }
        )

    
