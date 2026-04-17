from dataclasses import dataclass

from gwn.authentication import GwnAuthConfig
from mqtt.config.LoggingConfig import LoggingConfig
from mqtt.config.MqttConfig import MqttConfig


@dataclass(slots=True)
class AppConfig:
    mqtt: MqttConfig
    logging: LoggingConfig
    gwn: GwnAuthConfig
