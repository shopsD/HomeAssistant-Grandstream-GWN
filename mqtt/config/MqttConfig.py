from dataclasses import dataclass, field
from pathlib import Path

@dataclass(slots=True)
class HomeAssistantConfig:
    discovery_topic: str = "homeassistant"
    always_publish_autodiscovery: bool = False
    application_autodiscovery: bool = False
    default_network_autodiscovery: bool = False
    default_device_autodiscovery: bool = False
    default_ssid_autodiscovery: bool = False
    network_autodiscovery: dict[int | str, bool] = field(default_factory=dict)
    device_autodiscovery: dict[int | str, bool] = field(default_factory=dict)
    ssid_autodiscovery: dict[int | str, bool] = field(default_factory=dict)
    network_name_override: dict[int | str, str] = field(default_factory=dict)
    device_name_override: dict[int | str, str] = field(default_factory=dict)
    ssid_name_override: dict[int | str, str] = field(default_factory=dict)

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
    topic_manifest_path: Path | None = None
    no_publish: bool = False
    homeassistant: HomeAssistantConfig = field(default_factory=HomeAssistantConfig)

