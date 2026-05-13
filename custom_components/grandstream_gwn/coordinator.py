import logging
from datetime import timedelta
from enum import Enum
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from gwn.constants import Constants
from gwn.api import GwnClient
from gwn.authentication import GwnConfig
from gwn.request_data import GwnDevicePayload, GwnNetworkPayload, GwnSSIDPayload
from gwn.response_data import GwnDevice, GwnNetwork, GwnSSID

_LOGGER = logging.getLogger(Constants.LOG)

class GwnDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._entry = entry
        self._gwn_config: GwnConfig = _build_gwn_config(self._entry)
        self._gwn_client: GwnClient = GwnClient(self._gwn_config)
        super().__init__(
            hass,
            logger=_LOGGER,
            name="Grandstream GWN",
            update_interval=timedelta(seconds=self._gwn_config.refresh_period_s)
        )

    def _enum_value(self, value: Enum | None) -> str | None:
        if value is None:
            return None
        return value.value

    def _serialise_ssid(self, gwn_network: GwnNetwork, gwn_ssid: GwnSSID) -> dict[str, object]:
        return {
            Constants.SSID_ID: gwn_ssid.id,
            Constants.SSID_NAME: gwn_ssid.ssidName,
            Constants.WIFI_ENABLED: gwn_ssid.wifiEnabled,
            Constants.CLIENT_COUNT: gwn_ssid.onlineDevices,
            Constants.SCHEDULE_ENABLED: gwn_ssid.scheduleEnabled,
            Constants.PORTAL_ENABLED: gwn_ssid.portalEnabled,
            Constants.MAC_FILTERING_ENABLED: self._enum_value(gwn_ssid.macFilteringEnabled),
            Constants.SSID_ISOLATION_MODE: self._enum_value(gwn_ssid.ssidIsolationMode),
            Constants.SSID_ISOLATION: gwn_ssid.ssidIsolation,
            Constants.SSID_HIDDEN: gwn_ssid.ssidSsidHidden,
            Constants.SSID_VLAN_ID: gwn_ssid.ssidVlanid,
            Constants.SSID_VLAN_ENABLED: gwn_ssid.ssidVlanEnabled,
            Constants.SSID_ENABLE: gwn_ssid.ssidEnable,
            Constants.SSID_REMARK: gwn_ssid.ssidRemark,
            Constants.SSID_KEY: gwn_ssid.ssidKey,
            Constants.GHZ2_4_ENABLED: gwn_ssid.ghz2_4_Enabled,
            Constants.GHZ5_ENABLED: gwn_ssid.ghz5_Enabled,
            Constants.GHZ6_ENABLED: gwn_ssid.ghz6_Enabled,
            Constants.NETWORK_NAME: gwn_network.networkName,
            Constants.NETWORK_ID: gwn_network.id,
            Constants.ASSIGNED_DEVICES: { device.mac: device.name for device in sorted(gwn_ssid.devices, key=lambda device: device.mac) }
        }

    def _serialise_device(self, gwn_network: GwnNetwork, gwn_device: GwnDevice, ssids: list[GwnSSID], networks: dict[int, str]) -> dict[str, object]:
        return {
            Constants.STATUS: gwn_device.status,
            Constants.AP_TYPE: gwn_device.apType,
            Constants.MAC: gwn_device.mac,
            Constants.AP_NAME: gwn_device.name,
            Constants.IPV4: gwn_device.ip,
            Constants.UP_TIME: gwn_device.upTime,
            Constants.USAGE: gwn_device.usage,
            Constants.UPLOAD: gwn_device.upload,
            Constants.DOWNLOAD: gwn_device.download,
            Constants.CLIENTS: gwn_device.clients,
            Constants.CURRENT_FIRMWARE: gwn_device.versionFirmware,
            Constants.IPV6: gwn_device.ipv6,
            Constants.NEW_FIRMWARE: gwn_device.newFirmware,
            Constants.WIRELESS: gwn_device.wireless,
            Constants.VLAN_MAX_SIZE: gwn_device.vlanCount,
            Constants.SSID_COUNT: gwn_device.ssidNumber,
            Constants.ONLINE_STATUS: gwn_device.online,
            Constants.MODEL: gwn_device.model,
            Constants.DEVICE_TYPE: gwn_device.deviceType,
            Constants.CHANNEL_5: gwn_device.channel_5,
            Constants.CHANNEL_2_4: gwn_device.channel_2_4,
            Constants.CHANNEL_6: gwn_device.channel_6,
            Constants.PART_NUMBER: gwn_device.partNumber,
            Constants.BOOT_VERSION: gwn_device.bootVersion,
            Constants.NETWORK: gwn_device.network,
            Constants.TEMPERATURE: gwn_device.temperature,
            Constants.USED_MEMORY: gwn_device.usedMemory,
            Constants.CHANNEL_LOAD_2G4: gwn_device.channelload_2g4,
            Constants.CHANNEL_LOAD_6G: gwn_device.channelload_6g,
            Constants.CPU_USAGE: gwn_device.cpuUsage,
            Constants.CHANNEL_LOAD_5G: gwn_device.channelload_5g,
            Constants.AP_2G4_CHANNEL: gwn_device.ap_2g4_channel,
            Constants.AP_5G_CHANNEL: gwn_device.ap_5g_channel,
            Constants.AP_6G_CHANNEL: gwn_device.ap_6g_channel, # undocumented but confirmed by grandstream customer support
            Constants.CHANNEL_LISTS_2G4: gwn_device.channel_lists_2g4,
            Constants.CHANNEL_LISTS_5G: gwn_device.channel_lists_5g,
            Constants.CHANNEL_LISTS_6G: gwn_device.channel_lists_6g,
            Constants.NETWORK_NAME: gwn_network.networkName,
            Constants.NETWORK_ID: gwn_network.id,
            Constants.NETWORKS: networks,
            Constants.SSIDS: [
                {
                    Constants.SSID_ID: ssid.id,
                    Constants.SSID_NAME: ssid.ssidName
                }
                for ssid in sorted(ssids, key=lambda ssid: int(ssid.id))
            ]
        }

    def _serialise_network(self, gwn_network: GwnNetwork, ssids: dict[str,dict[str, object]], devices: dict[str,dict[str, object]]) -> dict[str, object]:
        return {
            Constants.NETWORK_ID: gwn_network.id,
            Constants.NETWORK_NAME: gwn_network.networkName,
            Constants.COUNTRY_DISPLAY: gwn_network.countryDisplay,
            Constants.TIMEZONE: gwn_network.timezone,
            Constants.SSIDS: ssids,
            Constants.DEVICES: devices
        }

    async def _async_update_data(self) -> dict[Any, dict[str, Any]]:
        gwn_networks: list[GwnNetwork] = await self._gwn_client.get_gwn_data()
        full_network_dict: dict[int, str] = {
            int(network.id): network.networkName
            for network in sorted(gwn_networks, key=lambda network: int(network.id))
        }
        network_list: dict[str, dict[str, object]] = {}
        for gwn_network in gwn_networks:
            ssid_list: dict[str,dict[str, object]] = {}
            device_list: dict[str,dict[str, object]] = {}

            device_assignments: dict[str, list[GwnSSID]] = {}
            for gwn_ssid in gwn_network.ssids:
                ssid_list[gwn_ssid.id] = self._serialise_ssid(gwn_network, gwn_ssid)
                for gwn_device in gwn_ssid.devices:
                    if gwn_device.mac not in device_assignments:
                        device_assignments[gwn_device.mac] = []
                    device_assignments[gwn_device.mac].append(gwn_ssid)
            for gwn_device in gwn_network.devices:
                device_list[gwn_device.mac] = self._serialise_device(gwn_network, gwn_device, device_assignments.get(gwn_device.mac, []), full_network_dict)
            network_list[gwn_network.id] = self._serialise_network(gwn_network, ssid_list, device_list)

        return {Constants.GWN:{Constants.NETWORKS: network_list}}

    def is_readonly(self) -> bool:
        return self._gwn_client.is_readonly

    async def async_set_network_value(self, network_id: str, key: str, value: str) -> bool:
        payload: GwnNetworkPayload = GwnNetworkPayload(id=int(network_id))

        if key == Constants.NETWORK_NAME:
            payload.networkName = None if value is None else str(value)
        else:
            raise ValueError(f"Unsupported network key: {key}")

        result = await self._gwn_client.set_network_data(payload)
        if result:
            await self.async_request_refresh()
        return result

    async def async_set_device_value(self, device_mac: str, network_id: str, key: str, value: int | str) -> bool:
        payload: GwnDevicePayload = GwnDevicePayload(ap_mac=device_mac, networkId=int(network_id))

        if key == Constants.AP_NAME:
            payload.ap_name = None if value is None else str(value)
        elif key == Constants.AP_2G4_CHANNEL:
            payload.ap_2g4_channel = None if value is None else int(value)
        elif key == Constants.AP_5G_CHANNEL:
            payload.ap_5g_channel = None if value is None else int(value)
        elif key == Constants.AP_6G_CHANNEL:
            payload.ap_6g_channel = None if value is None else int(value)
        elif key == Constants.NETWORK_ID:
            payload.networkId = None if value is None else int(value)
        else:
            raise ValueError(f"Unsupported device key: {key}")

        result = await self._gwn_client.set_device_data(payload)
        if result:
            await self.async_request_refresh()
        return result

    async def async_press_device_action(self, device_mac: str, network_id: str, action: str) -> bool:
        payload = GwnDevicePayload(ap_mac=device_mac, networkId=int(network_id))

        if action == Constants.REBOOT:
            payload.reboot = True
        elif action == Constants.RESET:
            payload.reset = True
        elif action == Constants.UPDATE_FIRMWARE:
            payload.update = True
        else:
            raise ValueError(f"Unsupported device action: {action}")

        result = await self._gwn_client.set_device_data(payload)
        if result:
            await self.async_request_refresh()
        return result

    async def async_set_ssid_value(self, ssid_id: str, network_id: str, key: str, value: bool | int | str | dict[str, bool]) -> bool:
        payload: GwnSSIDPayload = GwnSSIDPayload(id=int(ssid_id), networkId=int(network_id))

        if key == Constants.SSID_ENABLE:
            payload.ssidEnable = bool(value)
        elif key == Constants.PORTAL_ENABLED:
            payload.ssidPortalEnable = bool(value)
        elif key == Constants.SSID_ISOLATION:
            payload.ssidIsolation = bool(value)
        elif key == Constants.GHZ2_4_ENABLED:
            payload.ghz2_4_enabled = bool(value)
        elif key == Constants.GHZ5_ENABLED:
            payload.ghz5_enabled = bool(value)
        elif key == Constants.GHZ6_ENABLED:
            payload.ghz6_enabled = bool(value)
        elif key == Constants.SSID_HIDDEN:
            payload.ssidSsidHidden = bool(value)
        elif key == Constants.SSID_VLAN_ID:
            payload.ssidVlanid = None if value is None else int(str(value))
            payload.ssidVlan = None if value is None else int(str(value)) > 0
        elif key == Constants.SSID_NAME:
            payload.ssidSsid = None if value is None else str(value)
        elif key == Constants.SSID_KEY:
            payload.ssid_key = None if value is None else str(value)
        elif key == Constants.TOGGLE_DEVICE:
            payload.toggled_macs = None if value is None or not isinstance(value,dict) else value
        else:
            raise ValueError(f"Unsupported SSID key: {key}")

        result = await self._gwn_client.set_ssid_data(payload)
        if result:
            await self.async_request_refresh()
        return result

