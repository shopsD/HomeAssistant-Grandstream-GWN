import asyncio
import logging
import json
from typing import Any, Awaitable, Callable

from gwn.constants import Constants
from mqtt.config import MqttConfig
from mqtt.clients import HomeAssistantMqttClient, MqttPublisherClient
from mqtt.connection.MqttInterface import MqttInterface

_LOGGER = logging.getLogger(Constants.LOG)

class MqttClient:
    def __init__(self, config: MqttConfig) -> None:
        self._config: MqttConfig = config
        self._interface: MqttInterface = MqttInterface(config)
        self._application_callback: Callable[[dict[str, Any]], None] | None = None
        self._network_callback: Callable[[str, dict[str, Any]], Awaitable[None]] | None = None
        self._device_callback: Callable[[str, dict[str, Any], str], Awaitable[None]] | None = None
        self._ssid_callback: Callable[[str, list[str], str, dict[str, Any]], Awaitable[None]] | None = None
        self._listen_task: asyncio.Task[None] | None = None
        self._publisher_clients: list[MqttPublisherClient] = [
            HomeAssistantMqttClient(config.homeassistant)
        ]

    async def _listen_to_topics(self) -> None:
        base = self._interface.topic
        topics = [
            f"{base}/{Constants.APPLICATION}/{Constants.SET}",
            f"{base}/{Constants.NETWORKS}/+/{Constants.SET}",
            f"{base}/{Constants.NETWORKS}/+/{Constants.DEVICES}/+/{Constants.SET}",
            f"{base}/{Constants.NETWORKS}/+/{Constants.SSIDS}/+/{Constants.SET}",
            f"{base}/{Constants.GWN}/{Constants.SET}"
        ]
        while True:
            try:
                if not self._interface.is_connected:
                    await self._interface.connect()
                for topic in topics:
                    await self._interface.subscribe(topic)
                    _LOGGER.debug("Subscribed to %s", topic)

                async for message in self._interface.messages:
                    payload: str | bytes = message.payload
                    message_topic: str = str(message.topic)
                    try:
                        decoded_payload = message.payload.decode("utf-8")
                        payload = decoded_payload
                        await self._handle_mqtt_command(message_topic, decoded_payload)
                    except Exception as e:
                        _LOGGER.error(f"Failed to process MQTT command to {message_topic}: {e}")
                        _LOGGER.debug(f"Failed MQTT command: {payload!r}")
            except asyncio.CancelledError:
                raise
            except Exception as e:
                _LOGGER.warning(f"MQTT listener disconnected: {e}")
                await self._interface.disconnect()
                await asyncio.sleep(5)

    async def _handle_mqtt_command(self, topic: str, payload: str) -> None:
        # only process anything that is a set command and starts with the topic
        if (topic.startswith(f"{self._interface.topic}/") and topic.endswith(f"/{Constants.SET}")):
            # only json is allowed
            data = json.loads(payload)
            if not isinstance(data, dict):
                _LOGGER.debug(f"Received malformed data. Received: {data}")
                raise KeyError("MQTT payload must be an object")
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
                _LOGGER.info("Multi Data command")
                network_id = data.get(Constants.NETWORK_ID)
                device_mac = data.get(Constants.MAC)
                ssid_id = data.get(Constants.SSID_ID)
                application_command = network_id is None

                if device_mac is not None and ssid_id is not None:
                    _LOGGER.debug(f"Malformed Payload: {data}")
                    return _LOGGER.warning(f"Only 1 of '{Constants.MAC}' ({device_mac}) and '{Constants.SSID_ID}' ({ssid_id}) can be specified")
                
                if (device_mac is not None or ssid_id is not None) and application_command:
                    _LOGGER.debug(f"Malformed Payload: {data}")
                    return _LOGGER.warning(f"Malformed command. If {Constants.NETWORK_ID} is absent then {Constants.MAC} and {Constants.SSID_ID} must also be absent")

                action_data = data.get(Constants.ACTION)
                input_device_macs: object = ()
                if ssid_id is None and data.get(Constants.DEVICE_MACS, None) is not None:
                    _LOGGER.debug(f"Malformed Payload: {data}")
                    return _LOGGER.warning(f"Malformed command. {Constants.DEVICE_MACS} can only be supplied with {Constants.SSID_ID}")

                if ssid_id is not None:
                    input_device_macs = data.get(Constants.DEVICE_MACS)

                    if not isinstance(input_device_macs, list) or not all(isinstance(item, str) for item in input_device_macs):
                        _LOGGER.debug(f"Malformed {Constants.DEVICE_MACS} entry. Received: {input_device_macs}")
                        raise KeyError(f"{Constants.DEVICE_MACS} must be an array/list of strings")
                    device_macs = input_device_macs

                if not isinstance(action_data, list) or not all(isinstance(item, dict) for item in action_data):
                    _LOGGER.debug(f"Malformed {Constants.ACTION} entry. Received: {action_data}")
                    raise KeyError(f"{Constants.ACTION} must be an array/list of objects")

                for command_data in action_data:
                    formatted_data[command_data[Constants.ACTION]] = command_data.get(Constants.VALUE, None)
                _LOGGER.debug("Formatted Payload: %s", formatted_data)
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
                raw_action_data: object = ()
                raw_device_macs: object = ()
                if ssid_id is None:
                    raw_action_data = data
                else:
                    raw_device_macs = data.get(Constants.DEVICE_MACS)
                    raw_action_data = data.get(Constants.ACTION)

                    if not isinstance(raw_device_macs, list) or not all(isinstance(item, str) for item in raw_device_macs):
                        _LOGGER.debug(f"Malformed {Constants.DEVICE_MACS} entry. Received: {raw_device_macs}")
                        raise KeyError(f"{Constants.DEVICE_MACS} must be an array/list of strings")
                    device_macs = raw_device_macs

                if not isinstance(raw_action_data, dict):
                    _LOGGER.debug(f"Malformed {Constants.ACTION} entry. Received: {raw_action_data}")
                    raise KeyError(f"{Constants.ACTION} must be an object")

                formatted_data = {raw_action_data[Constants.ACTION]: raw_action_data.get(Constants.VALUE, None) }
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

    def _get_device_topic(self, network_id: str, device_mac: str) -> str:
        return f"{self._get_network_topic(network_id)}/{Constants.DEVICES}/{device_mac}"

    def _get_ssid_topic(self, network_id: str, ssid_id: str) -> str:
        return f"{self._get_network_topic(network_id)}/{Constants.SSIDS}/{ssid_id}"

    async def _publish_online_payload(self, application_payload: dict[str,object], clear: bool, clear_autodiscovery: bool) -> None:
        application_topic = f"{self._interface.topic}/{Constants.APPLICATION}"
        await self._interface.publish(f"{application_topic}/{Constants.STATUS}", "" if clear else '{"status": "online"}', retain=True)
        state_topic: str = f"{application_topic}/{Constants.STATE}"
        await self._interface.publish(state_topic, "" if clear else json.dumps(application_payload), retain=True)
        if clear and not clear_autodiscovery:
            return

        exception_occurred: bool = False
        for publisher_client in self._publisher_clients:
            try:
                ha_payload_data = publisher_client.build_application_discovery_payload(state_topic, application_topic, application_payload, clear_autodiscovery)
                for topic, payload in ha_payload_data:
                    await self._interface.publish(topic, "" if clear_autodiscovery else json.dumps(payload), retain=True)
                if not clear_autodiscovery and len(ha_payload_data) > 0:
                    publisher_client.application_published()
            except Exception as e:
                exception_occurred = True
                _LOGGER.error(f"Failed to publish Client specific payload - {state_topic}: {e}")
        if exception_occurred:
            raise Exception("Some exceptions occurred when publishing Application Data")

    async def _publish_network_payload(self, network_payload: dict[str, object], clear: bool, clear_autodiscovery: bool):
        network_id: str = str(network_payload.get(Constants.NETWORK_ID))
        network_topic: str = self._get_network_topic(network_id)
        state_topic: str = f"{network_topic}/{Constants.STATE}"
        await self._interface.publish(state_topic, "" if clear else json.dumps(network_payload),retain=True)
        if clear and not clear_autodiscovery:
            return

        exception_occurred: bool = False
        for publisher_client in self._publisher_clients:
            try:
                ha_payload_data = publisher_client.build_network_discovery_payload(state_topic, network_topic, network_payload, clear_autodiscovery)
                for topic, payload in ha_payload_data:
                    await self._interface.publish(topic, "" if clear_autodiscovery else json.dumps(payload), retain=True)
                if not clear_autodiscovery and len(ha_payload_data) > 0:
                    publisher_client.networks_published(network_topic)
            except Exception as e:
                exception_occurred = True
                _LOGGER.error(f"Failed to publish Client specific payload - {state_topic}: {e}")
        if exception_occurred:
            raise Exception("Some exceptions occurred when publishing networks")

    async def _publish_device_payload(self, device_payload: dict[str, object], network_names: dict[int,str], clear: bool, is_readonly: bool, clear_autodiscovery: bool) -> None:
        network_id: str = str(device_payload.get(Constants.NETWORK_ID))
        device_mac = str(device_payload.get(Constants.MAC))
        device_mac = MqttPublisherClient.strip_mac(device_mac)
        device_topic = self._get_device_topic(network_id,device_mac)

        state_topic: str = f"{device_topic}/{Constants.STATE}"
        await self._interface.publish(state_topic, "" if clear else json.dumps(device_payload), retain=True)
        
        if clear and not clear_autodiscovery:
            return

        exception_occurred: bool = False
        for publisher_client in self._publisher_clients:
            try:
                ha_payload_data = publisher_client.build_device_discovery_payload(state_topic, device_topic, device_payload, network_names, is_readonly, clear_autodiscovery)

                for topic, payload in ha_payload_data:
                    await self._interface.publish(topic, "" if clear_autodiscovery else json.dumps(payload), retain=True)
                if not clear_autodiscovery and len(ha_payload_data) > 0:
                    publisher_client.devices_published(device_topic)
            except Exception as e:
                exception_occurred = True
                _LOGGER.error(f"Failed to publish Client specific payload - {state_topic}: {e}")
        if exception_occurred:
            raise Exception("Some exceptions occurred when publishing devices")

    async def _publish_ssid_payload(self, ssid_payload: dict[str, object], devices: dict[str, str], clear: bool, is_readonly: bool, clear_autodiscovery: bool) -> None:
        network_id: str = str(ssid_payload.get(Constants.NETWORK_ID))
        ssid_id: str = str(ssid_payload.get(Constants.SSID_ID))
        ssid_topic = self._get_ssid_topic(network_id,ssid_id)

        state_topic: str = f"{ssid_topic}/{Constants.STATE}"
        await self._interface.publish(state_topic, "" if clear else json.dumps(ssid_payload), retain=True)
        if clear and not clear_autodiscovery:
            return
        exception_occurred: bool = False
        for publisher_client in self._publisher_clients:
            try:
                ha_payload_data = publisher_client.build_ssid_discovery_payload(state_topic, ssid_topic, ssid_payload, devices, is_readonly, clear_autodiscovery)
                for topic, payload in ha_payload_data:
                    await self._interface.publish(topic, "" if clear_autodiscovery else json.dumps(payload), retain=True)
                if not clear_autodiscovery and len(ha_payload_data) > 0:
                    publisher_client.ssids_published(ssid_topic)
            except Exception as e:
                exception_occurred = True
                _LOGGER.error(f"Failed to publish Client specific payload - {state_topic}: {e}")
        if exception_occurred:
            raise Exception("Some exceptions occurred when publishing SSIDs")

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
        if self._interface.is_connected:
            try:
                await self._publish_offline()
            except Exception as e:
                _LOGGER.warn(f"Failed to publish offline message: {e}")
        return await self._interface.disconnect()

    async def publish_online(self, application_payload: dict[str,object]) -> None:
        await self._publish_online_payload(application_payload, False, False)

    async def publish_network(self, network_payload: dict[str, object]) -> None:
        await self._publish_network_payload(network_payload, False, False)

    async def publish_device(self, device_payload: dict[str, object], network_names: dict[int,str], is_readonly: bool) -> None:
        await self._publish_device_payload(device_payload, network_names, False, is_readonly, False)

    async def publish_ssid(self, ssid_payload: dict[str, object], devices: dict[str, str], is_readonly: bool) -> None:
        await self._publish_ssid_payload(ssid_payload, devices, False, is_readonly, False)

    async def unpublish_online(self, application_payload: dict[str,object], propagate: bool) -> None:
        await self._publish_online_payload(application_payload, True, propagate) # Maybe if uninstalling?

    async def unpublish_network(self, network_payload: dict[str, object], propagate: bool) -> None:
        await self._publish_network_payload(network_payload, True, propagate)

    async def unpublish_device(self, device_payload: dict[str, object], propagate: bool) -> None:
        await self._publish_device_payload(device_payload, {}, True, False, propagate)
        await self._publish_device_payload(device_payload, {}, True, True, propagate) # always clear read only

    async def unpublish_ssid(self, ssid_payload: dict[str, object], devices: dict[str, str], propagate: bool) -> None:
        await self._publish_ssid_payload(ssid_payload, devices, True, False, propagate)
        await self._publish_ssid_payload(ssid_payload, devices, True, True, propagate) # always clear read only

    async def reset_networks(self, network_id: str | None = None) -> None:
        exception_occurred: bool = False
        _LOGGER.debug(f"Resetting {len(self._publisher_clients)} clients MQTT data for Network with ID {network_id}")
        for publisher_client in self._publisher_clients:
            try:
                publisher_client.reset_networks(None if network_id is None else self._get_network_topic(network_id))
            except Exception as e:
                exception_occurred = True
                _LOGGER.error(f"Failed to reset client specific Network with ID {network_id}: {e}")
        if exception_occurred:
            raise Exception("Some exceptions occurred when resetting networks")

    async def reset_devices(self, network_id: str | None = None, device_mac: str | None = None) -> None:
        if (network_id is not None and device_mac is None) or (device_mac is not None and network_id is None):
            raise KeyError("Network ID and MAC must both be none or both be supplied")
        _LOGGER.debug(f"Resetting {len(self._publisher_clients)} clients MQTT data for Device with MAC {device_mac}")
        exception_occurred: bool = False
        device_topic: str | None = None if device_mac is None or network_id is None else self._get_device_topic(network_id, device_mac)
        for publisher_client in self._publisher_clients:
            try:
                publisher_client.reset_devices(device_topic)
            except Exception as e:
                exception_occurred = True
                _LOGGER.error(f"Failed to reset client specific Device with MAC {device_mac}: {e}")
        if exception_occurred:
            raise Exception("Some exceptions occurred when resetting devices")

    async def reset_ssids(self, network_id: str | None = None, ssid_id: str | None = None) -> None:
        if (network_id is not None and ssid_id is None) or (ssid_id is not None and network_id is None):
            raise KeyError("Network ID and SSID ID must both be none or both be supplied")

        exception_occurred: bool = False
        ssid_topic: str | None = None if ssid_id is None or network_id is None else self._get_ssid_topic(network_id, ssid_id)
        _LOGGER.debug(f"Resetting {len(self._publisher_clients)} clients MQTT data for SSID with ID {ssid_id}")
        for publisher_client in self._publisher_clients:
            try:
                publisher_client.reset_ssids(ssid_topic)
            except Exception as e:
                exception_occurred = True
                _LOGGER.error(f"Failed to reset client specific SSID with ID {ssid_id}: {e}")
        if exception_occurred:
            raise Exception("Some exceptions occurred when resetting SSIDs")
