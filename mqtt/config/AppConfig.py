from dataclasses import dataclass

from gwn.authentication import GwnConfig
from mqtt.config.LoggingConfig import LoggingConfig
from mqtt.config.MqttConfig import MqttConfig


@dataclass(slots=True)
class AppConfig:
    mqtt: MqttConfig
    logging: LoggingConfig
    gwn: GwnConfig
