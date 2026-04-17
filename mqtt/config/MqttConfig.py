from dataclasses import dataclass

@dataclass(slots=True)
class MqttConfig:
    host: str = "mqtt://127.0.0.1"
    port: int = 1883
    username: str | None = None
    password: str | None = None
    client_id: str | None = None
    keepalive: int = 60
    topic: str = "gwn"
