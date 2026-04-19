import logging
import json

from gwn.constants import Constants
from mqtt.config import MqttConfig
from mqtt.connection.MqttInterface import MqttInterface

_LOGGER = logging.getLogger(Constants.LOG)

class MqttClient:
    def __init__(self, config: MqttConfig) -> None:
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
        await self._interface.publish(f"{network_topic}/state",json.dumps(gwn_network),retain=True)
        return network_topic
    
    async def publish_device(self, network_topic: str, device_mac:str, device_payload: dict[str, object]) -> None:
        device_topic = f"{network_topic}/devices/{device_mac}"
        await self._interface.publish(f"{device_topic}/state",json.dumps(device_payload), retain=True)

    async def publish_ssid(self, network_topic: str, gwn_ssid_id: str, ssid_payload: dict[str, object]) -> None:
        ssid_topic = f"{network_topic}/ssids/{gwn_ssid_id}"
        await self._interface.publish(f"{ssid_topic}/state",json.dumps(ssid_payload), retain=True)