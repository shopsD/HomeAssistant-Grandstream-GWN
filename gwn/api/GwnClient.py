from typing import Any, cast

from gwn.api.GwnRequestor import GwnRequestor
from gwn.authentication import GwnConfig
from gwn.request_data import GwnDevice
from gwn.request_data import GwnSSID, IsolationMode, MacFiltering, SecurityMode


class GwnClient:
    def __init__(self, config: GwnConfig) -> None:
        self._config = config
        self._requestor = GwnRequestor(config)

    def _normalise_dictionary_data(self, dictionary_data: dict[str, Any] | None) -> dict[str, Any]:
        normalised:dict[str, Any] = {}
        if not dictionary_data:
            return {}
        for entry in dictionary_data:
            normalised[entry["key"]] = entry

        return normalised

    def _normalise_mac(self, mac:str) -> str:
        mac = mac.replace(":", "").replace("-", "").upper()
        return ":".join(mac[i:i+2] for i in range(0, 12, 2))

    def _build_device_data(self, ssid_info: dict[str,GwnSSID], device_info: list[dict[str, Any]]) -> list[GwnDevice]:
        device_list: list[GwnDevice] = []
        for device in device_info:
            basic_info:dict[str, Any] = device[0]
            config_info_port:dict[str, Any] = device[1]
            config_info_client:dict[str, Any] = device[2]
            device_firmware:dict[str, Any] = device[3]
            
            # the sub tables are json objects with 3 parameters: type, key and value so use "key" as a dictionary key
            config_info_port["result"] = self._normalise_dictionary_data(config_info_port["result"])
            config_info_client["g24"] = self._normalise_dictionary_data(config_info_client["g24"])
            config_info_client["g5"] = self._normalise_dictionary_data(config_info_client["g5"])
            config_info_client["g6"] = self._normalise_dictionary_data(config_info_client["g6"])
            device_list.append(GwnDevice(
                status=int(basic_info["status"])==1,
                apType=basic_info["apType"],
                mac=self._normalise_mac(basic_info["mac"]),
                name=basic_info["name"],
                ip=basic_info["ipv4"] if basic_info["ipv4"] is not None else basic_info["ip"],
                upTime=basic_info["upTime"],
                usage=int(basic_info["usage"]),
                upload=int(basic_info["upload"]),
                download=int(basic_info["download"]),
                clients=int(basic_info["clients"]),
                versionFirmware=basic_info["versionFirmware"],
                newFirmware=device_firmware["lastVersion"],
                networkId=basic_info["networkId"],
                ipv6=basic_info["ipv6"],
                wireless=int(config_info_port["wireless"]) == 1,
                vlanCount=int(config_info_port["vlanCount"]),
                ssidNumber=int(config_info_port["ssidNumber"]),
                temperature=config_info_client["temperature"],
                bootVersion=config_info_client["bootVersion"],
                online=int(config_info_port["online"]) == 1,

                deviceType=config_info_port["deviceType"],
                model=config_info_port["model"],
                network=config_info_client["network"],
                usedMemory=config_info_client["usedMemory"],
                cpuUsage=config_info_client["cpuUsage"],
                channelload_2g4=config_info_client["channelload_2g4"],
                channelload_5g=config_info_client["channelload_5g"],
                channelload_6g=config_info_client["channelload_6g"],
                channel_2_4=int(config_info_client["g24"]["channel"]["value"]),
                channel_5=int(config_info_client["g5"]["channel"]["value"]),
                channel_6=int(config_info_client["g6"]["channel"]["value"]),
                ssid=[]
            ))
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
                ssidIsolationMode=(IsolationMode.Radio if config_info["ssidIsolationMode"]=="0" 
                    else IsolationMode.Internet if config_info["ssidIsolationMode"]=="1" 
                    else IsolationMode.Gateway if config_info["ssidIsolationMode"]=="2" 
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

    async def _get_device_data(self, network_id: int,device_response: list[dict[str, Any]] | None, firmware_data: dict[str:dict[str:Any]]) -> list[dict[str, Any]] :
        device_data: list[list[dict[str, Any]]] = []
        if device_response is not None:
            for basic_info in device_response:
                mac = basic_info.get("mac")
                if mac:
                    mac = self._normalise_mac(mac)
                    device_info_port = await self._requestor.get_device_info_port(network_id,mac) or {}
                    device_info_client = await self._requestor.get_device_info_client(mac) or {}
                    device_data.append([basic_info,device_info_port,device_info_client, firmware_data[mac]])
        return device_data

    async def _get_firmware_data(self, network_id: int) -> dict[str:dict[str:Any]]:
        device_firmware = await self._requestor.get_device_firmware_version(int(network_id))
        if device_firmware is None:
            return {}
        firmware_data: dict[str:dict[str:Any]] = {}
        for firmware in device_firmware:
            # mac the MAC actually follow the format of AA:BB:CC:DD:EE:FF instead of AABBCCDDEEFF
            mac = self._normalise_mac(firmware["mac"])
            firmware_data[mac] = firmware
        return firmware_data

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
        device_firmware_data = await self._get_firmware_data(int(network_id))
        device_data = await self._get_device_data(int(network_id),device_response,device_firmware_data)

        ssids = self._build_ssid_data(ssid_data)
        return self._build_device_data(ssids,device_data)

    