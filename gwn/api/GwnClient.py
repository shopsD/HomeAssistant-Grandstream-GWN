from typing import Any

from gwn.api.GwnRequestor import GwnRequestor
from gwn.authentication import GwnConfig
from gwn.request_data import GwnDevice
from gwn.request_data import GwnSSID


class GwnClient:
    def __init__(self, config: GwnConfig) -> None:
        self._config = config
        self._requestor = GwnRequestor(config)


    def _build_device_data(self,basic_info: list[dict[str, Any]] | None, detailed_info: dict[str, Any] | None, ssid_info: dict[str,GwnSSID]) -> list[GwnDevice]:
        device_list: list[GwnDevice] = []
        return device_list

    def _build_ssid_data(self, ssid_info: dict[str, Any]) -> dict[str,GwnSSID]:
        ssid_list: dict[str,GwnSSID] = {}
        return ssid_list

    async def _get_ssid_data(self, network_id: str) -> dict[str, Any]:
        ssid_response = await self._requestor.get_all_ssids(network_id)
        ssid_data: dict[str, Any] = {}
        if ssid_response is not None:
            for result in ssid_response:
                id = result.get("id")
                if id:
                    ssid =  await self._requestor.get_ssid_configuration(int(id))
                    if ssid is not None:
                        ssid_data[id] = ssid
        return ssid_data

    async def _get_device_data(self, device_response: list[dict[str, Any]] | None) -> dict[str, Any] :
        macs: list[str] = []
        if device_response is not None:
            for result in device_response:
                mac = result.get("mac")
                if mac:
                    macs.append(mac)
        return await self._requestor.get_device_list_info(macs) or {}

    @property
    def refresh_period(self) -> int:
        return self._config.refresh_period_s

    async def authenticate(self) -> bool:
        return await self._requestor.authenticate()

    async def get_all_networks(self) -> list[dict[str, Any]] | None:
        return await self._requestor.get_all_networks()

    async def get_all_ssids(self, network_id: str) -> list[dict[str, Any]] | None:
        return await self._requestor.get_all_ssids(network_id)

    async def get_gwn_data(self, network_id: str) -> list[GwnDevice] | None:
        ssid_data = await self._get_ssid_data(network_id)
        device_response = await self._requestor.get_all_devices(network_id)
        device_data = await self._get_device_data(device_response)

        ssids = self._build_ssid_data(ssid_data)
        return self._build_device_data(device_response,device_data,ssids)

    