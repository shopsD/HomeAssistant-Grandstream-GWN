import logging
import ssl

from aiomqtt import Client

import constants

from mqtt.config import MqttConfig

_LOGGER = logging.getLogger(constants.Constants.LOG)

class ConnectionManager:
    def __init__(self, config: MqttConfig) -> None:
        self._config = config
        self._client: Client | None = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def client(self) -> Client:
        if self._client is None:
            raise RuntimeError("MQTT client is not connected")
        return self._client

    @property
    def topic(self) -> str:
        return self._config.topic

    async def connect(self) -> None:
        _LOGGER.info("Connecting to MQTT")
        if self._client is not None:
            _LOGGER.error("Client is already connected")
            return
        tls_context = None
        if self._config.tls:
            tls_context = ssl.create_default_context()
        client = Client(
            hostname=self._config.host,
            port=self._config.port,
            username=self._config.username,
            password=self._config.password,
            identifier=self._config.client_id,
            keepalive=self._config.keepalive,
            tls_context = tls_context,
            tls_insecure=not self._config.verify_tls,
            logger = _LOGGER
        )

        await client.__aenter__()
        self._client = client
        self._connected = True
        _LOGGER.info("Connected to MQTT broker at %s:%s", self._config.host, self._config.port)

    async def disconnect(self) -> None:
        if self._client is None:
            return

        await self._client.__aexit__(None, None, None)
        self._client = None
        self._connected = False
        _LOGGER.info("Disconnected from MQTT broker")

    async def publish(self, topic: str, payload: str, retain: bool = False) -> None:
        await self.client.publish(topic, payload, retain=retain)
