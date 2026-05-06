import asyncio
import logging
from enum import Enum
from typing import Any

from gwn.api import GwnClient
from gwn.constants import BandSteering, BandwidthType, BooleanEnum, Constants, IsolationMode, MacFiltering, MultiCastToUnicast, RadioPower, SecurityMode, SSID_11W, SSID_BMS, SSIDSecurityType, WpaKeyMode, Width2G, Width5G, Width6G, WpaEncryption
from gwn.request_data import GwnDevicePayload, GwnNetworkPayload, GwnSSIDPayload
from gwn.response_data import GwnDevice, GwnNetwork, GwnSSID
from mqtt.config import AppConfig
from mqtt.connection import MqttClient

_LOGGER = logging.getLogger(Constants.LOG)

class AuthenticationError(Exception):
    pass

class RequestError(Exception):
    pass

class MqttGwnManager:
    def __init__(self, config: AppConfig, mqtt_client: MqttClient, gwn_client: GwnClient) -> None:
        self._config: AppConfig = config
        self._mqtt_client: MqttClient = mqtt_client
        self._gwn_client: GwnClient = gwn_client
        self._poll_trigger = asyncio.Event()

        self._cached_networks: dict[str, dict[str, object]] = {}
        self._cached_devices: dict[str, dict[str, dict[str, object]]] = {}
        self._cached_ssids: dict[str, dict[str, dict[str, object]]] = {}

    async def _run_gwn_interface(self) -> None:
        _LOGGER.debug("Polling GWN")
        if self._config.unpublish_initial_data:
            await self._unpublish_all_data()
        while True:
            try:
                networks = await self._gwn_client.get_gwn_data()
                await self._publish_gwn_data(networks)
            except Exception as e:
                _LOGGER.error(f"Error retreiving GWN Data: {e}")
            try:
                _LOGGER.info("Checking manifest")
                self._mqtt_client.write_manifest()
            except Exception as e:
                _LOGGER.error(f"Error updating manifest: {e}")
            _LOGGER.info(f"Will refresh in {self._gwn_client.refresh_period}s")
            try:
                await asyncio.wait_for(self._poll_trigger.wait(), timeout=self._gwn_client.refresh_period)
                self._poll_trigger.clear()
            except asyncio.TimeoutError:
                pass
        _LOGGER.info("Stopped Polling of GWN Manager")

    async def _run_mqtt_interface(self) -> None:
        _LOGGER.info("Listening to MQTT")
        payload: dict[str, object] = {
            Constants.CURRENT_VERSION: Constants.APP_VERSION,
            Constants.NEW_VERSION: Constants.APP_VERSION
        }
        await self._mqtt_client.publish_online(payload)
        await asyncio.Event().wait()
        _LOGGER.info("Stopped listening to MQTT")

    async def _unpublish_all_data(self) -> None:
        _LOGGER.info("Cleaning out old data")
        gwn_networks = await self._gwn_client.get_gwn_data()
        _LOGGER.info(f"Cleaning out old data for {len(gwn_networks)} Networks")
        for gwn_network in gwn_networks:
            device_assignments: dict[str, list[GwnSSID]] = self._build_device_assignments(gwn_network.ssids)
            ssid_device_info: dict[str, str] = {}
            _LOGGER.info(f"Cleaning out old data for {len(gwn_network.devices)} Devices for Network with ID {gwn_network.id}")
            for gwn_device in gwn_network.devices:
                try:
                    _LOGGER.debug(f"Unpublishing old Device with MAC {gwn_device.mac}")
                    assignments: list[GwnSSID] = device_assignments.get(gwn_device.mac, [])
                    ssid_device_info[gwn_device.mac] = gwn_device.name # doesnt need to be set to name but do so for consistency
                    device_payload = self._serialise_device(gwn_network, gwn_device, assignments)
                    await self._mqtt_client.unpublish_device(device_payload, True)
                    _LOGGER.debug(f"Unpublished old Device with MAC {gwn_device.mac}")
                except Exception as e:
                    _LOGGER.warn(f"Failed to unpublish Device with MAC {gwn_device.mac}: {e}")
            _LOGGER.info(f"Cleaning out old data for {len(gwn_network.ssids)} SSIDs for Network with ID {gwn_network.id}")
            for gwn_ssid in gwn_network.ssids:
                try:
                    _LOGGER.debug(f"Unpublishing old SSID with ID {gwn_ssid.id}")
                    ssid_payload = self._serialise_ssid(gwn_network, gwn_ssid)
                    await self._mqtt_client.unpublish_ssid(ssid_payload, ssid_device_info, True)
                    _LOGGER.debug(f"Unpublished old SSID with ID {gwn_ssid.id}")
                except Exception as e:
                    _LOGGER.warn(f"Failed to unpublish SSID with ID {gwn_ssid.id}: {e}")
            try:
                _LOGGER.debug(f"Unpublishing old Network with ID {gwn_network.id}")
                network_payload = self._serialise_network(gwn_network)
                await self._mqtt_client.unpublish_network(network_payload, True)
                _LOGGER.debug(f"Unpublished old Network with ID {gwn_network.id}")
            except Exception as e:
                _LOGGER.warn(f"Failed to unpublish Network with ID {gwn_network.id}: {e}")
        _LOGGER.info("Cleaned out old data")

    def _build_device_assignments(self, ssids: list[GwnSSID]) -> dict[str, list[GwnSSID]]:
        device_assignments: dict[str, list[GwnSSID]] = {}
        for gwn_ssid in ssids:
            for gwn_device in gwn_ssid.devices:
                if gwn_device.mac not in device_assignments:
                    device_assignments[gwn_device.mac] = []
                device_assignments[gwn_device.mac].append(gwn_ssid)
        return device_assignments

    async def _publish_network(self, gwn_network: GwnNetwork, cached_networks: dict[str, dict[str, object]], force_republish: bool) -> None:
        try:
            network_payload = self._serialise_network(gwn_network)
            cached_payload = network_payload.copy()
            cached_payload[Constants.CACHE] = "metadata"
            if force_republish or self._config.publish_every_poll or gwn_network.id not in cached_networks or cached_networks[gwn_network.id] != cached_payload:
                _LOGGER.debug(f"Publishing Network: {gwn_network.networkName} with ID {gwn_network.id} to MQTT")
                await self._mqtt_client.publish_network(network_payload)
                _LOGGER.debug(f"Successfully Published Network {gwn_network.networkName} with ID {gwn_network.id} to MQTT")
            self._cached_networks[gwn_network.id] = cached_payload # only cache after publishing
        except Exception as e:
            if gwn_network.id in cached_networks:  # always preserve the cache if it fails so it is not unpublished
                failed_payload = cached_networks[gwn_network.id].copy()
                failed_payload.pop(Constants.CACHE, None) # this is metadata used only in the cache so ensure it is removed to force a refresh on another cycle
                self._cached_networks[gwn_network.id] = failed_payload
            _LOGGER.error(f"Failed to publish Network {gwn_network.networkName} with ID {gwn_network.id} to MQTT: %s", e)

    async def _publish_devices(self, gwn_network: GwnNetwork, network_names: dict[int,str], cached_devices: dict[str, dict[str, dict[str, object]]], force_republish: bool) -> None:
        _LOGGER.info(f"Checking {len(gwn_network.devices)} Devices for Network {gwn_network.id} ({gwn_network.networkName}) for publishing over MQTT")
        device_assignments: dict[str, list[GwnSSID]] = self._build_device_assignments(gwn_network.ssids)
        self._cached_devices[gwn_network.id] = {}

        for gwn_device in gwn_network.devices:
            try:
                assignments: list[GwnSSID] = device_assignments.get(gwn_device.mac, [])
                device_payload = self._serialise_device(gwn_network, gwn_device, assignments)
                # copy the cache because all networks need to be recorded so that if a discovery publish fails, it will reattempt on next cycle
                cached_payload = device_payload.copy()
                cached_payload[Constants.CACHE] = dict(sorted(network_names.items()))

                if (gwn_network.id in cached_devices and
                    gwn_device.mac in cached_devices[gwn_network.id] and
                    (
                        # these are baked into the payloads so only change with auto discovery. This must therefore, be explicitly checked here
                        cached_payload[Constants.CHANNEL_LISTS_2G4] != cached_devices[gwn_network.id][gwn_device.mac].get(Constants.CHANNEL_LISTS_2G4) or
                        cached_payload[Constants.CHANNEL_LISTS_5G] != cached_devices[gwn_network.id][gwn_device.mac].get(Constants.CHANNEL_LISTS_5G) or
                        cached_payload[Constants.CHANNEL_LISTS_6G] != cached_devices[gwn_network.id][gwn_device.mac].get(Constants.CHANNEL_LISTS_6G)
                    )
                ):
                    _LOGGER.debug(f"Publishing Autodiscovery for Device with MAC {gwn_device.mac} to MQTT")
                    # since channel options are baked into the data for every option list, if the channel width changes, and thus the available select options,
                    # discovery needs to be republished
                    await self._mqtt_client.reset_devices(gwn_network.id, gwn_device.mac)
                if (force_republish or
                    self._config.publish_every_poll or
                    gwn_network.id not in cached_devices or
                    gwn_device.mac not in cached_devices[gwn_network.id] or
                    cached_devices[gwn_network.id][gwn_device.mac] != cached_payload):
                    _LOGGER.debug(f"Publishing Device with MAC {gwn_device.mac} to MQTT")
                    await self._mqtt_client.publish_device(device_payload, network_names, self._gwn_client.is_readonly)
                    _LOGGER.debug(f"Successfully published Device with MAC {gwn_device.mac} to MQTT")
                self._cached_devices[gwn_network.id][gwn_device.mac] = cached_payload # only cache after publishing
            except Exception as e:
                if gwn_network.id in cached_devices and gwn_device.mac in cached_devices[gwn_network.id]: # always preserve the cache if it fails so it is not unpublished
                    failed_payload = cached_devices[gwn_network.id][gwn_device.mac].copy()
                    failed_payload.pop(Constants.CACHE, None) # this is metadata used only in the cache so ensure it is removed to force a refresh on another cycle
                    self._cached_devices[gwn_network.id][gwn_device.mac] = failed_payload
                _LOGGER.error("Failed to publish Device with MAC %s to MQTT: %s", gwn_device.mac, e)

    async def _publish_ssids(self, gwn_network: GwnNetwork, device_names: dict[str, str], cached_ssids: dict[str, dict[str, dict[str, object]]], force_republish: bool) -> None:
        _LOGGER.info(f"Checking { len(gwn_network.ssids) } SSIDs for Network {gwn_network.id} ({gwn_network.networkName}) for publishing over MQTT")
        self._cached_ssids[gwn_network.id] = {}
        device_names = dict(sorted(device_names.items()))
        for gwn_ssid in gwn_network.ssids:
            try:
                ssid_payload = self._serialise_ssid(gwn_network, gwn_ssid)
                cached_payload = ssid_payload.copy()
                cached_payload[Constants.CACHE] = device_names
                if (gwn_network.id in cached_ssids and
                    gwn_ssid.id in cached_ssids[gwn_network.id] and
                    (
                        # these are baked into the payloads so only change with auto discovery. This must therefore, be explicitly checked here
                        cached_payload[Constants.ASSIGNED_DEVICES] != cached_ssids[gwn_network.id][gwn_ssid.id][Constants.ASSIGNED_DEVICES] or
                        # check the cached key data as if it is different then the previous auto discovery publish failed, so try again
                        Constants.CACHE not in cached_ssids[gwn_network.id][gwn_ssid.id] or
                        cached_payload[Constants.CACHE] != cached_ssids[gwn_network.id][gwn_ssid.id][Constants.CACHE]
                    )
                ):
                    _LOGGER.debug(f"Publishing Autodiscovery for SSID: {gwn_ssid.ssidName} with ID {gwn_ssid.id} to MQTT")
                    # since assigned devices are baked into the data for every home assistant toggle, if device assignments change, discovery needs to be republished
                    # cache is checked as well so that if the device name changes, then it updates in autodiscovery (home assistant UI)
                    await self._mqtt_client.reset_ssids(gwn_network.id, gwn_ssid.id)
                if (force_republish or
                    self._config.publish_every_poll or
                    gwn_network.id not in cached_ssids or
                    gwn_ssid.id not in cached_ssids[gwn_network.id] or
                    cached_ssids[gwn_network.id][gwn_ssid.id] != cached_payload):
                    _LOGGER.debug(f"Publishing SSID: {gwn_ssid.ssidName} with ID {gwn_ssid.id} to MQTT")

                    await self._mqtt_client.publish_ssid(ssid_payload, device_names, self._gwn_client.is_readonly)
                    _LOGGER.debug(f"Successfully published SSID {gwn_ssid.ssidName} with ID {gwn_ssid.id} to MQTT")
                self._cached_ssids[gwn_network.id][gwn_ssid.id] = cached_payload # only cache after publishing
            except Exception as e:
                if gwn_network.id in cached_ssids and gwn_ssid.id in cached_ssids[gwn_network.id]: # always preserve the cache if it fails so it is not unpublished
                    failed_payload = cached_ssids[gwn_network.id][gwn_ssid.id].copy()
                    failed_payload.pop(Constants.CACHE, None) # this is metadata used only in the cache so ensure it is removed to force a refresh on another cycle
                    self._cached_ssids[gwn_network.id][gwn_ssid.id] = failed_payload
                _LOGGER.error("Failed to publish SSID %s with ID %s to MQTT: %s", gwn_ssid.ssidName, gwn_ssid.id, e)

    async def _unpublish_networks(self, old_cache: dict[str, dict[str, object]]) -> None:
        removed_network_ids = set(old_cache) - set(self._cached_networks)
        for network_id in removed_network_ids:
            try:
                _LOGGER.debug(f"Unpublishing Network with ID {network_id} from MQTT")
                await self._mqtt_client.unpublish_network(old_cache[network_id], True)
                _LOGGER.debug(f"Unpublished Network with ID {network_id} from MQTT")
            except Exception as e:
                # allow retry again on next poll cycle
                self._cached_networks[network_id] = old_cache[network_id]
                _LOGGER.error("Failed to unpublish Network with ID %s from MQTT: %s", network_id, e)

    async def _unpublish_devices(self, old_cache: dict[str, dict[str, dict[str, object]]], current_devices: dict[str, str]) -> None:
        for network_id, old_devices in old_cache.items():
            new_devices = self._cached_devices.get(network_id, {})
            removed_device_macs = set(old_devices) - set(new_devices)
            for device_mac in removed_device_macs:
                try:
                    _LOGGER.debug(f"Unpublishing Device with MAC {device_mac} from MQTT")
                    await self._mqtt_client.unpublish_device(old_devices[device_mac], device_mac not in current_devices)
                    _LOGGER.debug(f"Unpublished Device with MAC {device_mac} from MQTT")
                except Exception as e:
                    # allow retry again on next poll cycle
                    self._cached_devices.setdefault(network_id, {})[device_mac] = old_devices[device_mac]
                    _LOGGER.error("Failed to unpublish Device with MAC %s from MQTT: %s", device_mac, e)

    async def _unpublish_ssids(self, old_ssid_cache: dict[str, dict[str, dict[str, object]]], old_device_cache: dict[str, dict[str, dict[str, object]]]) -> None:
        for network_id, old_ssids in old_ssid_cache.items():
            new_ssids = self._cached_ssids.get(network_id, {})
            removed_ssid_ids = set(old_ssids) - set(new_ssids)
            old_devices = old_device_cache.get(network_id, {})
            ssid_device_info: dict[str, str] = {device_mac: str(device_payload.get(Constants.NAME, "")) for device_mac, device_payload in old_devices.items()}
            for ssid_id in removed_ssid_ids:
                try:
                    _LOGGER.debug(f"Unpublishing SSID with ID {ssid_id} from MQTT")
                    await self._mqtt_client.unpublish_ssid(old_ssids[ssid_id], ssid_device_info, True)
                    _LOGGER.debug(f"Unpublished SSID with ID {ssid_id} from MQTT")
                except Exception as e:
                    # allow retry again on next poll cycle
                    self._cached_ssids.setdefault(network_id, {})[ssid_id] = old_ssids[ssid_id]
                    _LOGGER.error("Failed to unpublish SSID with ID %s from MQTT: %s", ssid_id, e)

    async def _publish_gwn_data(self, gwn_networks: list[GwnNetwork]) -> None:
        _LOGGER.info(f"Publishing {len(gwn_networks)} Networks over MQTT")
        network_names: dict[int,str] = {int(network.id):network.networkName for network in gwn_networks}
        # take a snapshot of the cache and then wipe it. This prevents the cache from growing stale
        cached_networks: dict[str, dict[str, object]] = self._cached_networks
        cached_devices: dict[str, dict[str, dict[str, object]]] = self._cached_devices
        cached_ssids: dict[str, dict[str, dict[str, object]]] = self._cached_ssids
        self._cached_networks = {}
        self._cached_devices = {}
        self._cached_ssids = {}

        # first see if any old networks have been removed or any new networks were added
        force_republish_networks: bool = False
        force_republish_devices: bool = False
        force_republish_ssids: bool = False

        network_device_names: dict[str, dict[str, str]] = {} # contains devices tied to a network
        current_devices: dict[str, str] = {}  # contains all devices present (regardless of network)
        _LOGGER.debug("Checking cached data")
        # first find any newly added networks
        for gwn_network in gwn_networks:
            network_device_names[gwn_network.id] = {}
            if (gwn_network.id not in cached_networks or
                cached_networks[gwn_network.id][Constants.NETWORK_NAME] != gwn_network.networkName):
                force_republish_devices = True
                force_republish_networks = True
            for gwn_device in gwn_network.devices:
                current_devices[gwn_device.mac] = gwn_device.name
                network_device_names[gwn_network.id][gwn_device.mac] = gwn_device.name
                if (gwn_network.id not in cached_devices or
                    gwn_device.mac not in cached_devices[gwn_network.id] or
                    cached_devices[gwn_network.id][gwn_device.mac][Constants.NAME] != gwn_device.name):
                    force_republish_ssids = True
        # now handle networks or devices that may have moved or been removed
        for network_id, network_dict in cached_devices.items():
            if network_id not in network_device_names:
                force_republish_devices = True
            else:
                for device_mac in network_dict.keys():
                    if device_mac not in network_device_names[network_id]:
                        force_republish_ssids = True
                        force_republish_devices = True

        if force_republish_networks:
            await self._mqtt_client.reset_networks()
        if force_republish_devices:
            await self._mqtt_client.reset_devices()
        if force_republish_ssids:
            await self._mqtt_client.reset_ssids()

        _LOGGER.debug(f"Processing {len(gwn_networks)} Networks")
        for gwn_network in gwn_networks:
            await self._publish_network(gwn_network, cached_networks, force_republish_networks)
            await self._publish_devices(gwn_network, network_names, cached_devices, force_republish_devices)
            await self._publish_ssids(gwn_network, network_device_names[gwn_network.id], cached_ssids, force_republish_ssids)
        _LOGGER.info(f"Processed {len(gwn_networks)} Networks")
        _LOGGER.info("Processing cache for unpublishing")
        await self._unpublish_networks(cached_networks)
        await self._unpublish_devices(cached_devices, current_devices)
        await self._unpublish_ssids(cached_ssids, cached_devices)
        _LOGGER.info("Processed cache for unpublishing")

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
            Constants.CLIENT_ISOLATION_ENABLED: gwn_ssid.clientIsolationEnabled,
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

    def _serialise_device(self, gwn_network: GwnNetwork, gwn_device: GwnDevice, ssids: list[GwnSSID]) -> dict[str, object]:
        return {
            Constants.STATUS: gwn_device.status,
            Constants.AP_TYPE: gwn_device.apType,
            Constants.MAC: gwn_device.mac,
            Constants.NAME: gwn_device.name,
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
            Constants.SSIDS: [
                {
                    Constants.SSID_ID: ssid.id,
                    Constants.SSID_NAME: ssid.ssidName,
                }
                for ssid in sorted(ssids, key=lambda ssid: int(ssid.id))
            ]
        }

    def _serialise_network(self, gwn_network: GwnNetwork) -> dict[str, object]:
        return {
            Constants.NETWORK_ID: gwn_network.id,
            Constants.NETWORK_NAME: gwn_network.networkName,
            Constants.COUNTRY_DISPLAY: gwn_network.countryDisplay,
            Constants.TIMEZONE: gwn_network.timezone
        }

    def _handle_application_command(self, data: dict[str, Any]) -> None:
        _LOGGER.info(f"Command {data}")
        update_version = data.get(Constants.UPDATE_VERSION)
        restart = data.get(Constants.RESTART)
        _LOGGER.info(f"Command {update_version} {restart}")

    async def _handle_network_command(self, network_id: str, data: dict[str, Any]) -> None:
        payload: GwnNetworkPayload = GwnNetworkPayload(id=int(network_id))

        # Discovery Payload Data
        payload.networkName = data.get(Constants.NETWORK_NAME, None)

        # Non-Discovery Payload Data
        payload.country = data.get(Constants.COUNTRY, None)
        payload.timezone = data.get(Constants.TIMEZONE, None)
        payload.networkAdministrators = data.get(Constants.NETWORK_ADMINS, None)

        if await self._gwn_client.set_network_data(payload) and not self._poll_trigger.is_set():
            # immediately refresh/update the data
            self._poll_trigger.set()
    
    async def _handle_device_command(self, device_mac: str, data: dict[str, Any], network_id: str) -> None:    
        payload: GwnDevicePayload = GwnDevicePayload(ap_mac=device_mac, networkId=int(network_id))
        
        # Discovery Payload Data
        payload.reboot = Constants.REBOOT in data
        payload.update = Constants.UPDATE_FIRMWARE in data
        payload.reset = Constants.RESET in data
        payload.target_network = data.get(Constants.NETWORK_NAME, None)
        payload.ap_2g4_channel = data.get(Constants.AP_2G4_CHANNEL, None)
        payload.ap_5g_channel = data.get(Constants.AP_5G_CHANNEL, None)
        payload.ap_6g_channel = data.get(Constants.AP_6G_CHANNEL, None)

        # Non-Discovery Payload Data
        payload.ap_2g4_power = None if Constants.AP_2G4_POWER not in data else RadioPower(data.get(Constants.AP_2G4_POWER))
        payload.ap_2g4_ratelimit_enable = None if Constants.AP_2G4_RATELIMIT_ENABLE not in data else BooleanEnum(data.get(Constants.AP_2G4_RATELIMIT_ENABLE))
        payload.ap_2g4_rssi = data.get(Constants.AP_2G4_RSSI, None)
        payload.ap_2g4_rssi_enable = None if Constants.AP_2G4_RSSI_ENABLE not in data else BooleanEnum(data.get(Constants.AP_2G4_RSSI_ENABLE))
        payload.ap_2g4_tag = data.get(Constants.AP_2G4_TAG, None)
        payload.ap_2g4_width = None if Constants.AP_2G4_WIDTH not in data else Width2G(data.get(Constants.AP_2G4_WIDTH))

        payload.ap_5g_power = None if Constants.AP_5G_POWER not in data else RadioPower(data.get(Constants.AP_5G_POWER))
        payload.ap_5g_ratelimit_enable = None if Constants.AP_5G_RATELIMIT_ENABLE not in data else BooleanEnum(data.get(Constants.AP_5G_RATELIMIT_ENABLE))
        payload.ap_5g_rssi = data.get(Constants.AP_5G_RSSI, None)
        payload.ap_5g_rssi_enable = None if Constants.AP_5G_RSSI_ENABLE not in data else BooleanEnum(data.get(Constants.AP_5G_RSSI_ENABLE))
        payload.ap_5g_tag = data.get(Constants.AP_5G_TAG, None)
        payload.ap_5g_width = None if Constants.AP_5G_WIDTH not in data else Width5G(data.get(Constants.AP_5G_WIDTH))

        payload.ap_alternate_dns = data.get(Constants.AP_ALTERNATE_DNS, None)
        payload.ap_band_steering = None if Constants.AP_BAND_STEERING not in data else BandSteering(data.get(Constants.AP_BAND_STEERING))
        payload.ap_ipv4_route = data.get(Constants.AP_IPV4_ROUTE, None)
        payload.ap_ipv4_static = data.get(Constants.AP_IPV4_STATIC, None)
        payload.ap_ipv4_static_mask = data.get(Constants.AP_IPV4_STATIC_MASK, None)
        payload.ap_name = data.get(Constants.AP_NAME, None)
        payload.ap_preferred_dns = data.get(Constants.AP_PREFERRED_DNS, None)
        payload.ap_static = data.get(Constants.AP_STATIC, None)

        payload.ap_6g_power = None if Constants.AP_6G_POWER not in data else RadioPower(data.get(Constants.AP_6G_POWER))
        payload.ap_6g_ratelimit_enable = None if Constants.AP_6G_RATELIMIT_ENABLE not in data else BooleanEnum(data.get(Constants.AP_6G_RATELIMIT_ENABLE))
        payload.ap_6g_rssi = data.get(Constants.AP_6G_RSSI, None)
        payload.ap_6g_rssi_enable = None if Constants.AP_6G_RSSI_ENABLE not in data else BooleanEnum(data.get(Constants.AP_6G_RSSI_ENABLE))
        payload.ap_6g_tag = data.get(Constants.AP_6G_TAG, None)
        payload.ap_6g_width = None if Constants.AP_6G_WIDTH not in data else Width6G(data.get(Constants.AP_6G_WIDTH))

        if await self._gwn_client.set_device_data(payload) and not self._poll_trigger.is_set():
            # immediately refresh/update the data
            self._poll_trigger.set()

    async def _handle_ssid_command(self, ssid_id: str, data: dict[str, Any], network_id: str) -> None:
        payload: GwnSSIDPayload = GwnSSIDPayload(id=int(ssid_id), networkId=int(network_id))

        # Discovery Payload Data
        payload.ssidEnable = data.get(Constants.SSID_ENABLE, None)
        payload.ssidPortalEnable = data.get(Constants.PORTAL_ENABLED, None)
        payload.ssidVlanid = data.get(Constants.SSID_VLAN_ID, None)
        payload.ssidVlan = data.get(Constants.SSID_VLAN_ENABLED, None if payload.ssidVlanid is None else int(payload.ssidVlanid) > 0)
        payload.ghz2_4_enabled = data.get(Constants.GHZ2_4_ENABLED, None)
        payload.ghz5_enabled = data.get(Constants.GHZ5_ENABLED, None)
        payload.ghz6_enabled = data.get(Constants.GHZ6_ENABLED, None)
        payload.ssid_key = data.get(Constants.SSID_KEY, None)
        payload.ssidSsidHidden = data.get(Constants.SSID_HIDDEN, None)
        payload.ssidSsid = data.get(Constants.SSID_NAME, None)
        payload.ssidIsolation = data.get(Constants.SSID_ISOLATION, data.get(Constants.CLIENT_ISOLATION_ENABLED, None))
        payload.toggled_macs = data.get(Constants.TOGGLE_DEVICE, None)
        # Non-Discovery Payload Data
        payload.ssidRemark = data.get(Constants.SSID_REMARK, None)
        payload.ssidRadiusDynamicVlan = data.get(Constants.SSID_RADIUS_DYNAMIC_VLAN, None)
        payload.ssidNewSsidBand = data.get(Constants.SSID_NEW_SSID_BAND, None)
        payload.ssidWifiClientLimit = data.get(Constants.SSID_WIFI_CLIENT_LIMIT, None)
        payload.ssidEncryption = None if Constants.SSID_ENCRYPTION not in data else SecurityMode(data.get(Constants.SSID_ENCRYPTION))
        payload.ssidWepKey = data.get(Constants.SSID_WEP_KEY, None)
        payload.ssidWpaKeyMode = None if Constants.SSID_WPA_KEY_MODE not in data else WpaKeyMode(data.get(Constants.SSID_WPA_KEY_MODE))
        payload.ssidWpaEncryption = None if Constants.SSID_WPA_ENCRYPTION not in data else WpaEncryption (data.get(Constants.SSID_WPA_ENCRYPTION))
        payload.ssidWpaKey = data.get(Constants.SSID_WPA_KEY, None)
        payload.ssidBridgeEnable = data.get(Constants.SSID_BRIDGE_ENABLE, None)
        payload.ssidIsolationMode = None if Constants.SSID_ISOLATION_MODE not in data else IsolationMode (data.get(Constants.SSID_ISOLATION_MODE))
        payload.ssidGatewayMac = data.get(Constants.SSID_GATEWAY_MAC, None)
        payload.ssidVoiceEnterprise = data.get(Constants.SSID_VOICE_ENTERPRISE, None)
        payload.ssid11V = data.get(Constants.SSID_11V, None)
        payload.ssid11R = data.get(Constants.SSID_11R, None)
        payload.ssid11K = data.get(Constants.SSID_11K, None)
        payload.ssidDtimPeriod = data.get(Constants.SSID_DTIM_PERIOD, None)
        payload.ssidMcastToUcast = None if Constants.SSID_MCAST_TO_UCAST not in data else MultiCastToUnicast (data.get(Constants.SSID_MCAST_TO_UCAST))
        payload.ssidProxyarp = data.get(Constants.SSID_PROXYARP, None)
        payload.ssidStaIdleTimeout = data.get(Constants.SSID_STA_IDLE_TIMEOUT, None)

        payload.ssid11W = None if Constants.SSID_11W not in data else SSID_11W(data.get(Constants.SSID_11W))
        payload.ssidBms = None if Constants.SSID_BMS not in data else SSID_BMS(data.get(Constants.SSID_BMS))
        payload.ssidClientIPAssignment = data.get(Constants.SSID_CLIENT_IP_ASSIGNMENT, None)
        payload.bindMacs = data.get(Constants.BIND_MACS, None)
        payload.removeMacs = data.get(Constants.REMOVE_MACS, None)
        payload.ssidPortalPolicy = data.get(Constants.SSID_PORTAL_POLICY, None)
        payload.ssidMaclistBlacks = data.get(Constants.SSID_MACLIST_BLACKS, None)
        payload.ssidMaclistWhites = data.get(Constants.SSID_MACLIST_WHITES, None)
        payload.ssidMacFiltering = None if Constants.SSID_MAC_FILTERING not in data else MacFiltering(data.get(Constants.SSID_MAC_FILTERING))
        payload.scheduleId = data.get(Constants.SCHEDULE_ID, None)
        payload.ssidTimedClientPolicy = data.get(Constants.SSID_TIMED_CLIENT_POLICY, None)
        payload.bandwidthType = None if Constants.BANDWIDTH_TYPE not in data else BandwidthType (data.get(Constants.BANDWIDTH_TYPE))
        payload.bandwidthRules = data.get(Constants.BANDWIDTH_RULES, None)
        payload.ssidSecurityType = None if Constants.SSID_SECURITY_TYPE not in data else SSIDSecurityType (data.get(Constants.SSID_SECURITY_TYPE))
        payload.ppskProfile = data.get(Constants.PPSK_PROFILE, None)
        payload.radiusProfile = data.get(Constants.RADIUS_PROFILE, None)

        if await self._gwn_client.set_ssid_data(payload) and not self._poll_trigger.is_set():
            
            # immediately refresh/update the data
            self._poll_trigger.set()
    
    async def connect(self) -> bool:
        try:
            _LOGGER.debug("Registering MQTT Handlers")
            self._mqtt_client.set_application_callback(self._handle_application_command)
            self._mqtt_client.set_network_callback(self._handle_network_command)
            self._mqtt_client.set_device_callback(self._handle_device_command)
            self._mqtt_client.set_ssid_callback(self._handle_ssid_command)
            _LOGGER.debug("Registered MQTT Handlers")
            _LOGGER.info("Connecting to MQTT")
            if not await self._mqtt_client.connect():
                raise AuthenticationError("Failed to connect to MQTT Broker")
            _LOGGER.debug("Connected to MQTT Server")

            _LOGGER.debug("Connecting to GWN Manager")
            if not await self._gwn_client.authenticate():
                raise AuthenticationError("Failed to acquire access token from GWN Manager")
            _LOGGER.debug("Connected to GWN Manager")

            _LOGGER.info("Successfully connected to MQTT and GWN Manager")
            return True
        except Exception as e:
            _LOGGER.error(f"Failed to connect: {e}")
            await self._mqtt_client.disconnect()
            await self._gwn_client.close()
        return False

    async def run(self) -> None:
        _LOGGER.info("Starting Poll of GWN Manager and MQTT")
        await self._mqtt_client.unpublish_manifest()
        gwn_task = asyncio.create_task(self._run_gwn_interface())
        mqtt_task = asyncio.create_task(self._run_mqtt_interface())
        try:
            await asyncio.gather(gwn_task, mqtt_task)
        finally:
            await self._mqtt_client.disconnect()
            await self._gwn_client.close()
        _LOGGER.info("Application shutting down")
