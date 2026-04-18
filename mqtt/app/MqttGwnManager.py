import asyncio
import logging

from gwn.api import GwnClient
from gwn.constants import Constants
from mqtt.connection import MqttClient

_LOGGER = logging.getLogger(Constants.LOG)

class AuthenticationError(Exception):
    pass

class RequestError(Exception):
    pass

class MqttGwnManager:
    def __init__(self, mqttClient: MqttClient, gwnClient: GwnClient) -> None:
        self._mqttClient = mqttClient
        self._gwnClient = gwnClient
        self._expiry: int = -1


    async def _run_gwn_interface(self) -> None:
        _LOGGER.debug("Polling GWN")
        while True:
            try:
                networks = await self._gwnClient.get_gwn_data()
                _LOGGER.info(f"Publishing {len(networks)} Networks over MQTT")
            except Exception as e:
                _LOGGER.error("Error retreiving GWN Data: %s", e)
            _LOGGER.info(f"Will refresh in {self._gwnClient.refresh_period}s")
            await asyncio.sleep(self._gwnClient.refresh_period)

    async def _run_mqtt_interface(self) -> None:
        _LOGGER.info("Listening to MQTT")
        await asyncio.Event().wait()

    async def connect(self) -> bool:
        try:
            _LOGGER.info("Connecting to MQTT")
            _LOGGER.debug("Connecting to MQTT")
            if not await self._mqttClient.connect():
                raise AuthenticationError("Failed to connect to MQTT Broker")

            _LOGGER.debug("Connected to MQTT Server")
            _LOGGER.debug("Connecting to GWN Manager")
            if not await self._gwnClient.authenticate():
                raise AuthenticationError("Failed to acquire access token from GWN Manager")

            _LOGGER.debug("Connected to GWN Manager")
            await self._mqttClient.publish(f"{self._mqttClient.topic}/status", "online", retain=True)
            _LOGGER.debug("Published Application status")
            _LOGGER.info("Successfully connected to MQTT and GWN Manager")
            return True
        except Exception as e:
            _LOGGER.error("Failed to connect: %s", e)
            await self._mqttClient.disconnect()
        return False

    async def run(self) -> None:
        _LOGGER.info("Starting Poll of GWN Manager and MQTT")
        gwn_task = asyncio.create_task(self._run_gwn_interface())
        mqtt_task = asyncio.create_task(self._run_mqtt_interface())
        await asyncio.gather(gwn_task, mqtt_task)


        
