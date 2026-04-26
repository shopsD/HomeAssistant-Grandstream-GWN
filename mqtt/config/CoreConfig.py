from dataclasses import dataclass

from gwn.authentication import GwnConfig
from mqtt.config.AppConfig import AppConfig
from mqtt.config.LoggingConfig import LoggingConfig
from mqtt.config.MqttConfig import MqttConfig


@dataclass(slots=True)
class CoreConfig:
    app: AppConfig
    gwn: GwnConfig
    logging: LoggingConfig
    mqtt: MqttConfig
