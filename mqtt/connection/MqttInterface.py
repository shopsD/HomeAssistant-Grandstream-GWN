import logging
import ssl

from aiomqtt import Client

from gwn.constants import Constants
from mqtt.config import MqttConfig

_LOGGER = logging.getLogger(Constants.LOG)

class MqttInterface:
    def __init__(self, config: MqttConfig) -> None:
        self._config: MqttConfig = config
        self._client: Client | None = None
        self._connected: bool = False

    def _ensure_client(self) -> Client:
        if self._client is None:
            raise RuntimeError("MQTT client is not connected")
        return self._client

    async def _authenticated_client(self) -> Client:
        if self._client is None:
            await self.connect()
        return self._ensure_client()

    @property
    def is_connected(self) -> bool:
        return self._connected and self._client is not None

    @property
    def topic(self) -> str:
        return self._config.topic

    @property
    def messages(self):
        return self._ensure_client().messages

    async def connect(self) -> bool:
        _LOGGER.info(f"Connecting to MQTT broker {self._config.host}:{self._config.port}")
        if self._client is not None:
            _LOGGER.error("Client is already connected")
            return self._connected
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
        _LOGGER.info(f"Connected to MQTT broker at {self._config.host}:{self._config.port}")
        return self._connected

    async def disconnect(self) -> None:
        if self._client is None:
            return
        client = self._client
        self._client = None
        self._connected = False

        await client.__aexit__(None, None, None)

        _LOGGER.info("Disconnected from MQTT broker")

    async def publish(self, topic: str, payload: str, retain: bool = False) -> None:
        if not self._config.no_publish:
            client = await self._authenticated_client()
            try:
                await client.publish(topic, payload, retain=retain)
            except Exception as e:
                _LOGGER.warn(f"MQTT Publish failed. Retrying publish: {e}")
                await self.disconnect()
                client = await self._authenticated_client()
                await client.publish(topic, payload, retain=retain)

    async def subscribe(self, topic: str) -> None:
        client = await self._authenticated_client()
        try:
            await client.subscribe(topic)
        except Exception as e:
            _LOGGER.warn(f"MQTT Subscribe failed. Retrying subscribe: {e}")
            await self.disconnect()
            client = await self._authenticated_client()
            await client.subscribe(topic)
