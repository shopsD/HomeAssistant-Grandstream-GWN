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


    async def _poll_gwn_manager(self) -> None:
        _LOGGER.debug("Polling GWN")
        networks = await self._gwnClient.get_all_networks()
        _LOGGER.debug(f"Found: {networks.length} networks")
        for network in networks:
            network_id = str(network["id"])
            network_name = str(network["networkName"])
            devices = await self._gwnClient.get_all_devices(network_id)
            _LOGGER.debug(f"Found: {devices.length} Devices for Network: {network_name}")
            ssids = await self._gwnClient.get_all_ssids(network_id)
            _LOGGER.debug(f"Found: {ssids.length} SSIDs for Network: {network_name}")

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
        while True:
            self._poll_gwn_manager()
            
            await asyncio.sleep(self._gwnClient.refresh_period)


        
