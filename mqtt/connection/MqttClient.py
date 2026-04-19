import logging
import json

from gwn.constants import Constants
from mqtt.config import MqttConfig, MqttPayloadFormat
from mqtt.connection.MqttInterface import MqttInterface

_LOGGER = logging.getLogger(Constants.LOG)

class MqttClient:
    def __init__(self, config: MqttConfig) -> None:
        self._config = config
        self._interface = MqttInterface(config)

    @property
    def is_connected(self) -> bool:
        return self._interface.is_connected

    async def connect(self) -> bool:
        return await self._interface.connect()

    async def disconnect(self) -> None:
        return await self._interface.disconnect()

    async def publish_online(self) -> None:
        await self._interface.publish(f"{self._interface.topic}/status", "online", retain=True)

    async def publish_network(self, gwn_network_id: str, gwn_network: dict[str, object]) -> str:
        network_topic = f"{self._interface.topic}/networks/{gwn_network_id}"
        
        gwn_network_id_int: int = int(gwn_network_id)
        payload_format: MqttPayloadFormat = MqttPayloadFormat.BOTH if gwn_network_id_int not in self._config.network_payload else self._config.network_payload[gwn_network_id_int]
        if payload_format != MqttPayloadFormat.HOMEASSISTANT:
            await self._interface.publish(f"{network_topic}/state",json.dumps(gwn_network),retain=True)
        if payload_format != MqttPayloadFormat.GENERIC:
            stub = 0
            # TODO: Else shape for Home Assistant
            
        return network_topic
    
    async def publish_device(self, network_topic: str, device_mac:str, device_payload: dict[str, object]) -> None:
        device_topic = f"{network_topic}/devices/{device_mac}"
        
        payload_format: MqttPayloadFormat = MqttPayloadFormat.BOTH if device_mac not in self._config.device_payload else self._config.device_payload[device_mac]
        if payload_format != MqttPayloadFormat.HOMEASSISTANT:
            await self._interface.publish(f"{device_topic}/state",json.dumps(device_payload), retain=True)
        if payload_format != MqttPayloadFormat.GENERIC:
            stub = 0
            # TODO: Else shape for Home Assistant

    async def publish_ssid(self, network_topic: str, gwn_ssid_id: str, ssid_payload: dict[str, object]) -> None:
        ssid_topic = f"{network_topic}/ssids/{gwn_ssid_id}"
        gwn_ssid_id_int: int = int(gwn_ssid_id)
        payload_format: MqttPayloadFormat = MqttPayloadFormat.BOTH if gwn_ssid_id_int not in self._config.ssid_payload else self._config.ssid_payload[gwn_ssid_id_int]
        if payload_format != MqttPayloadFormat.HOMEASSISTANT:
            await self._interface.publish(f"{ssid_topic}/state",json.dumps(ssid_payload), retain=True)
        if payload_format != MqttPayloadFormat.GENERIC:
            stub = 0
            # TODO: Else shape for Home Assistant
