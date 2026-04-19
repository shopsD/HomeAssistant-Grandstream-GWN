from dataclasses import dataclass, field
from enum import Enum

class MqttPayloadFormat(Enum):
    BOTH = 0
    GENERIC = 1
    HOMEASSISTANT = 2

@dataclass(slots=True)
class MqttConfig:
    host: str = "127.0.0.1"
    port: int = 1883
    username: str | None = None
    password: str | None = None
    client_id: str | None = None
    keepalive: int = 60
    topic: str = "gwn"
    tls: bool = False
    verify_tls: bool = True
    default_network_payload: MqttPayloadFormat = MqttPayloadFormat.GENERIC
    default_device_payload: MqttPayloadFormat = MqttPayloadFormat.GENERIC
    default_ssid_payload: MqttPayloadFormat = MqttPayloadFormat.GENERIC
    network_payload: dict[int | str, MqttPayloadFormat] = field(default_factory=dict)
    device_payload: dict[int | str, MqttPayloadFormat] = field(default_factory=dict)
    ssid_payload: dict[int | str, MqttPayloadFormat] = field(default_factory=dict)
