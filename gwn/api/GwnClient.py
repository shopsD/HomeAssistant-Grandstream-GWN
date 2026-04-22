import json
import logging
from typing import Any

from gwn.api.GwnInterface import GwnInterface
from gwn.authentication import GwnConfig
from gwn.constants import Constants
from gwn.request_data import GwnDevice, GwnNetwork, GwnSSID, IsolationMode, MacFiltering, SecurityMode

_LOGGER = logging.getLogger(Constants.LOG)

class GwnClient:
    def __init__(self, config: GwnConfig) -> None:
        self._config = config
        self._interface = GwnInterface(config)

    def _normalise_dictionary_data(self, dictionary_data: list[dict[str, Any]] | None) -> dict[str, Any]:
        normalised:dict[str, Any] = {}
        if not dictionary_data:
            return {}
        for entry in dictionary_data:
            normalised[entry["key"]] = entry

        return normalised

    def _build_device_data(self, device_info: list[list[dict[str, Any]]]) -> dict[str, GwnDevice]:
        device_list: dict[str, GwnDevice] = {}
        _LOGGER.info(f"Processing {len(device_info)} Devices")
        for device in device_info:
            try: # use a try catch so that only an individual device failure is ignored
                basic_info: dict[str, Any] = device[0]
                config_info_port: dict[str, Any] = device[1]
                config_info_client: dict[str, Any] = device[2]
                device_firmware: dict[str, Any] = device[3]
                
                # the sub tables are json objects with 3 parameters: type, key and value so use "key" as a dictionary key
                config_info_port["result"] = self._normalise_dictionary_data(config_info_port["result"])
                config_info_client["g24"] = self._normalise_dictionary_data(config_info_client["g24"])
                config_info_client["g5"] = self._normalise_dictionary_data(config_info_client["g5"])
                config_info_client["g6"] = self._normalise_dictionary_data(config_info_client["g6"])
                
                mac= GwnConfig.normalise_mac(basic_info["mac"])
                if mac in self._config.exclude_device:
                    _LOGGER.debug(f"Ignoring Device: {mac}")
                else:
                    gwn_device = GwnDevice(
                        status=int(basic_info["status"])==1,
                        apType=basic_info["apType"],
                        mac=mac,
                        name=basic_info["name"],
                        ip=basic_info["ipv4"] if basic_info["ipv4"] is not None else basic_info["ip"],
                        upTime=basic_info["upTime"],
                        usage=int(basic_info["usage"]),
                        upload=int(basic_info["upload"]),
                        download=int(basic_info["download"]),
                        clients=int(basic_info["clients"]),
                        versionFirmware=basic_info["versionFirmware"],
                        networkId=basic_info["networkId"],
                        ipv6=basic_info["ipv6"],

                        newFirmware=device_firmware["lastVersion"],
                        
                        wireless=int(config_info_port["wireless"]) == 1,
                        vlanCount=int(config_info_port["vlanCount"]),
                        ssidNumber=int(config_info_port["ssidNumber"]),
                        online=int(config_info_port["online"]) == 1,
                        model=config_info_port["model"],
                        deviceType=config_info_port["deviceType"],

                        channel_5=int(config_info_client["g5"]["channel"]["value"]),
                        channel_2_4=int(config_info_client["g24"]["channel"]["value"]),
                        channel_6=int(config_info_client["g6"]["channel"]["value"]),
                        partNumber=config_info_client["partNumber"],
                        bootVersion=config_info_client["bootVersion"],
                        network=config_info_client["network"],
                        temperature=config_info_client["temperature"],
                        usedMemory=config_info_client["usedMemory"],
                        channelload_2g4=config_info_client["channelload_2g4"],
                        cpuUsage=config_info_client["cpuUsage"],
                        channelload_6g=config_info_client["channelload_6g"],
                        channelload_5g=config_info_client["channelload_5g"],
                    )
                    _LOGGER.debug(f"Processed device with MAC {gwn_device.mac}")
                    device_list[mac] = gwn_device
            except Exception as e:
                _LOGGER.error("Failed to process a device %s", e)
        _LOGGER.info(f"Processed {len(device_list)} Devices")
        return device_list

    def _build_ssid_data(self, ssid_info: dict[str, Any], devices: dict[str, GwnDevice]) -> dict[str | int, GwnSSID]:
        ssid_list: dict[str | int,GwnSSID] = {}
        _LOGGER.info(f"Processing {len(ssid_info)} SSIDs")
        for id in ssid_info:
            if int(id) in self._config.exclude_ssid:
                _LOGGER.debug(f"Ignoring SSID: {id}")
            else:
                basic_info: dict[str, Any] = ssid_info[id][0]
                config_info: dict[str, Any] = ssid_info[id][1]
                ssid_device_info: list[dict[str, Any]] = ssid_info[id][2]

                gwn_ssid = GwnSSID(
                    id=id,
                    ssidName=basic_info["ssidName"],
                    wifiEnabled=int(basic_info["wifiEnabled"])==1,
                    onlineDevices=int(basic_info["onlineDevices"]),
                    scheduleEnabled=int(basic_info["scheduleEnabled"])==1,
                    portalEnabled=int(basic_info["portalEnabled"])==1,
                    securityMode=SecurityMode(int(basic_info["securityMode"])),
                    macFilteringEnabled=MacFiltering(int(basic_info["macFilteringEnabled"])),
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
                    ssidKey=(None if int(id) in self._config.exclude_passphrase
                        else str(config_info["ssidWpaKey"]) if config_info["ssidWpaKey"] is not None
                        else str(config_info["ssidWepKey"]) if config_info["ssidWepKey"] is not None
                        else None),
                    ghz2_4_Enabled="2" in str(config_info["ssidNewSsidBand"]),
                    ghz5_Enabled="5" in str(config_info["ssidNewSsidBand"]),
                    ghz6_Enabled="6" in str(config_info["ssidNewSsidBand"]),
                    devices=[]
                )
                
                has_device_info = ssid_device_info is not None and len(ssid_device_info) > 0

                if has_device_info:
                    for device_info in ssid_device_info:
                        mac = GwnConfig.normalise_mac(str(device_info.get("mac")))
                        gwn_device = devices[mac]
                        if gwn_device and bool(device_info.get("checked")):
                            gwn_ssid.devices.append(gwn_device)

                ssid_dictionary_key = int(gwn_ssid.id) if has_device_info else str(gwn_ssid.ssidName)
                if not has_device_info and ssid_dictionary_key in ssid_list:
                    _LOGGER.warning(f"SSIDs with duplicate names found '{gwn_ssid.ssidName}'. Ignoring SSID with ID {gwn_ssid.id}")
                else:
                    ssid_list[ssid_dictionary_key] = gwn_ssid
                _LOGGER.debug(f"Processed SSID: {id} - Key: {ssid_dictionary_key}")
        _LOGGER.info(f"Processed {len(ssid_list)} SSIDs")
        return ssid_list

    async def _get_ssid_data(self, network_id: str) -> dict[str, Any]:
        ssid_response = await self._interface.get_all_ssids(network_id)
        ssid_data: dict[str, list[dict[str,Any] | list[dict[str, Any]] | None]] = {}
        if ssid_response is not None:
            for basic_info in ssid_response:
                id = basic_info.get("id")
                if id is not None:
                    config_info = await self._interface.get_ssid_configuration(int(id))
                    ssid_device_info = await self._interface.get_ssid_devices(int(id))
                    if config_info is not None:
                        ssid_data[id] = [basic_info, config_info, ssid_device_info]
        return ssid_data

    async def _get_device_data(self, network_id: int, device_response: list[dict[str, Any]] | None, firmware_data: dict[str, dict[str, Any]]) -> list[list[dict[str, Any]]] :
        device_data: list[list[dict[str, Any]]] = []
        if device_response is not None:
            for basic_info in device_response:
                mac = basic_info.get("mac")
                if mac:
                    _LOGGER.debug(f"Reqeusting data for {mac}")
                    mac = GwnConfig.normalise_mac(mac)
                    device_info_port = await self._interface.get_device_info_port(network_id,mac) or {}
                    device_info_client = await self._interface.get_device_info_client(mac) or {}
                    device_data.append([basic_info,device_info_port,device_info_client, firmware_data[mac]])
                else:
                    _LOGGER.warning("Found response with missing MAC Address")
        return device_data

    async def _get_firmware_data(self, network_id: int) -> dict[str,dict[str,Any]]:
        device_firmware = await self._interface.get_device_firmware_version(int(network_id))
        if device_firmware is None:
            return {}
        firmware_data: dict[str,dict[str,Any]] = {}
        for firmware in device_firmware:
            # mac the MAC actually follow the format of AA:BB:CC:DD:EE:FF instead of AABBCCDDEEFF
            mac = GwnConfig.normalise_mac(firmware["mac"])
            firmware_data[mac] = firmware
        return firmware_data

    async def _associated_ssids_with_devices(self, ssids: dict[str | int, GwnSSID], devices: dict[str, GwnDevice], device_info: list[list[dict[str, Any]]]):
        for device in device_info:
            try: # use a try catch so that only an individual device failure is ignored
                basic_info: dict[str, Any] = device[0]
                config_info_client: dict[str, Any] = device[2]
                mac = GwnConfig.normalise_mac(basic_info["mac"])
                gwn_device = devices.get(mac)
                if gwn_device:
                    # map SSIDs to the device using SSID name
                    # ideally SSID name will not be used
                    for ssid in config_info_client["ssid"]:
                        # only find ssid if it was a string as this is the ssid name. If its an int, then it is the internal ssid ID
                        ssid_key = str(list(ssid.keys())[0])
                        if ssid_key in ssids: # will be false if it matched via SSID rather than device
                            ssids[ssid_key].devices.append(gwn_device)
            except Exception as e:
                _LOGGER.error("Failed to match Device to SSID: %s", e)

                

    async def _get_network_data(self, network_id: str) -> tuple[list[GwnDevice], list[GwnSSID]]:
        _LOGGER.info(f"Getting Devices for Network: {network_id}")
        ssid_data = await self._get_ssid_data(network_id)
        device_response = await self._interface.get_all_devices(network_id)
        device_firmware_data = await self._get_firmware_data(int(network_id))
        device_data = await self._get_device_data(int(network_id),device_response,device_firmware_data)
        
        devices = self._build_device_data(device_data)
        ssids = self._build_ssid_data(ssid_data, devices)
        await self._associated_ssids_with_devices(ssids, devices, device_data)
        _LOGGER.info(f"Found {len(devices)} Devices for Network: {network_id}")
        _LOGGER.info(f"Found {len(ssids)} SSIDs for Network: {network_id}")
        return list(devices.values()), list(ssids.values())

    @property
    def refresh_period(self) -> int:
        return self._config.refresh_period_s

    async def close(self) -> None:
        await self._interface.close()

    async def authenticate(self) -> bool:
        return await self._interface.authenticate()

    async def get_gwn_data(self) -> list[GwnNetwork]:
        _LOGGER.info("Getting Networks")
        networks = await self._interface.get_all_networks()
        gwn_networks: list[GwnNetwork] = []
        if networks is not None:
            for network in networks:
                try:
                    network_id =  int(network["id"])
                    if network_id in self._config.exclude_network:
                        _LOGGER.debug(f"Ignoring Network: {network_id}")
                    else:
                        _LOGGER.debug(f"Processing Network ID {network_id}")
                        network_data = await self._interface.get_network_info(network_id)
                        if network_data:
                            ssid_device_data = await self._get_network_data(str(network_id))
                            gwn_network = GwnNetwork(
                                id = str(network_id),
                                networkName = str(network_data["networkName"]),
                                countryDisplay = str(network_data["countryDisplay"]),
                                country = str(network_data["country"]),
                                timezone = str(network_data["timezone"]),
                                devices = ssid_device_data[0],
                                ssids = ssid_device_data[1]
                            )
                            gwn_networks.append(gwn_network)
                            _LOGGER.debug(f"Processed Network '{gwn_network.networkName}' with ID {gwn_network.id}")
                except Exception as e:
                    _LOGGER.error("Failed to process a Network: %s", e)
        _LOGGER.info(f"Found {len(gwn_networks)} Networks")
        return gwn_networks

    async def set_ssid_data(self, ssid_id: str, device_macs: list[str], data: dict[str, Any], network_id: str) -> bool:
        ssid_enable = data.get(Constants.SSID_ENABLE, None)
        portal_enabled = data.get(Constants.PORTAL_ENABLED, None)
        vlan_id = data.get(Constants.SSID_VLAN_ID, None)
        vlan_enabled = None if vlan_id is None else int(vlan_id) > 0
        ghz2_4_enabled = data.get(Constants.GHZ2_4_ENABLED, None)
        ghz5_enabled = data.get(Constants.GHZ5_ENABLED, None)
        ghz6_enabled = data.get(Constants.GHZ6_ENABLED, None)
        ssid_key = data.get(Constants.SSID_KEY, None)
        ssid_hidden = data.get(Constants.SSID_HIDDEN, None)
        ssid_name = data.get(Constants.SSID_NAME, None)
        bind_macs = data.get(Constants.TOGGLE_DEVICE, None)
        # first fetch existing data
        config_info = await self._interface.get_ssid_configuration(int(ssid_id))
        if config_info is None:
            _LOGGER.error(f"Failed to fetch existing SSID config for ID {ssid_id}. Update will not be applied")
            return False
        
        # normalise the macs for processing and for transport in the payload
        normalised_device_macs: list[str] = [GwnConfig.normalise_mac(mac) for mac in device_macs]
        original_bind_macs: list[str] = normalised_device_macs

        # try to update the snapshot in case the provided one is stale
        if self._interface.user_password_login:
            stored_macs = await self._interface.get_ssid_devices(int(ssid_id))
            if stored_macs is not None:
                flattened_stored_macs: list[str] = []
                for device_info in stored_macs:
                    mac = GwnConfig.normalise_mac(str(device_info.get("mac")))
                    if bool(device_info.get("checked")):
                        flattened_stored_macs.append(mac)
                original_bind_macs = flattened_stored_macs
                
        # these keys are required as a basic list of the payload
        payload: dict[str, Any] = {
            "id": int(ssid_id),
            "networkId": network_id,
            "ssidSsid": str(config_info.get("ssidSsid")),
            "ssidWepKey": config_info.get("ssidWepKey",None),
            "ssidWpaKey": config_info.get("ssidWpaKey",None),
            "bindMacs": json.dumps(original_bind_macs),
            "ssidTimedClientPolicy": config_info.get("ssidTimedClientPolicy",None),
        }
        ssid_bands = str(config_info.get("ssidNewSsidBand"))
        if ssid_enable is not None:
            payload["ssidEnable"] = int(ssid_enable)
        if portal_enabled is not None:
            payload["ssidPortalEnable"] = int(portal_enabled)
        if vlan_id is not None and vlan_enabled:
            payload["ssidVlanid"] = int(vlan_id)
        if vlan_enabled is not None:
            payload["ssidVlan"] = int(vlan_enabled)
        if ghz2_4_enabled is not None:
            if ghz2_4_enabled and "2" not in ssid_bands:
                ssid_bands = f"{ssid_bands}{',' if len(ssid_bands) > 0 else ''}2"
            elif not ghz2_4_enabled:
                ssid_bands = ssid_bands.replace("2","")
            payload["ssidNewSsidBand"] = ssid_bands
        if ghz5_enabled is not None:
            if ghz5_enabled and "5" not in ssid_bands:
                ssid_bands = f"{ssid_bands}{',' if len(ssid_bands) > 0 else ''}5"
            elif not ghz5_enabled:
                ssid_bands = ssid_bands.replace("5","")
            payload["ssidNewSsidBand"] = ssid_bands
        if ghz6_enabled is not None:
            if ghz6_enabled and "6" not in ssid_bands:
                ssid_bands = f"{ssid_bands}{',' if len(ssid_bands) > 0 else ''}6"
            elif not ghz6_enabled:
                ssid_bands = ssid_bands.replace("6","")
            payload["ssidNewSsidBand"] = ssid_bands
        
        if ssid_key is not None and int(config_info["ssidEncryption"]) < 2:
            payload["ssidWepKey"] = ssid_key
        if ssid_key is not None and int(config_info["ssidEncryption"]) > 1:
            payload["ssidWpaKey"] = ssid_key
        if ssid_hidden is not None:
            payload["ssidSsidHidden"] = int(ssid_hidden)
        if ssid_name is not None:
            payload["ssidSsid"] = str(ssid_name)
        if bind_macs is not None:
            bind_macs = [GwnConfig.normalise_mac(mac) for mac in bind_macs]
            added_macs = [mac for mac in bind_macs if mac not in normalised_device_macs]
            removed_macs = [mac for mac in normalised_device_macs if mac not in bind_macs]
            final_bind_macs = [mac for mac in original_bind_macs if mac not in removed_macs]
            final_bind_macs.extend([mac for mac in added_macs if mac not in final_bind_macs])
            payload["bindMacs"] = final_bind_macs
            if len(removed_macs) > 0:
                payload["removeMacs"] = removed_macs

        result: bool = await self._interface.set_ssid_data(payload)
        if result:
            _LOGGER.debug(f"Successfully updated SSID {ssid_id}")
        else:
            _LOGGER.error(f"Failed to update SSID {ssid_id}")
        return result

    async def set_device_data(self, device_mac: str, network_id: str, data: dict[str, Any]) -> None:
        _LOGGER.info(f"Command {device_mac} {data}")
        reboot = data.get(Constants.REBOOT)
        update_firmware = data.get(Constants.UPDATE_FIRMWARE)
        reset = data.get(Constants.RESET)
        network_name = data.get(Constants.NETWORK_NAME)
        wireless = data.get(Constants.WIRELESS)
        channel_2_4 = data.get(Constants.CHANNEL_2_4)
        channel_5 = data.get(Constants.CHANNEL_5)
        channel_6 = data.get(Constants.CHANNEL_6)
        _LOGGER.info(f"Command {reboot} {update_firmware} {reset} {network_name} {wireless} {channel_2_4} {channel_5} {channel_6}")

    async def set_network_data(self, network_id: str, data: dict[str, Any]) -> None:
        _LOGGER.info(f"Command {network_id} {data}")
        network_name = data.get(Constants.NETWORK_NAME)
        _LOGGER.info(f"Command {network_name}")
