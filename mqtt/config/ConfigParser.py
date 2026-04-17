from pathlib import Path
from typing import cast

import yaml

from mqtt.config.AppConfig import AppConfig
from mqtt.config.MqttConfig import MqttConfig
from mqtt.config.LoggingConfig import LogLocation, LoggingConfig

class ConfigParserError(Exception):
    pass

class ConfigParser:
    @staticmethod
    def load(path: str | Path) -> AppConfig:
        config_path = Path(path)

        if not config_path.exists():
            raise ConfigParserError(f"Config file does not exist: {config_path}")

        with config_path.open("r", encoding="utf-8") as file_handle:
            raw = yaml.safe_load(file_handle) or {}

        mqtt_section = raw.get("mqtt")
        if not isinstance(mqtt_section, dict):
            raise ConfigParserError("Missing or invalid 'mqtt' section in config")

        host = mqtt_section.get("host")
        if not host:
            raise ConfigParserError("Missing required mqtt.host")

        logging_section = raw.get("logging", {})
        if not isinstance(logging_section, dict):
            raise ConfigParserError("Invalid 'logging' section in config")

        logging_location = str(logging_section.get("location", "console"))

        if logging_location not in {"syslog", "file", "console"}:
            raise ConfigParserError( "logging.location must be one of: syslog, file, console")

        output_path = logging_section.get("output_path")
        if logging_location == "file" and not output_path:
            raise ConfigParserError("logging.output_path is required when logging.location is 'file'")

        logging_location = cast(LogLocation, logging_location)
        size = int(logging_section.get("size", 0))
        files = int(logging_section.get("files", 1))

        if size < 0:
            raise ConfigParserError("logging.size must be >= 0")

        if files < 1:
            raise ConfigParserError("logging.files must be >= 1")

        return AppConfig(
            mqtt=MqttConfig(
                host=str(host),
                port=int(mqtt_section.get("port", 1883)),
                username=mqtt_section.get("username"),
                password=mqtt_section.get("password"),
                client_id=str(mqtt_section.get("client_id", "gwn-bridge")),
                keepalive=int(mqtt_section.get("keepalive", 60)),
                topic=str(mqtt_section.get("topic", "gwn")),
            ),
            logging=LoggingConfig(
                level=str(logging_section.get("level", "INFO")),
                location=logging_location,
                output_path=Path(output_path) if output_path is not None else None,
                size=size,
                files=files,
            ),
        )
