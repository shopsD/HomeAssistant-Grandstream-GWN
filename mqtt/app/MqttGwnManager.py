import asyncio
import logging

from gwn.api import GwnClient
from gwn.authentication import GwnToken
from gwn.constants import Constants
from mqtt.connection import ConnectionManager

_LOGGER = logging.getLogger(Constants.LOG)


class MqttGwnManager:
    def __init__(self, mqttClient: ConnectionManager, gwnClient: GwnClient) -> None:
        self._mqttClient = mqttClient
        self._gwnClient = gwnClient
        self._access_token: GwnToken | None = None
        self._expiry: int = -1


    async def _run_gwn_interface(self) -> None:
        _LOGGER.debug("Polling GWN")
        while True:
            networks = await self._gwnClient.get_all_networks()
            _LOGGER.debug(f"Found: {len(networks)} networks")
            for network in networks:
                network_id = str(network["id"])
                network_name = str(network["networkName"])
                devices = await self._gwnClient.get_all_devices(network_id)
                _LOGGER.debug(f"Found: {len(devices)} Devices for Network: {network_name}")
                ssids = await self._gwnClient.get_all_ssids(network_id)
                _LOGGER.debug(f"Found: {len(ssids)} SSIDs for Network: {network_name}")
            await asyncio.sleep(self._gwnClient.refresh_period)

    async def _run_mqtt_interface(self) -> None:
        _LOGGER.info("Listening to MQTT")
        await asyncio.Event().wait()

    async def connect(self) -> bool:
        try:
            _LOGGER.info("Connecting to MQTT")
            _LOGGER.debug("Connecting to MQTT")
            await self._mqttClient.connect()
            _LOGGER.debug("Connected to MQTT Server")
            _LOGGER.debug("Connecting to GWN Manager")
            self._access_token = await self._gwnClient.authenticate()
            _LOGGER.debug("Connected to GWN Manager")
            await self._mqttClient.publish(f"{self._mqttClient.topic}/status", "hello world", retain=True)
            _LOGGER.debug("Published Application status")
            _LOGGER.info("Successfully connected to MQTT and GWN Manager")
            return True
        except Exception as e:
            _LOGGER.error("Failed to connect: %s", e)
            await self._mqttClient.disconnect()
        return False

    async def run(self):
        _LOGGER.info("Starting Poll of GWN Manager and MQTT")
        gwn_task = asyncio.create_task(self._run_gwn_interface())
        mqtt_task = asyncio.create_task(self._run_mqtt_interface())
        await asyncio.gather(gwn_task, mqtt_task)


        
