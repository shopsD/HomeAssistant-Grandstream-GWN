import hashlib
import json
import logging
import time
from typing import Any
from urllib.parse import urlsplit

import aiohttp

from gwn.authentication import GwnConfig, GwnToken
from gwn.constants import Constants

_LOGGER = logging.getLogger(Constants.LOG)

class GwnInterface:
    def __init__(self, config: GwnConfig) -> None:
        self._config: GwnConfig = config
        self._session: aiohttp.ClientSession = aiohttp.ClientSession()
        self._token: GwnToken | None = None

    async def __aenter__(self) -> "GwnInterface":
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        if not self._session.closed:
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
            self._token = await self._headless_login()
        if self._token is not None and self.user_password_login:
            if self._token.authorisation_key is not None:
                response = await self._do_post("app/ssid/device/list",{},json.dumps({"lang":"en","requestDomain":self._config.base_url}),{
                    "Content-Type": "application/json",
                    "authorization": self._token.authorisation_key
                }, False)
                if response is None:
                    self._token.authorisation_key = None
            if self._token.authorisation_key is None:
                self._token.authorisation_key = await self._user_password_login()


    async def _post(self, path: str, body: dict[str, Any], bearer: bool = False) -> dict[str, Any] | None:
        
        await self._ensure_token_valid()
        body_json = json.dumps(body, separators=(",", ":"))
        headers={"Content-Type": "application/json"}
        params: dict[str, str] = {}
        if self._token is None:
            _LOGGER.error("No access token available")
            return None
        if bearer and self._token.authorisation_key is None:
            _LOGGER.error("No authorisation token available")
            return None
        elif bearer:
            if self._token.authorisation_key is not None:
                headers["authorization"] = self._token.authorisation_key
        else:
            timestamp_ms = int(time.time() * 1000)
            
            signature = self._build_signature(
                body=body_json,
                access_token=self._token.access_token,
                timestamp_ms=timestamp_ms
            )
            params = {
                "access_token": self._token.access_token,
                "appID": self._config.app_id,
                "timestamp": str(timestamp_ms),
                "signature": signature
            }
        return await self._do_post(path,params,body_json,headers)

    async def _do_post(self, path: str, params: dict[str, str], body: str, headers: dict[str,str], do_log: bool = True) -> dict[str,Any] | None:
        url = f"{self._config.base_url.rstrip('/')}/{path.lstrip('/')}"
        async with self._session.post(url, params=params, data=body,headers=headers ) as response:
            data = await response.json(content_type=None)

            if response.status != 200:
                if do_log: # for authentication checking
                    _LOGGER.warning(f"Request to '{url}' failed with status {response.status}: {data}")
                return None
            retCode = data.get("retCode")
            if retCode is not None and int(retCode) != 0:
                if do_log: # for authentication checking
                    _LOGGER.warning(f"Request to '{url}' failed with code {retCode}: {data.get('msg')}")
                return None
            if do_log: # for authentication checking
                _LOGGER.debug(f"Request to '{url}' succeeded")
            authorisation = response.headers.get("authorization",None)
            if authorisation:
                data["authorisation"] = authorisation
            return data

    async def _post_paginated(self, path: str, body: dict[str, Any], bearer: bool = False) -> list[dict[str, Any]] | None:
        page_num = 1
        results: list[dict[str, Any]] = []
        page_count = 0
        page_size = self._config.page_size
        while self._config.max_pages < 1 or page_count < self._config.max_pages:
            page_body = dict(body)
            page_body["pageNum"] = page_num
            page_body["pageSize"] = page_size

            response = await self._post(path, page_body, bearer)
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

    async def _headless_login(self) -> GwnToken | None:
        _LOGGER.info("Performing headless authentication")
        url = f"{self._config.base_url.rstrip('/')}/oauth/token"

        params = {
            "client_id": self._config.app_id,
            "client_secret": self._config.secret_key,
            "grant_type": "client_credentials"
        }

        async with self._session.get(url, params=params) as response:
            data = await response.json(content_type=None)

            if response.status != 200:
                _LOGGER.error(f"Token request failed with status {response.status}: {data}")
                return None

            if "access_token" not in data:
                _LOGGER.error(f"Token response missing access_token: {data}")
                return None
            _LOGGER.info("Headless authentication succeeded")
            return GwnToken.from_response(data)

    async def _user_password_login(self) -> str | None:
        _LOGGER.info("Performing username/password authentication")
        parts = urlsplit(self._config.base_url)
        body = {
            "userName": self._config.username,
            "userPwd": self._config.password,
            "serverId": "",
            "code": "",
            "checkCode":"",
            "codeToken":"",
            "lang":"en",
            "browserDomain": parts.netloc or parts.path,
            "checkMFACodeFirst":1
        }
        response = await self._do_post("/user/app/login",{},json.dumps(body),{"Content-Type": "application/json"})
        if response is None:
            _LOGGER.warning("Username/Password authentication failed")
            return None
        _LOGGER.info("Username/Password authentication succeeded")
        return response.get("authorisation", None)

    @property
    def refresh_period(self) -> int:
        return self._config.refresh_period_s

    @property
    def user_password_login(self) -> bool:
        return self._config.username is not None and self._config.password is not None

    async def close(self) -> None:
        await self._session.close()

    async def authenticate(self) -> bool:
        await self._ensure_token_valid()
        return (self._token is not None and (not self.user_password_login or self._token.authorisation_key is not None))

    async def get_all_networks(self) -> list[dict[str, Any]] | None:
        return await self._post_paginated("oapi/v1.0.0/network/list",{})

    async def get_network_data(self, network_id: int) -> dict[str, Any] | None:
        response = await self._post("oapi/v1.0.0/network/detail",{"id": network_id})
        if response is None:
            return None
        return response.get("data", {})

    async def get_all_ssids(self, network_id: str) -> list[dict[str, Any]] | None:
        return await self._post_paginated("oapi/v1.0.0/ssid/list",{ "networkId": network_id})

    async def get_ssid_configuration(self, ssid_id: int) -> dict[str, Any] | None:
        response = await self._post("oapi/v1.0.0/ssid/configuration",{ "id": ssid_id})
        if response is None:
            return None
        data = response.get("data", {})
        return data.get("configuration", {})

    async def get_ssid_devices(self, ssid_id: int) -> list[dict[str, Any]] | None:
        if self.user_password_login:
            return await self._post_paginated("app/ssid/device/list",{
                    "id":ssid_id,
                    "search":"",
                    "order":"",
                    "type":"all",
                    "filter":{
                        "deviceType":"all",
                        "siteId":"all"
                    }
                },True)
        # if username/password login is not available then dont return None as an error
        # and dont try requesting. Return an empty array to trigger fallback behaviour
        return []

    async def get_app_ssid_info(self, ssid_id: int) -> dict[str, Any] | None:
        if not self.user_password_login:
            return {}
        response = await self._post("app/ssid/editItem",{"id":ssid_id},True)
        if response is None:
            return None
        data = response.get("data")
        if data is None:
            return None
        response_data: dict[str, Any] = {}
        for category in data:
            response_data[category["name"]] = category["content"]
        return response_data if len(response_data) > 0 else response_data
    
    async def get_all_devices(self, network_id: str) -> list[dict[str, Any]] | None:
        return await self._post_paginated("oapi/v1.0.0/ap/list",{
            "networkId": network_id,
            "filter": {
                "showType": "all"
            }
        })

    async def get_network_info(self, network_id: int) -> dict[str, Any] | None:
        response = await self._post("oapi/v1.0.0/network/detail",{"id":network_id})
        if not response:
            return None
        return response.get("data", {})

    async def get_device_info_port(self, network_id: int, mac: str) -> dict[str, Any] | None:
        response = await self._post("oapi/v1.0.0/device/info",{"networkId":network_id, "mac": mac})
        if not response:
            return None
        return response.get("data", {})

    async def get_device_info_client(self, mac: str) -> dict[str, Any] | None:
        response = await self._post("oapi/v2.0.0/ap/info",{"mac": [mac]})
        if not response:
            return None
        return response.get("data", {})

    async def get_device_firmware_version(self, network_id: int) -> list[dict[str, Any]] | None:
        response = await self._post("oapi/v1.0.0/upgrade/version",{"networkId": network_id})
        if not response:
            return None
        data = response.get("data", {})
        return data.get("result", [])

    async def get_device_channel_info(self, mac: str) -> list[dict[str, Any]] | None:
        response = await self._post("oapi/v1.0.0/ap/config/channel",{"mac": [mac]})
        if not response:
            return None
        return response.get("data", [])

    async def get_app_device_info(self, mac: str, apType: str) -> list[dict[str, Any]] | None:
        if not self.user_password_login:
            return []
        response = await self._post("app/ap/configure/configItem",{"mac":mac,"apType":apType},True)
        if response is None:
            return None
        return response.get("data",[])

    async def get_app_timezone_info(self) -> dict[str, Any] | None:
        if not self.user_password_login:
            return {}
        response = await self._post("app/timezones?type=0",{},True)
        if response is None:
            return None
        return response

    async def set_ssid_data(self, payload: dict[str, Any] ) -> bool:
        if self._config.no_publish:
            _LOGGER.debug(f"Publish is disabled. SSID not Updated. Payload {payload}")
            return True
        return await self._post("oapi/v1.0.0/ssid/update",payload) is not None

    async def set_device_data(self, payload: dict[str, Any] ) -> bool:
        if self._config.no_publish:
            _LOGGER.debug(f"Publish is disabled. Device not Updated. Payload {payload}")
            return True
        return await self._post("oapi/v1.0.0/ap/config/edit",payload) is not None

    async def reboot_device(self, mac: str) -> bool:
        if self._config.no_publish:
            _LOGGER.debug(f"Publish is disabled. Reboot not sent. Payload {mac}")
            return True
        return await self._post("oapi/v1.0.0/ap/reboot",{"mac":[mac]}) is not None
    
    async def reset_device(self, mac: str) -> bool:
        if self._config.no_publish:
            _LOGGER.debug(f"Publish is disabled. Reset not sent. Payload {mac}")
            return True
        return await self._post("oapi/v1.0.0/ap/reset",{"mac":[mac]}) is not None

    async def update_device(self, mac: str) -> bool:
        if self._config.no_publish:
            _LOGGER.debug(f"Publish is disabled. Update not sent. Payload {mac}")
            return True
        response = await self._post("oapi/v1.0.0/upgrade/add",{"macs":[mac]})
        if response is None:
            return False
        data = response.get("data")
        if data is None:
            return False

        return GwnConfig.normalise_mac(mac) in [GwnConfig.normalise_mac(upgraded_mac) for upgraded_mac in data.get("success_upgrade_macs", [])]

    async def move_device_to_network(self, mac: str, network_id: str) -> bool:
        if self._config.no_publish:
            _LOGGER.debug(f"Publish is disabled. Device Not Moved. Payload {mac} - {network_id}")
            return True
        return await self._post("oapi/v1.0.0/ap/move",{"mac":[mac], "networkId": network_id}) is not None
       
    async def set_network_data(self, payload: dict[str, Any] ) -> bool:
        if self._config.no_publish:
            _LOGGER.debug(f"Publish is disabled. Network not Updated. Payload {payload}")
            return True
        return await self._post("oapi/v1.0.0/network/update",payload) is not None