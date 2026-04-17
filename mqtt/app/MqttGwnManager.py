import logging

from aiomqtt import Client

from mqtt.connection import ConnectionManager
from gwn.api import GwnClient
from gwn.authentication import GwnToken

_LOGGER = logging.getLogger(__name__)


class MqttGwnManager:
    def __init__(self, mqttClient: ConnectionManager, gwnClient: GwnClient) -> None:
        self._mqttClient = connectionManager
        self._gwnClient = gwnClient
        self._access_token: GwnToken | None = None
        self._expiry: int = -1

    async def connect(self):
        try:
            _LOGGER.info("Connecting to MQTT")
            _LOGGER.debug("Connecting to MQTT")
            await self._mqttClient.connect()
            _LOGGER.debug("Connected to MQTT Server")
            _LOGGER.debug("Connecting to GWN Manager")
            self._access_token = _gwnClient.authenticate()
            _LOGGER.debug("Connected to GWN Manager")
            await self._mqttClient.publish(f"{app_config.mqtt.topic}/status", "online", retain=True)
            _LOGGER.debug("Published Application status")
            _LOGGER.info("Successfully connected to MQTT and GWN Manager")
        except (e):
            _LOGGER.debug(f"Failed to connect: {e}")
            await self._mqttClient.disconnect()

    async def run(self):
        _LOGGER.info("Listening for Events")
        await asyncio.Event().wait()
        