def _parse_int_list(value: str | None) -> list[int]:
    if value is None or value.strip() == "":
        return []
    return [int(item.strip()) for item in value.split(",") if item.strip()]

def _parse_str_list(value: str | None) -> list[str]:
    if value is None or value.strip() == "":
        return []
    return [item.strip() for item in value.split(",") if item.strip()]

def _build_gwn_config(entry: ConfigEntry) -> GwnConfig:
    data = entry.data
    gwn_config: GwnConfig = GwnConfig(app_id=str(data["app_id"]), secret_key=str(data["secret_key"]))
    restricted_api = data.get("restricted_api")
    if restricted_api is not None:
        gwn_config.restricted_api = bool(restricted_api)
    username = data.get("username")
    if username is not None:
        gwn_config.username = str(username)
    password = data.get("password")
    if password not in (None, ""):
        gwn_config.password = GwnConfig.hash_password(str(password))
    base_url = data.get("base_url")
    if base_url is not None:
        gwn_config.base_url = str(base_url)
    page_size = data.get("page_size")
    if page_size is not None:
        gwn_config.page_size = int(page_size)
    max_pages = data.get("max_pages")
    if max_pages is not None:
        gwn_config.max_pages = int(max_pages)
    refresh_period_s = data.get("refresh_period_s")
    if refresh_period_s is not None:
        gwn_config.refresh_period_s = int(refresh_period_s)
    exclude_passphrase = data.get("exclude_passphrase")
    if exclude_passphrase is not None:
        gwn_config.exclude_passphrase = _parse_int_list(data.get("exclude_passphrase"))
    exclude_ssid = data.get("exclude_ssid")
    if exclude_ssid is not None:
        gwn_config.exclude_ssid = _parse_int_list(data.get("exclude_ssid"))
    exclude_device = data.get("exclude_device")
    if exclude_device is not None:
        gwn_config.exclude_device = [GwnConfig.normalise_mac(mac) for mac in _parse_str_list(exclude_device)]
    exclude_network = data.get("exclude_network")
    if exclude_network is not None:
        gwn_config.exclude_network = _parse_int_list(data.get("exclude_network"))
    ignore_failed_fetch_before_update = data.get("ignore_failed_fetch_before_update")
    if ignore_failed_fetch_before_update is not None:
        gwn_config.ignore_failed_fetch_before_update = bool(ignore_failed_fetch_before_update)
    ssid_name_to_device_binding = data.get("ssid_name_to_device_binding")
    if ssid_name_to_device_binding is not None:
        gwn_config.ssid_name_to_device_binding = bool(ssid_name_to_device_binding)
    no_publish = data.get("no_publish")
    if no_publish is not None:
        gwn_config.no_publish = bool(no_publish)
    return gwn_config
