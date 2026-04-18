from typing import Any, cast

from gwn.api.GwnRequestor import GwnRequestor
from gwn.authentication import GwnConfig
from gwn.request_data import GwnDevice
from gwn.request_data import GwnSSID, IsolationMode, MacFiltering, SecurityMode


class GwnClient:
    def __init__(self, config: GwnConfig) -> None:
        self._config = config
        self._requestor = GwnRequestor(config)


    def _build_device_data(self, ssid_info: dict[str,GwnSSID], detailed_info: list[dict[str, Any]]) -> list[GwnDevice]:
        device_list: list[GwnDevice] = []
        return device_list

    def _build_ssid_data(self, ssid_info: dict[str, Any]) -> dict[str,GwnSSID]:
        ssid_list: dict[str,GwnSSID] = {}
        for id in ssid_info:
            basic_info: dict[str, Any] = ssid_info[id][0]
            config_info: dict[str, Any] = ssid_info[id][1]
            ssid_list[id] = GwnSSID(
                id=id,
                ssidName=basic_info["ssidName"],
                wifiEnabled=int(basic_info["wifiEnabled"])==1,
                onlineDevices=int(basic_info["onlineDevices"]),
                scheduleEnabled=int(basic_info["scheduleEnabled"])==1,
                portalEnabled=int(basic_info["portalEnabled"])==1,
                securityMode=cast(SecurityMode, int(basic_info["securityMode"])),
                macFilteringEnabled=cast(MacFiltering,int(basic_info["macFilteringEnabled"])),
                clientIsolationEnabled=int(basic_info["clientIsolationEnabled"])==1,
                ssidIsolationMode=(IsolationMode.Radio if config_info["ssidIsolationMode"]=="Radio" 
                    else IsolationMode.Internet if config_info["ssidIsolationMode"]=="Internet" 
                    else IsolationMode.Gateway if config_info["ssidIsolationMode"]=="Gateway " 
                    else None),
                ssidIsolation=int(config_info["ssidIsolation"])==1,
                ssidSsidHidden=int(config_info["ssidSsidHidden"])==1,
                ssidNewSsidBand=str(config_info["ssidNewSsidBand"]),
                ssidVlanid=int(config_info["ssidVlanid"]) if config_info["ssidVlanid"] is not None else None,
                ssidVlanEnabled=int(config_info["ssidVlan"])==1 if config_info["ssidVlan"] is not None else False,
                ssidEnable=int(config_info["ssidEnable"]) == 1,
                ssidRemark=str(config_info["ssidRemark"]),
                ssidKey=(str(config_info["ssidWpaKey"]) if config_info["ssidWpaKey"] is not None
                    else str(config_info["ssidWepKey"]) if config_info["ssidWepKey"] is not None
                    else None),
                ghz2_4_Enabled="2" in str(config_info["ssidNewSsidBand"]),
                ghz5_Enabled="5" in str(config_info["ssidNewSsidBand"]),
                ghz6_Enabled="6" in str(config_info["ssidNewSsidBand"])
            )
        return ssid_list

    async def _get_ssid_data(self, network_id: str) -> dict[str, Any]:
        ssid_response = await self._requestor.get_all_ssids(network_id)
        ssid_data: dict[str, list[dict[str,Any]]] = {}
        if ssid_response is not None:
            for basic_info in ssid_response:
                id = basic_info.get("id")
                if id:
                    config_info = await self._requestor.get_ssid_configuration(int(id))
                    if config_info is not None:
                        
                        ssid_data[id] = [basic_info,config_info]
        return ssid_data

    async def _get_device_data(self, network_id: int,device_response: list[dict[str, Any]] | None) -> list[dict[str, Any]] :
        device_data: list[dict[str, Any]] = []
        if device_response is not None:
            for result in device_response:
                mac = result.get("mac")
                if mac:
                    device = await self._requestor.get_device_info(network_id,mac) or {}
                    if device:
                        device_data.append(device)
        return device_data

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
        device_data = await self._get_device_data(int(network_id),device_response)

        ssids = self._build_ssid_data(ssid_data)
        return self._build_device_data(ssids,device_data)

    