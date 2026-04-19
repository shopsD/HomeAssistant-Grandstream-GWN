from dataclasses import dataclass, field

@dataclass(slots=True)
class HomeAssistantConfig:
    default_network_autodiscovery: bool = False
    default_device_autodiscovery: bool = False
    default_ssid_autodiscovery: bool = False
    network_autodiscovery: dict[int | str, bool] = field(default_factory=dict)
    device_autodiscovery: dict[int | str, bool] = field(default_factory=dict)
    ssid_autodiscovery: dict[int | str, bool] = field(default_factory=dict)

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
    no_publish: bool = False
    homeassistant: HomeAssistantConfig = field(default_factory=HomeAssistantConfig)
    
