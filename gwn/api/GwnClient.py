import logging
from enum import Enum
from typing import Any, TypeVar

from gwn.api.GwnInterface import GwnInterface
from gwn.authentication import GwnConfig
from gwn.constants import Constants, IsolationMode, MacFiltering, SecurityMode, RadioPower, Width2G, Width5G, Width6G, BandSteering, BooleanEnum
from gwn.request_data import GwnDevicePayload, GwnNetworkPayload, GwnSSIDPayload
from gwn.response_data import GwnDevice, GwnNetwork, GwnSSID


_LOGGER = logging.getLogger(Constants.LOG)

class GwnClient:
    TypedEnum = TypeVar("TypedEnum", bound=Enum)

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
                device_info_channel: dict[str, Any] = device[4]

                # the sub tables are json objects with 3 parameters: type, key and value so use "key" as a dictionary key
                config_info_port["result"] = self._normalise_dictionary_data(config_info_port["result"])
                config_info_client["g24"] = self._normalise_dictionary_data(config_info_client["g24"])
                config_info_client["g5"] = self._normalise_dictionary_data(config_info_client["g5"])
                config_info_client["g6"] = self._normalise_dictionary_data(config_info_client["g6"])
                
                mac = GwnConfig.normalise_mac(basic_info["mac"])
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

                        ap_2g4_channel= 0 if str(device_info_channel["ap_2g4_channel"]["defaultValue"]) == "Use Radio Settings" else int(config_info_client["g24"]["channel"]["value"]),
                        ap_5g_channel= 0 if str(device_info_channel["ap_5g_channel"]["defaultValue"]) == "Use Radio Settings" else int(config_info_client["g5"]["channel"]["value"])
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
                        gwn_device = devices.get(mac, None)
                        if gwn_device is not None and bool(device_info.get("checked")):
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
                    device_info_channel = await self._interface.get_device_channel_info(mac) or []

                    device_data.append([basic_info,device_info_port,device_info_client, firmware_data.get(mac, {}), self._normalise_dictionary_data(device_info_channel)])
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
                    # ideally SSID name will not be used but this serves as a fallback if username and password were not supplied
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
        if self._config.ssid_name_to_device_binding:
            await self._associated_ssids_with_devices(ssids, devices, device_data)
        _LOGGER.info(f"Found {len(devices)} Devices for Network: {network_id}")
        _LOGGER.info(f"Found {len(ssids)} SSIDs for Network: {network_id}")
        return list(devices.values()), list(ssids.values())

    def _config_value(self, config: dict[str, Any] | None, key: str) -> str | None:
        if config is None:
            return None
        item = config.get(key)
        if not isinstance(item, dict):
            return None
        value = item.get("defaultValue")
        return None if value is None else str(value)

    def _config_int(self, config: dict[str, Any] | None, key: str) -> int | None:
        value = self._config_value(config, key)
        if value is None or value == "":
            return None
        if value == "Use Radio Settings":
            return 0
        return int(value)

    def _config_bool(self, config: dict[str, Any] | None, key: str) -> bool | None:
        value = self._config_value(config, key)
        if value is None or value == "":
            return None
        return value == "1"

    def _config_enum(self, config: dict[str, Any] | None, key: str, enum_type: type[TypedEnum]) -> TypedEnum | None:
        value = self._config_value(config, key)
        if value is None or value == "":
            return None
        return enum_type(int(value))
   
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

    async def set_ssid_data(self, device_macs: list[str], payload: GwnSSIDPayload) -> bool:

        # first fetch existing data
        _LOGGER.debug(f"Fetching current data for SSID {payload.id}")
        config_info = await self._interface.get_ssid_configuration(payload.id)
        if config_info is None and not self._config.ignore_failed_fetch_before_update:
            _LOGGER.error(f"Failed to fetch existing SSID config for ID {payload.id}. Update will not be applied")
            return False

        # normalise the macs for processing and for transport in the payload
        normalised_device_macs: list[str] = [GwnConfig.normalise_mac(mac) for mac in device_macs]
        original_bind_macs: list[str] = normalised_device_macs
        # try to update the snapshot in case the provided one is stale
        detailed_ssid_info: dict[str, Any] | None = None
        if self._interface.user_password_login:
            _LOGGER.debug(f"Fetching detailed data for SSID {payload.id}")
            stored_macs = await self._interface.get_ssid_devices(payload.id)
            ssid_info = await self._interface.get_app_ssid_info(payload.id)
            if ssid_info is not None:
                detailed_ssid_info = {}

                detailed_ssid_info["basic"] = self._normalise_dictionary_data(ssid_info["basic"])
                detailed_ssid_info["access_security"] = self._normalise_dictionary_data(ssid_info["access_secrity"])
                detailed_ssid_info["access_control"] = self._normalise_dictionary_data(ssid_info["access_control"])
                detailed_ssid_info["device_manage"] = self._normalise_dictionary_data(ssid_info["device_manage"])
                detailed_ssid_info["advanced"] = self._normalise_dictionary_data(ssid_info["advanced"])
            elif not self._config.ignore_failed_fetch_before_update:
                _LOGGER.error(f"Failed to fetch existing detailed SSID config for ID {payload.id}. Update will not be applied")
                return False
            if stored_macs is not None:
                flattened_stored_macs: list[str] = []
                for device_info in stored_macs:
                    mac = GwnConfig.normalise_mac(str(device_info.get("mac")))
                    if bool(device_info.get("checked")):
                        flattened_stored_macs.append(mac)
                original_bind_macs = flattened_stored_macs
            elif not self._config.ignore_failed_fetch_before_update:
                _LOGGER.error(f"Failed to fetch existing SSID to device mapping for ID {payload.id}. Update will not be applied")
                return False
        
        _LOGGER.debug(f"Initialising default payload data for SSID {payload.id}")
        # these keys are required as a basic list of the payload so build them up either from the existing payload
        # or perform a pre-update fetch and use the updated version
        if payload.bindMacs is None:
            payload.bindMacs = original_bind_macs

        if payload.toggled_macs is not None:
            payload.toggled_macs = [GwnConfig.normalise_mac(mac) for mac in payload.toggled_macs]
            added_macs = [mac for mac in payload.toggled_macs if mac not in normalised_device_macs]
            removed_macs = [mac for mac in normalised_device_macs if mac not in payload.toggled_macs]
            final_bind_macs = [mac for mac in original_bind_macs if mac not in removed_macs]
            final_bind_macs.extend([mac for mac in added_macs if mac not in final_bind_macs])
            payload.bindMacs = final_bind_macs
            if len(removed_macs) > 0:
                payload.removeMacs = removed_macs

        if payload.ssidSsid is None:
            payload.ssidSsid = None if config_info is None else config_info.get("ssidSsid")
        if payload.ssidTimedClientPolicy is None:
            payload.ssidTimedClientPolicy = None if detailed_ssid_info is None else self._config_value(detailed_ssid_info["access_control"],"ssid_timed_client_policy")

        # since toggling a single band is supported, any other bands need to be checked to prevent overwritting their values
        if payload.ssidNewSsidBand is None:
            payload.ssidNewSsidBand = None if config_info is None else config_info.get("ssidNewSsidBand")
        if payload.ssidWepKey is None:
            payload.ssidWepKey = None if config_info is None else config_info.get("ssidWepKey")
        if payload.ssidWpaKey is None:
            payload.ssidWpaKey = None if config_info is None else config_info.get("ssidWpaKey")

        # config info may have failed but if the source was not from home assistant, 
        # then ssidEncryption may have been set by another MQTT command

        ssid_encryption: SecurityMode | None = None

        if payload.ssidEncryption is not None:
            ssid_encryption = SecurityMode(payload.ssidEncryption)
        elif config_info is not None:
            ssid_encryption = SecurityMode(int(config_info["ssidEncryption"]))

        # if Wep/Wpa key was not specified directly and instead ssid_key was given, use encryption to infer method
        if ssid_encryption is None:
            _LOGGER.warn(f"Unable to set WPA/WEP Key for SSID {payload.id}. Unable to determine encryption")
            return False
        if payload.ssid_key is not None:
            match ssid_encryption:
                case SecurityMode.WEP64:
                    payload.ssidWepKey = payload.ssid_key
                case SecurityMode.WEP128:
                    payload.ssidWepKey = payload.ssid_key
                case SecurityMode.OPEN:
                    payload.ssidWepKey = payload.ssidWepKey
                    payload.ssidWpaKey = payload.ssidWpaKey
                case _:
                    payload.ssidWpaKey = payload.ssid_key
        _LOGGER.debug(f"Building Payload for SSID {payload.id}")
        payload_dict = payload.build_payload()
        if len(payload_dict) == 0:
            absent_list: list[str] = []
            for required in payload.REQUIRED:
                if getattr(payload, required) is None:
                    absent_list.append(required)

            _LOGGER.error(f"Failed to send payload. Required fields are missing {absent_list}")
            return False
        _LOGGER.debug(f"Sending Payload for SSID {payload.id}")
        result: bool = await self._interface.set_ssid_data(payload_dict)
        if result:
            _LOGGER.debug(f"Successfully updated SSID {payload.id}")
        else:
            _LOGGER.error(f"Failed to update SSID {payload.id}")
        return result

    async def set_device_data(self, payload: GwnDevicePayload) -> bool:
        payload.ap_mac = GwnConfig.normalise_mac(payload.ap_mac)
        # first handle commands
        commands = 0
        if payload.reboot:
            commands = commands+1
        if payload.reset:
            commands = commands+1
        if payload.update:
            commands = commands+1
        if payload.target_network is not None:
            commands = commands+1
        if commands > 1:
            _LOGGER.warn("Sending Multiple Commands in a Single Payload is Unsupported")
            return False
        elif commands > 0: # commands and setting data together is not support. Commands will always override data
            if payload.reboot:
                _LOGGER.info(f"Sending Reboot to {payload.ap_mac}")
                return await self._interface.reboot_device(payload.ap_mac)
            if payload.reset:
                _LOGGER.info(f"Sending Reset to {payload.ap_mac}")
                return await self._interface.reset_device(payload.ap_mac)
            if payload.update:
                _LOGGER.info(f"Sending Update to {payload.ap_mac}")
                return await self._interface.update_device(payload.ap_mac)
            if payload.target_network is not None:
                _LOGGER.info(f"Moving device {payload.ap_mac} to {payload.target_network}")
                return await self._interface.move_device_to_network(payload.ap_mac,str(payload.target_network))


        # first fetch existing data
        _LOGGER.debug(f"Fetching current data for device {payload.ap_mac}")
        device_info_port = await self._interface.get_device_info_port(payload.networkId,payload.ap_mac)
        device_info_client = await self._interface.get_device_info_client(payload.ap_mac)
        info_channel = await self._interface.get_device_channel_info(payload.ap_mac)
        if (device_info_port is None or device_info_client is None or info_channel is None) and not self._config.ignore_failed_fetch_before_update:
            _LOGGER.error(f"Failed to fetch existing Device config for device with MAC {payload.ap_mac}. Update will not be applied")
            return False
        device_info_channel: dict[str, Any] | None = None
        if device_info_port is not None:
            device_info_port["result"] = self._normalise_dictionary_data(device_info_port["result"])
        if device_info_client is not None:
            device_info_client["g24"] = self._normalise_dictionary_data(device_info_client["g24"])
            device_info_client["g5"] = self._normalise_dictionary_data(device_info_client["g5"])
            device_info_client["g6"] = self._normalise_dictionary_data(device_info_client["g6"])
        if info_channel is not None:
            device_info_channel = self._normalise_dictionary_data(info_channel)

        device_info_config: dict[str, Any] | None = None
        if self._interface.user_password_login and device_info_client is not None:
            _LOGGER.debug(f"Fetching detailed data for device {payload.ap_mac}")
            config_device_info = await self._interface.get_app_device_info(payload.ap_mac,device_info_client["apType"])
            if config_device_info is not None:
                device_info_config = self._normalise_dictionary_data(config_device_info)

        # these keys are required as a basic list of the payload
        _LOGGER.debug(f"Initialising default payload data for device {payload.ap_mac}")
        if payload.ap_2g4_channel is None:
            payload.ap_2g4_channel = 0 if device_info_channel is None or str(device_info_channel["ap_2g4_channel"]["defaultValue"]) == "Use Radio Settings" else 0 if device_info_client is None else int(device_info_client["g24"]["channel"]["value"])
        if payload.ap_2g4_power is None:
            payload.ap_2g4_power = None if device_info_client is None else RadioPower(int(device_info_client["g24"]["power"]))

        if payload.ap_2g4_ratelimit_enable is None:
            payload.ap_2g4_ratelimit_enable = self._config_enum(device_info_config, "ap_2g4_ratelimit_enable", BooleanEnum)
        if payload.ap_2g4_rssi is None:
            payload.ap_2g4_rssi = self._config_int(device_info_config, "ap_2g4_rssi")
        if payload.ap_2g4_rssi_enable is None:
            payload.ap_2g4_rssi_enable = self._config_enum(device_info_config, "ap_2g4_rssi_enable", BooleanEnum)
        if payload.ap_2g4_tag is None:
            payload.ap_2g4_tag = self._config_value(device_info_config, "ap_2g4_tag")
        if payload.ap_2g4_width is None:
            payload.ap_2g4_width = self._config_enum(device_info_config, "ap_2g4_width", Width2G)

        if payload.ap_5g_channel is None:
            payload.ap_5g_channel = 0 if device_info_channel is None or str(device_info_channel["ap_5g_channel"]["defaultValue"]) == "Use Radio Settings" else 0 if device_info_client is None else int(device_info_client["g5"]["channel"]["value"])
        if payload.ap_5g_power is None:
            payload.ap_5g_power = None if device_info_client is None else RadioPower(int(device_info_client["g5"]["power"]))
        if payload.ap_5g_ratelimit_enable is None:
            payload.ap_5g_ratelimit_enable = self._config_enum(device_info_config, "ap_5g_ratelimit_enable", BooleanEnum)
        if payload.ap_5g_rssi is None:
            payload.ap_5g_rssi = self._config_int(device_info_config, "ap_5g_rssi")
        if payload.ap_5g_rssi_enable is None:
            payload.ap_5g_rssi_enable = self._config_enum(device_info_config, "ap_5g_rssi_enable", BooleanEnum)
        if payload.ap_5g_tag is None:
            payload.ap_5g_tag = self._config_value(device_info_config, "ap_5g_tag")
        if payload.ap_5g_width is None:
            payload.ap_5g_width = self._config_enum(device_info_config, "ap_5g_width", Width5G)

        if payload.ap_6g_power is None:
            payload.ap_6g_power = None if device_info_client is None else RadioPower(int(device_info_client["g6"]["power"]))
        if payload.ap_6g_power is None:
            payload.ap_6g_power = None if device_info_client is None else RadioPower(int(device_info_client["g6"]["power"]))
        if payload.ap_6g_ratelimit_enable is None:
            payload.ap_6g_ratelimit_enable = self._config_enum(device_info_config, "ap_6g_ratelimit_enable", BooleanEnum)
        if payload.ap_6g_rssi is None:
            payload.ap_6g_rssi = self._config_int(device_info_config, "ap_6g_rssi")
        if payload.ap_6g_rssi_enable is None:
            payload.ap_6g_rssi_enable = self._config_enum(device_info_config, "ap_6g_rssi_enable", BooleanEnum)
        if payload.ap_6g_tag is None:
            payload.ap_6g_tag = self._config_value(device_info_config, "ap_6g_tag")
        if payload.ap_6g_width is None:
            payload.ap_6g_width = self._config_enum(device_info_config, "ap_6g_width", Width6G)

        if payload.ap_alternate_dns is None:
            payload.ap_alternate_dns = self._config_value(device_info_config, "ap_alternate_dns")
        if payload.ap_band_steering is None:
            payload.ap_band_steering = self._config_enum(device_info_config, "ap_band_steering", BandSteering)
        if payload.ap_ipv4_route is None:
            payload.ap_ipv4_route = self._config_value(device_info_config, "ap_ipv4_route")
        if payload.ap_ipv4_static is None:
            payload.ap_ipv4_static = self._config_value(device_info_config, "ap_ipv4_static")
        if payload.ap_ipv4_static_mask is None:
            payload.ap_ipv4_static_mask = self._config_value(device_info_config, "ap_ipv4_static_mask")
        if payload.ap_name is None:
            payload.ap_name = self._config_value(device_info_config, "ap_name")
        if payload.ap_preferred_dns is None:
            payload.ap_preferred_dns = self._config_value(device_info_config, "ap_preferred_dns")
        if payload.ap_static is None:
            payload.ap_static = self._config_bool(device_info_config, "ap_static")

        _LOGGER.debug(f"Building Payload for device {payload.ap_mac}")
        payload_dict = payload.build_payload()
        if len(payload_dict) == 0:
            absent_list: list[str] = []
            for required in payload.REQUIRED:
                if getattr(payload, required) is None:
                    absent_list.append(required)
            _LOGGER.error(f"Failed to send payload. Required fields are missing {absent_list}")
            return False
        _LOGGER.debug(f"Sending Payload for device {payload.ap_mac}")
        result: bool = await self._interface.set_device_data(payload_dict)
        if result:
            _LOGGER.debug(f"Successfully updated Device {payload.ap_mac}")
        else:
            _LOGGER.error(f"Failed to update Device {payload.ap_mac}")
        return result

    async def set_network_data(self, payload: GwnNetworkPayload) -> bool:
        _LOGGER.debug(f"Fetching current data for network {payload.id}")
        network_info: dict[str, Any] | None = await self._interface.get_network_data(payload.id)
        if network_info is None and not self._config.ignore_failed_fetch_before_update:
            _LOGGER.error(f"Failed to fetch existing Network config for ID {payload.id}. Update will not be applied")
            return False

        if payload.networkName is None:
            payload.networkName = None if network_info is None else network_info.get("networkName")
        if payload.country is None:
            payload.country = None if network_info is None else network_info.get("country")
        if payload.timezone is None:
            payload.timezone = None if network_info is None else network_info.get("timezone")
        if payload.networkAdministrators is None:
            payload.networkAdministrators = None if network_info is None else [int(admin["id"]) for admin in network_info.get("networkAdmins",[])]

        _LOGGER.debug(f"Building Payload for network {payload.id}")
        payload_dict = payload.build_payload()
        if len(payload_dict) == 0:
            absent_list: list[str] = []
            for required in payload.REQUIRED:
                if getattr(payload, required) is None:
                    absent_list.append(required)
            _LOGGER.error(f"Failed to send payload. Required fields are missing {absent_list}")
            return False
        _LOGGER.debug(f"Sending Payload for network {payload.id}")
        result: bool = await self._interface.set_network_data(payload_dict)
        if result:
            _LOGGER.debug(f"Successfully updated Network {payload.id}")
        else:
            _LOGGER.error(f"Failed to update Network {payload.id}")
        return result
        
