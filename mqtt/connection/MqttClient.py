import asyncio
import logging
import json
from typing import Any, Awaitable, Callable

from gwn.constants import Constants
from mqtt.config import MqttConfig
from mqtt.connection.HomeAssistantMqttClient import HomeAssistantMqttClient
from mqtt.connection.MqttInterface import MqttInterface

_LOGGER = logging.getLogger(Constants.LOG)

class MqttClient:
    def __init__(self, config: MqttConfig) -> None:
        self._config: MqttConfig = config
        self._interface: MqttInterface = MqttInterface(config)
        self._homeassistant_client: HomeAssistantMqttClient = HomeAssistantMqttClient(config.homeassistant)
        self._application_callback: Callable[[dict[str, Any]], None] | None = None
        self._network_callback: Callable[[str, dict[str, Any]], Awaitable[None]] | None = None
        self._device_callback: Callable[[str, dict[str, Any], str], Awaitable[None]] | None = None
        self._ssid_callback: Callable[[str, list[str], str, dict[str, Any]], Awaitable[None]] | None = None
        self._listen_task: asyncio.Task[None] | None = None

    async def _listen_to_topics(self) -> None:
        base = self._interface.topic
        topics = [
            f"{base}/{Constants.APPLICATION}/{Constants.SET}",
            f"{base}/{Constants.NETWORKS}/+/{Constants.SET}",
            f"{base}/{Constants.NETWORKS}/+/{Constants.DEVICES}/+/{Constants.SET}",
            f"{base}/{Constants.NETWORKS}/+/{Constants.SSIDS}/+/{Constants.SET}",
            f"{base}/{Constants.GWN}/{Constants.SET}"
        ]

        for topic in topics:
            await self._interface.subscribe(topic)
            _LOGGER.debug("Subscribed to %s", topic)

        async for message in self._interface.messages:
            try:
                topic = str(message.topic)
                payload = message.payload.decode("utf-8")
                await self._handle_mqtt_command(topic, payload)
            except Exception as e:
                _LOGGER.error("Failed to process MQTT command: %s", e)

    async def _handle_mqtt_command(self, topic: str, payload: str) -> None:
        # only process anything that is a set command and starts with the topic
        if (topic.startswith(self._interface.topic) and topic.endswith(f"/{Constants.SET}")):
            # only json is allowed
            data = json.loads(payload)
            # buttons only have an action, no value and if action is missing its an unsupported message
            # strip the subscription topic and the set portion
            sub_topic = topic.removeprefix(f"{self._interface.topic}/").removesuffix(f"/{Constants.SET}")
            parts = sub_topic.split("/")
            parts_count = len(parts)

            network_id: str | None = None
            device_mac: str | None = None
            ssid_id: str | None = None
            device_macs: list[str] = []
            formatted_data: dict[str, Any] = {}
            application_command: bool = False
            if parts_count == 1 and parts[0] == Constants.GWN:
                _LOGGER.info(f"Multi Data command: {formatted_data}")
                network_id = data.get(Constants.NETWORK_ID)
                device_mac = data.get(Constants.MAC)
                ssid_id = data.get(Constants.SSID_ID)
                
                if device_mac is not None and ssid_id is not None:
                    return _LOGGER.warning(f"Only 1 of '{Constants.MAC}' ({device_mac}) and '{Constants.SSID_ID}' ({ssid_id}) can be specified")
                
                if ssid_id is None:
                    action_data = data
                else:
                    device_macs = data.get(Constants.DEVICE_MACS)
                    action_data = data.get(Constants.ACTION)

                for command_data in action_data:
                    formatted_data[command_data[Constants.ACTION]] = command_data.get(Constants.VALUE, None)

            else:
                if parts_count == 1 and parts[0] == Constants.APPLICATION:
                    _LOGGER.info("Application command")
                    application_command = True
                elif parts_count == 2 and parts[0] == Constants.NETWORKS :
                    network_id = str(parts[1])
                    _LOGGER.info(f"Network command for {network_id}")
                elif parts_count == 4 and parts[2] == Constants.DEVICES:
                    network_id = str(parts[1])
                    device_mac = str(parts[3])
                    _LOGGER.info(f"Device command for {device_mac} on Network with ID {network_id}")
                elif parts_count == 4 and parts[2] == Constants.SSIDS:
                    network_id = str(parts[1])
                    ssid_id = str(parts[3])
                    _LOGGER.info(f"SSID command for SSID {ssid_id} on Network with ID {network_id}")
                else:
                    return _LOGGER.warning("Unhandled MQTT command topic: %s", topic)
                if ssid_id is None:
                    action_data = data
                else:
                    device_macs = data.get(Constants.DEVICE_MACS)
                    action_data = data.get(Constants.ACTION)
                formatted_data = {action_data[Constants.ACTION]: action_data.get(Constants.VALUE, None) }
                _LOGGER.debug("Formatted Payload: %s", formatted_data)

            if application_command and self._application_callback is not None:
                self._application_callback(formatted_data)
            elif network_id is None:
                _LOGGER.warning("No Network ID specified")
            elif self._ssid_callback is not None and ssid_id is not None:
                await self._ssid_callback(ssid_id, device_macs, network_id, formatted_data)
            elif self._device_callback is not None and device_mac is not None:
                await self._device_callback(device_mac, formatted_data, network_id)
            elif self._network_callback is not None:
                await self._network_callback(network_id, formatted_data)

    async def _publish_offline(self) -> None:
        await self._interface.publish(f"{self._interface.topic}/{Constants.APPLICATION}/{Constants.STATUS}", '{"status": "offline"}', retain=True)

    def _get_network_topic(self, network_id: str) -> str:
        return f"{self._interface.topic}/{Constants.NETWORKS}/{network_id}"

    async def _publish_online_payload(self, application_payload: dict[str,object], clear: bool) -> None:
        application_topic = f"{self._interface.topic}/{Constants.APPLICATION}"
        await self._interface.publish(f"{application_topic}/{Constants.STATUS}", "" if clear else '{"status": "online"}', retain=True)
        state_topic: str = f"{application_topic}/{Constants.STATE}"
        await self._interface.publish(state_topic, "" if clear else json.dumps(application_payload), retain=True)
        ha_payload_data = self._homeassistant_client.build_application_discovery_payload(state_topic, application_topic, application_payload, clear)
        for topic, payload in ha_payload_data:
            await self._interface.publish(topic, "" if clear else json.dumps(payload), retain=True)
        if not clear:
            self._homeassistant_client.application_published()

    async def _publish_network_payload(self, network_payload: dict[str, object], clear: bool):
        network_id: str = str(network_payload.get(Constants.NETWORK_ID))
        network_topic: str = self._get_network_topic(network_id)
        state_topic: str = f"{network_topic}/{Constants.STATE}"
        await self._interface.publish(state_topic, "" if clear else json.dumps(network_payload),retain=True)
        ha_payload_data = self._homeassistant_client.build_network_discovery_payload(state_topic, network_topic, network_payload, clear)
        for topic, payload in ha_payload_data:
            await self._interface.publish(topic, "" if clear else json.dumps(payload), retain=True)
        if not clear:
            self._homeassistant_client.networks_published(network_topic)

    async def _publish_device_payload(self, device_payload: dict[str, object], network_names: dict[int,str], clear: bool) -> None:
        network_id: str = str(device_payload.get(Constants.NETWORK_ID))
        network_topic: str = self._get_network_topic(network_id)
        device_mac = str(device_payload.get(Constants.MAC))
        device_mac = self._homeassistant_client.strip_mac(device_mac)
        device_topic = f"{network_topic}/{Constants.DEVICES}/{device_mac}"

        state_topic: str = f"{device_topic}/{Constants.STATE}"
        await self._interface.publish(state_topic, "" if clear else json.dumps(device_payload), retain=True)
        ha_payload_data = self._homeassistant_client.build_device_discovery_payload(state_topic, device_topic, device_payload, network_names, clear)
        for topic, payload in ha_payload_data:
            await self._interface.publish(topic, "" if clear else json.dumps(payload), retain=True)
        if not clear:
            self._homeassistant_client.devices_published(device_topic)

    async def _publish_ssid_payload(self, ssid_payload: dict[str, object], devices: list[list[str]], clear: bool) -> None:
        network_id: str = str(ssid_payload.get(Constants.NETWORK_ID))
        network_topic: str = self._get_network_topic(network_id)
        ssid_id: str = str(ssid_payload.get(Constants.SSID_ID))
        ssid_topic = f"{network_topic}/{Constants.SSIDS}/{ssid_id}"

        state_topic: str = f"{ssid_topic}/{Constants.STATE}"
        await self._interface.publish(state_topic, "" if clear else json.dumps(ssid_payload), retain=True)
        ha_payload_data = self._homeassistant_client.build_ssid_discovery_payload(state_topic, ssid_topic, ssid_payload, devices, clear)
        for topic, payload in ha_payload_data:
            await self._interface.publish(topic, "" if clear else json.dumps(payload), retain=True)
        if not clear:
            self._homeassistant_client.ssids_published(ssid_topic)


    @property
    def is_connected(self) -> bool:
        return self._interface.is_connected

    def set_application_callback(self, callback: Callable[[dict[str, Any]], None]) -> None:
        self._application_callback = callback

    def set_network_callback(self, callback: Callable[[str, dict[str, Any]], Awaitable[None]]) -> None:
        self._network_callback = callback

    def set_device_callback(self, callback: Callable[[str, dict[str, Any], str], Awaitable[None]]) -> None:
        self._device_callback = callback

    def set_ssid_callback(self, callback: Callable[[str, list[str], str, dict[str, Any]], Awaitable[None]]) -> None:
        self._ssid_callback = callback

    async def connect(self) -> bool:
        if await self._interface.connect():
            self._listen_task = asyncio.create_task(self._listen_to_topics())
            return True
        return False

    async def disconnect(self) -> None:
        if self._listen_task is not None:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None
        await self._publish_offline()
        return await self._interface.disconnect()
    
    async def publish_online(self, application_payload: dict[str,object]) -> None:
        await self._publish_online_payload(application_payload, False)

    async def publish_network(self, network_payload: dict[str, object]) -> None:
        await self._publish_network_payload(network_payload, False)

    async def publish_device(self, device_payload: dict[str, object], network_names: dict[int,str]) -> None:
        await self._publish_device_payload(device_payload, network_names, False)

    async def publish_ssid(self, ssid_payload: dict[str, object], devices: list[list[str]]) -> None:
        await self._publish_ssid_payload(ssid_payload, devices, False)

    async def unpublish_online(self, application_payload: dict[str,object]) -> None:
        await self._publish_online_payload(application_payload, True) # Maybe if uninstalling?

    async def unpublish_network(self, network_payload: dict[str, object]) -> None:
        await self._publish_network_payload(network_payload, True)

    async def unpublish_device(self, device_payload: dict[str, object]) -> None:
        await self._publish_device_payload(device_payload, {}, True)

    async def unpublish_ssid(self, ssid_payload: dict[str, object], devices: list[list[str]]) -> None:
        await self._publish_ssid_payload(ssid_payload, devices, True)
