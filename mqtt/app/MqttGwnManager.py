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

    async def _run_gwn_interface(self) -> None:
        _LOGGER.debug("Polling GWN")
        while True:
            try:
                networks = await self._gwn_client.get_gwn_data()
                
                await self._publish_network(networks)
            except Exception as e:
                _LOGGER.error("Error retreiving GWN Data: %s", e)
            _LOGGER.info(f"Will refresh in {self._gwn_client.refresh_period}s")
            await asyncio.sleep(self._gwn_client.refresh_period)
        _LOGGER.info("Stopped Polling of GWN Manager")

    async def _run_mqtt_interface(self) -> None:
        _LOGGER.info("Listening to MQTT")
        
        await asyncio.Event().wait()
        _LOGGER.info("Stopped listening to MQTT")

    def _build_ssid_assignments(self, devices: list[GwnDevice]) -> dict[str, list[dict[str, str]]]:
        ssid_assignments: dict[str, list[dict[str, str]]] = {}
        for gwn_device in devices:
            for gwn_ssid in gwn_device.ssids:
                if gwn_ssid.id not in ssid_assignments:
                    ssid_assignments[gwn_ssid.id] = []
                ssid_assignments[gwn_ssid.id].append(
                    {
                        "mac": gwn_device.mac,
                        "name": gwn_device.name,
                        "apType": gwn_device.apType,
                    }
                )
        return ssid_assignments
                
    async def _publish_network(self, gwn_networks: list[GwnNetwork]) -> None:
        _LOGGER.info(f"Publishing {len(gwn_networks)} Networks over MQTT")
        for gwn_network in gwn_networks:
            ssid_assignments: dict[str, list[dict[str, str]]] = self._build_ssid_assignments(gwn_network.devices)
            _LOGGER.debug(f"Publishing Network: {gwn_network.networkName} with ID {gwn_network.id} to MQTT")
            network_topic = ""
            try:
                network_topic = await self._mqtt_client.publish_network(gwn_network.id, self._serialise_network(gwn_network))
            except Exception as e:
                _LOGGER.error(f"Failed to publish Network {gwn_network.networkName} with ID {gwn_network.id} to MQTT: %s", e)
                continue
            # devices may share an SSID so dont republish it again if it already was published
            published_ssids: set[str] = set()
            for gwn_device in gwn_network.devices:
                _LOGGER.debug(f"Publishing Device {gwn_device.mac} to MQTT")
                try:
                    device_payload = self._serialise_device(gwn_network, gwn_device)
                    await self._mqtt_client.publish_device(network_topic, gwn_network.networkName, device_payload)
                except Exception as e:
                    _LOGGER.error(f"Failed to publish Device {gwn_device.mac} to MQTT: %s", e)
                    continue
                for gwn_ssid in gwn_device.ssids:
                    if gwn_ssid.id not in published_ssids: 
                        _LOGGER.debug(f"Publishing SSID: {gwn_ssid.ssidName} with ID {gwn_ssid.id} to MQTT")
                        try:
                            ssid_payload = self._serialise_ssid(gwn_ssid, ssid_assignments.get(gwn_ssid.id, []))
                            await self._mqtt_client.publish_ssid(network_topic,gwn_network.networkName, gwn_ssid.id, ssid_payload )
                            published_ssids.add(gwn_ssid.id) # dont republish this SSID
                        except Exception as e:
                            _LOGGER.error(f"Failed to publish SSID {gwn_ssid.ssidName} with ID {gwn_ssid.id} to MQTT: %s", e)
                            continue

        _LOGGER.info(f"Published {len(gwn_networks)} Networks over MQTT")

    def _enum_value(self, value: Enum | None) -> str | None:
        if value is None:
            return None
        return value.name

    def _serialise_ssid(self, gwn_ssid: GwnSSID, assigned_devices: list[dict[str, str]]) -> dict[str, object]:
        return {
            "id": gwn_ssid.id,
            "ssidName": gwn_ssid.ssidName,
            "wifiEnabled": gwn_ssid.wifiEnabled,
            "onlineDevices": gwn_ssid.onlineDevices,
            "scheduleEnabled": gwn_ssid.scheduleEnabled,
            "portalEnabled": gwn_ssid.portalEnabled,
            "macFilteringEnabled": self._enum_value(gwn_ssid.macFilteringEnabled),
            "clientIsolationEnabled": gwn_ssid.clientIsolationEnabled,
            "ssidIsolationMode": self._enum_value(gwn_ssid.ssidIsolationMode),
            "ssidIsolation": gwn_ssid.ssidIsolation,
            "ssidSsidHidden": gwn_ssid.ssidSsidHidden,
            "ssidVlanid": gwn_ssid.ssidVlanid,
            "ssidVlanEnabled": gwn_ssid.ssidVlanEnabled,
            "ssidEnable": gwn_ssid.ssidEnable,
            "ssidRemark": gwn_ssid.ssidRemark,
            "ssidKey": gwn_ssid.ssidKey,
            "ghz2_4_Enabled": gwn_ssid.ghz2_4_Enabled,
            "ghz5_Enabled": gwn_ssid.ghz5_Enabled,
            "ghz6_Enabled": gwn_ssid.ghz6_Enabled,
            "assignedDevices": assigned_devices
        }

    def _serialise_device(self, gwn_network: GwnNetwork, gwn_device: GwnDevice) -> dict[str, object]:
        return {
            "status": gwn_device.status,
            "apType": gwn_device.apType,
            "mac": gwn_device.mac,
            "name": gwn_device.name,
            "ip": gwn_device.ip,
            "upTime": gwn_device.upTime,
            "usage": gwn_device.usage,
            "upload": gwn_device.upload,
            "download": gwn_device.download,
            "clients": gwn_device.clients,
            "versionFirmware": gwn_device.versionFirmware,
            "ipv6": gwn_device.ipv6,
            "newFirmware": gwn_device.newFirmware,
            "wireless": gwn_device.wireless,
            "vlanCount": gwn_device.vlanCount,
            "ssidNumber": gwn_device.ssidNumber,
            "online": gwn_device.online,
            "model": gwn_device.model,
            "deviceType": gwn_device.deviceType,
            "channel_5": gwn_device.channel_5,
            "channel_2_4": gwn_device.channel_2_4,
            "channel_6": gwn_device.channel_6,
            "partNumber": gwn_device.partNumber,
            "bootVersion": gwn_device.bootVersion,
            "network": gwn_device.network,
            "temperature": gwn_device.temperature,
            "usedMemory": gwn_device.usedMemory,
            "channelload_2g4": gwn_device.channelload_2g4,
            "channelload_6g": gwn_device.channelload_6g,
            "cpuUsage": gwn_device.cpuUsage,
            "channelload_5g": gwn_device.channelload_5g,
            "networkName": gwn_network.networkName,
            "ssids": [
                {
                    "id": ssid.id,
                    "ssidName": ssid.ssidName,
                }
                for ssid in gwn_device.ssids
            ]
        }

    def _serialise_network(self, gwn_network: GwnNetwork) -> dict[str, object]:
        return {
            "id": gwn_network.id,
            "networkName": gwn_network.networkName,
            "countryDisplay": gwn_network.countryDisplay,
            "timezone": gwn_network.timezone
        }
    
    def _handle_application_command(self, data: dict[str, Any]) -> None:
        _LOGGER.info(f"Command {data}")
        update_version = data.get("update_version")
        restart = data.get("restart")
        _LOGGER.info(f"Command {update_version} {restart}")

    def _handle_network_command(self, network_id: str, data: dict[str, Any]) -> None:
        _LOGGER.info(f"Command {network_id} {data}")
        network_name = data.get("networkName")
        _LOGGER.info(f"Command {network_name}")

    def _handle_device_command(self, device_mac: str, network_id: str, data: dict[str, Any]) -> None:
        _LOGGER.info(f"Command {device_mac} {data}")
        reboot = data.get("reboot")
        update_firmware = data.get("update_firmware")
        reset = data.get("reset")
        network_name = data.get("networkName")
        wireless = data.get("wireless")
        channel_2_4 = data.get("channel_2_4")
        channel_5 = data.get("channel_5")
        channel_6 = data.get("channel_6")
        _LOGGER.info(f"Command {reboot} {update_firmware} {reset} {network_name} {wireless} {channel_2_4} {channel_5} {channel_6}")

    def _handle_ssid_command(self, ssid_id: str, network_id: str, data: dict[str, Any]) -> None:
        _LOGGER.info(f"Command {ssid_id} {data}")
        ssid_enable = data.get("ssidEnable")
        portale_enabled = data.get("portalEnabled")
        vlan_id = data.get("ssidVlanid")
        vlan_enabled = None if vlan_id is None else int(vlan_id) > 0
        client_isolation_enabled = data.get("clientIsolationEnabled")
        ghz2_4_enabled = data.get("ghz2_4_Enabled")
        ghz5_enabled = data.get("ghz5_Enabled")
        ghz6_enabled = data.get("ghz6_Enabled")
        ssid_key = data.get("ssidKey")
        ssid_hidden = data.get("ssidSsidHidden")
        ssid_name = data.get("ssidName")
        _LOGGER.info(f"Command {ssid_enable} {portale_enabled} {vlan_id} {vlan_enabled} {client_isolation_enabled} {ghz2_4_enabled} {ghz5_enabled} {ghz6_enabled} {ssid_key} {ssid_hidden} {ssid_name}")
    
    async def connect(self) -> bool:
        try:
            _LOGGER.info("Connecting to MQTT")
            if not await self._mqtt_client.connect():
                raise AuthenticationError("Failed to connect to MQTT Broker")
            _LOGGER.debug("Connected to MQTT Server")
            self._mqtt_client.set_application_callback(self._handle_application_command)
            self._mqtt_client.set_network_callback(self._handle_network_command)
            self._mqtt_client.set_device_callback(self._handle_device_command)
            self._mqtt_client.set_ssid_callback(self._handle_ssid_command)
            _LOGGER.debug("Registered MQTT Handlers")

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

