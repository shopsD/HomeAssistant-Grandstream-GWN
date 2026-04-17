from dataclasses import dataclass

from mqtt.config.LoggingConfig import LoggingConfig
from mqtt.config.MqttConfig import MqttConfig


@dataclass(slots=True)
class AppConfig:
    mqtt: MqttConfig
    logging: LoggingConfig
