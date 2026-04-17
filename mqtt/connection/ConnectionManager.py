import logging

from aiomqtt import Client

from mqtt.config import MqttConfig

_LOGGER = logging.getLogger(__name__)


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

    async def connect(self) -> None:
        if self._client is not None:
            return

        client = Client(
            hostname=self._config.host,
            port=self._config.port,
            username=self._config.username,
            password=self._config.password,
            identifier=self._config.client_id,
            keepalive=self._config.keepalive,
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
