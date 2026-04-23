import asyncio
import logging
from enum import Enum
from typing import Any

from gwn.api import GwnClient
from gwn.constants import Constants
from gwn.request_data import GwnDevice, GwnNetwork, GwnSSID
from mqtt.connection import MqttClient

_LOGGER = logging.getLogger(Constants.LOG)

class AuthenticationError(Exception):
    pass

class RequestError(Exception):
    pass

class MqttGwnManager:
    def __init__(self, mqtt_client: MqttClient, gwn_client: GwnClient) -> None:
        self._mqtt_client = mqtt_client
        self._gwn_client = gwn_client
        self._poll_trigger = asyncio.Event()

    async def _run_gwn_interface(self) -> None:
        _LOGGER.debug("Polling GWN")
        while True:
            try:
                networks = await self._gwn_client.get_gwn_data()
                await self._publish_network(networks)
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

    async def _publish_network(self, gwn_networks: list[GwnNetwork]) -> None:
        _LOGGER.info(f"Publishing {len(gwn_networks)} Networks over MQTT")
        for gwn_network in gwn_networks:
            device_assignments: dict[str, list[GwnSSID]] = self._build_device_assignments(gwn_network.ssids)
            _LOGGER.debug(f"Publishing Network: {gwn_network.networkName} with ID {gwn_network.id} to MQTT")
            network_topic = ""
            try:
                network_topic = await self._mqtt_client.publish_network(gwn_network.id, self._serialise_network(gwn_network))
            except Exception as e:
                _LOGGER.error(f"Failed to publish Network {gwn_network.networkName} with ID {gwn_network.id} to MQTT: %s", e)
                continue
            _LOGGER.info(f"Publishing {len(gwn_network.devices)} Devices for Network {gwn_network.id} ({gwn_network.networkName}) over MQTT")
            ssid_device_info: list[list[str]] = [] # build a stripped down and full list of devices for use in SSID toggles
            for gwn_device in gwn_network.devices:
                _LOGGER.debug(f"Publishing Device {gwn_device.mac} to MQTT")
                ssid_device_info.append([gwn_device.mac,gwn_device.name])
                try:
                    assignments: list[GwnSSID] = device_assignments.get(gwn_device.mac, [])
                    device_payload = self._serialise_device(gwn_network, gwn_device, assignments)
                    await self._mqtt_client.publish_device(network_topic, int(gwn_network.id), gwn_network.networkName, device_payload)
                except Exception as e:
                    _LOGGER.error(f"Failed to publish Device {gwn_device.mac} to MQTT: %s", e)
                    continue
            _LOGGER.info(f"Publishing {len(gwn_network.ssids)} Devices for Network {gwn_network.id} ({gwn_network.networkName}) over MQTT")
            for gwn_ssid in gwn_network.ssids:
                _LOGGER.debug(f"Publishing SSID: {gwn_ssid.ssidName} with ID {gwn_ssid.id} to MQTT")
                try:
                    ssid_payload = self._serialise_ssid(gwn_network, gwn_ssid)
                    await self._mqtt_client.publish_ssid(network_topic, int(gwn_network.id), gwn_network.networkName, ssid_device_info, gwn_ssid.id, ssid_payload)
                except Exception as e:
                    _LOGGER.error(f"Failed to publish SSID {gwn_ssid.ssidName} with ID {gwn_ssid.id} to MQTT: %s", e)

        _LOGGER.info(f"Published {len(gwn_networks)} Networks over MQTT")

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
            Constants.ASSIGNED_DEVICES: { device.mac: device.name for device in gwn_ssid.devices }
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
            Constants.SSIDS: [
                {
                    Constants.SSID_ID: ssid.id,
                    Constants.SSID_NAME: ssid.ssidName,
                }
                for ssid in ssids
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
        await self._gwn_client.set_network_data(network_id, data)
    
    async def _handle_device_command(self, device_mac: str, data: dict[str, Any], network_id: str) -> None:
        await self._gwn_client.set_device_data(device_mac, network_id, data)

    async def _handle_ssid_command(self, ssid_id: str, device_macs:list[str], network_id: str, data: dict[str, Any]) -> None:
        if await self._gwn_client.set_ssid_data(ssid_id, device_macs, data, network_id) and not self._poll_trigger.is_set():
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

