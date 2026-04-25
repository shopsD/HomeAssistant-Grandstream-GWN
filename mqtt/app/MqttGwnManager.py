import asyncio
import logging
from enum import Enum
from typing import Any

from gwn.api import GwnClient
from gwn.constants import Constants
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
        while True:
            try:
                networks = await self._gwn_client.get_gwn_data()
                await self._publish_gwn_data(networks)
            except Exception as e:
                _LOGGER.error("Error retreiving GWN Data: %s", e)
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

    def _build_device_assignments(self, ssids: list[GwnSSID]) -> dict[str, list[GwnSSID]]:
        device_assignments: dict[str, list[GwnSSID]] = {}
        for gwn_ssid in ssids:
            for gwn_device in gwn_ssid.devices:
                if gwn_device.mac not in device_assignments:
                    device_assignments[gwn_device.mac] = []
                device_assignments[gwn_device.mac].append(gwn_ssid)
        return device_assignments

    async def _publish_network(self, gwn_network: GwnNetwork, cached_networks: dict[str, dict[str, object]]) -> None:           
        try:
            network_payload = self._serialise_network(gwn_network)
            if self._config.publish_every_poll or gwn_network.id not in cached_networks or cached_networks[gwn_network.id] != network_payload:
                _LOGGER.debug(f"Publishing Network: {gwn_network.networkName} with ID {gwn_network.id} to MQTT")
                await self._mqtt_client.publish_network(network_payload)
                _LOGGER.debug(f"Successfully Published Network {gwn_network.networkName} with ID {gwn_network.id} to MQTT")
            self._cached_networks[gwn_network.id] = network_payload # only cache after publishing
        except Exception as e:
            if gwn_network.id in cached_networks: # always preserve the cache if it fails
                self._cached_networks[gwn_network.id] = cached_networks[gwn_network.id]
            _LOGGER.error(f"Failed to publish Network {gwn_network.networkName} with ID {gwn_network.id} to MQTT: %s", e)           

    async def _publish_devices(self, gwn_network: GwnNetwork, network_names: dict[int,str], cached_devices) -> None:
        _LOGGER.info(f"Checking {len(gwn_network.devices)} Devices for Network {gwn_network.id} ({gwn_network.networkName}) for publishing over MQTT")
        device_assignments: dict[str, list[GwnSSID]] = self._build_device_assignments(gwn_network.ssids)
        self._cached_devices[gwn_network.id] = {}
    
        for gwn_device in gwn_network.devices:
            try:
                assignments: list[GwnSSID] = device_assignments.get(gwn_device.mac, [])
                device_payload = self._serialise_device(gwn_network, gwn_device, assignments)
                if (self._config.publish_every_poll or
                    gwn_network.id not in cached_devices or
                    gwn_device.mac not in cached_devices[gwn_network.id] or
                    cached_devices[gwn_network.id][gwn_device.mac] != device_payload):
                    _LOGGER.debug(f"Publishing Device with MAC {gwn_device.mac} to MQTT")
                    await self._mqtt_client.publish_device(device_payload, network_names)
                    _LOGGER.debug(f"Successfully published Device with MAC {gwn_device.mac} to MQTT")
                self._cached_devices[gwn_network.id][gwn_device.mac] = device_payload # only cache after publishing
            except Exception as e:
                if gwn_network.id in cached_devices and gwn_device.mac in cached_devices[gwn_network.id]: # always preserve the cache if it fails
                    self._cached_devices[gwn_network.id][gwn_device.mac] = cached_devices[gwn_network.id][gwn_device.mac]
                _LOGGER.error("Failed to publish Device with MAC %s to MQTT: %s", gwn_device.mac, e)

    async def _publish_ssids(self,gwn_network: GwnNetwork, cached_ssids: dict[str, dict[str, dict[str, object]]]) -> None:
        _LOGGER.info(f"Checking { len(gwn_network.ssids) } SSIDs for Network {gwn_network.id} ({gwn_network.networkName}) for publishing over MQTT")        
        ssid_device_info: list[list[str]] = [] # build a stripped down and full list of devices for use in SSID toggles
        self._cached_ssids[gwn_network.id] = {}
        for gwn_device in gwn_network.devices:
            ssid_device_info.append([gwn_device.mac,gwn_device.name])
        for gwn_ssid in gwn_network.ssids:
            
            try:                   
                ssid_payload = self._serialise_ssid(gwn_network, gwn_ssid)
                if (self._config.publish_every_poll or  
                    gwn_network.id not in cached_ssids or 
                    gwn_ssid.id not in cached_ssids[gwn_network.id] or
                    cached_ssids[gwn_network.id][gwn_ssid.id] != ssid_payload):
                    _LOGGER.debug(f"Publishing SSID: {gwn_ssid.ssidName} with ID {gwn_ssid.id} to MQTT")

                    await self._mqtt_client.publish_ssid(ssid_payload, ssid_device_info)
                    _LOGGER.debug(f"Successfully published SSID {gwn_ssid.ssidName} with ID {gwn_ssid.id} to MQTT")
                self._cached_ssids[gwn_network.id][gwn_ssid.id] = ssid_payload # only cache after publishing
            except Exception as e:
                if gwn_network.id in cached_ssids and gwn_ssid.id in cached_ssids[gwn_network.id]: # always preserve the cache if it fails
                    self._cached_ssids[gwn_network.id][gwn_ssid.id] = cached_ssids[gwn_network.id][gwn_ssid.id]
                _LOGGER.error("Failed to publish SSID %s with ID %s to MQTT: %s", gwn_ssid.ssidName, gwn_ssid.id, e)

    async def _unpublish_networks(self, old_cache: dict[str, dict[str, object]]) -> None:
        removed_network_ids = set(old_cache) - set(self._cached_networks)
        for network_id in removed_network_ids:
            await self._mqtt_client.unpublish_network(old_cache[network_id])

    async def _unpublish_devices(self, old_cache: dict[str, dict[str, dict[str, object]]]) -> None:
        for network_id, old_devices in old_cache.items():
            new_devices = self._cached_devices.get(network_id, {})
            removed_device_macs = set(old_devices) - set(new_devices)
            for device_mac in removed_device_macs:
                await self._mqtt_client.unpublish_device(old_devices[device_mac])

    async def _unpublish_ssids(self, old_ssid_cache: dict[str, dict[str, dict[str, object]]], old_device_cache: dict[str, dict[str, dict[str, object]]]) -> None:
        for network_id, old_ssids in old_ssid_cache.items():
            new_ssids = self._cached_ssids.get(network_id, {})
            removed_ssid_ids = set(old_ssids) - set(new_ssids)
            old_devices = old_device_cache.get(network_id, {})
            ssid_device_info: list[list[str]] = [
                [device_mac, str(device_payload.get(Constants.NAME, ""))]
                for device_mac, device_payload in old_devices.items()
            ]

            for ssid_id in removed_ssid_ids:
                await self._mqtt_client.unpublish_ssid(old_ssids[ssid_id], ssid_device_info)

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
        old_networks = set(cached_networks)
        old_devices = {network_id: set(devices) for network_id, devices in cached_devices.items()}

        # if the topology changes, then all devices/ssids must be republished
        # create a local copy so that the unpublishing later can also happen
        local_cached_devices: dict[str, dict[str, dict[str, object]]] = cached_devices
        local_cached_ssids: dict[str, dict[str, dict[str, object]]] = cached_ssids
        if old_networks != {network.id for network in gwn_networks}:
            # force a republish of all devices and their topology so the select network updates
            await self._mqtt_client.reset_devices()
            local_cached_devices = {}
        if old_devices != { network.id: { device.mac for device in network.devices} for network in gwn_networks }:
            # force a republish of all ssids and their topology so the assign devices updates
            await self._mqtt_client.reset_ssids()
            local_cached_ssids = {}
    
        for gwn_network in gwn_networks:
            await self._publish_network(gwn_network, cached_networks)
            await self._publish_devices(gwn_network, network_names, local_cached_devices)
            await self._publish_ssids(gwn_network, local_cached_ssids)
        _LOGGER.info(f"Published {len(gwn_networks)} Networks over MQTT")
        _LOGGER.info("Cleaning old data from cache")
        await self._unpublish_networks(cached_networks)
        await self._unpublish_devices(cached_devices)
        await self._unpublish_ssids(cached_ssids, cached_devices)
        _LOGGER.info("Cleaned old data from cache")

    def _enum_value(self, value: Enum | None) -> str | None:
        if value is None:
            return None
        return value.name

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
        payload.networkName = data.get(Constants.NETWORK_NAME, None)
        if await self._gwn_client.set_network_data(payload) and not self._poll_trigger.is_set():
            # immediately refresh/update the data
            self._poll_trigger.set()
    
    async def _handle_device_command(self, device_mac: str, data: dict[str, Any], network_id: str) -> None:    
        payload: GwnDevicePayload = GwnDevicePayload(ap_mac=device_mac, networkId=int(network_id))
        
        payload.reboot = Constants.REBOOT in data
        payload.update = Constants.UPDATE_FIRMWARE in data
        payload.reset = Constants.RESET in data
        payload.target_network = data.get(Constants.NETWORK_NAME, None)
        payload.ap_2g4_channel = data.get(Constants.AP_2G4_CHANNEL, None)
        payload.ap_5g_channel = data.get(Constants.AP_5G_CHANNEL, None)
        payload.ap_6g_channel = data.get(Constants.AP_6G_CHANNEL, None)

        if await self._gwn_client.set_device_data(payload) and not self._poll_trigger.is_set():
            # immediately refresh/update the data
            self._poll_trigger.set()

    async def _handle_ssid_command(self, ssid_id: str, device_macs:list[str], network_id: str, data: dict[str, Any]) -> None:
        payload: GwnSSIDPayload = GwnSSIDPayload(id=int(ssid_id), networkId=int(network_id))

        payload.ssidEnable = data.get(Constants.SSID_ENABLE, None)
        payload.ssidPortalEnable = data.get(Constants.PORTAL_ENABLED, None)
        payload.ssidVlanid = data.get(Constants.SSID_VLAN_ID, None)
        payload.ssidVlan = None if payload.ssidVlanid is None else int(payload.ssidVlanid) > 0
        payload.ghz2_4_enabled = data.get(Constants.GHZ2_4_ENABLED, None)
        payload.ghz5_enabled = data.get(Constants.GHZ5_ENABLED, None)
        payload.ghz6_enabled = data.get(Constants.GHZ6_ENABLED, None)
        payload.ssid_key = data.get(Constants.SSID_KEY, None)
        payload.ssidSsidHidden = data.get(Constants.SSID_HIDDEN, None)
        payload.ssidSsid = data.get(Constants.SSID_NAME, None)
        payload.ssidIsolation = data.get(Constants.CLIENT_ISOLATION_ENABLED, None)
        payload.toggled_macs = data.get(Constants.TOGGLE_DEVICE, None)
        
        if await self._gwn_client.set_ssid_data(device_macs, payload) and not self._poll_trigger.is_set():
            
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
            _LOGGER.error("Failed to connect: %s", e)
            await self._mqtt_client.disconnect()
        return False

    async def run(self) -> None:
        _LOGGER.info("Starting Poll of GWN Manager and MQTT")
        gwn_task = asyncio.create_task(self._run_gwn_interface())
        mqtt_task = asyncio.create_task(self._run_mqtt_interface())
        try:
            await asyncio.gather(gwn_task, mqtt_task)
        finally:
            await self._mqtt_client.disconnect()
            await self._gwn_client.close()
        _LOGGER.info("Application shutting down")

