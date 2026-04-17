from pathlib import Path
from typing import cast

import logging
import yaml

from gwn.authentication import GwnAuthConfig
from mqtt.config.AppConfig import AppConfig
from mqtt.config.MqttConfig import MqttConfig
from mqtt.config.LoggingConfig import LogLocation, LoggingConfig

_LOGGER = logging.getLogger(__name__)

class ConfigParserError(Exception):
    pass

class ConfigParser:
    @staticmethod
    def load(path: str | Path) -> AppConfig:
        _LOGGER.debug(f"Loading Config from {path}")
        config_path = Path(path)

        if not config_path.exists():
            raise ConfigParserError(f"Config file does not exist: {config_path}")

        with config_path.open("r", encoding="utf-8") as file_handle:
            raw = yaml.safe_load(file_handle) or {}

        gwn_section = raw.get("gwn", {})

        if not isinstance(gwn_section, dict):
            raise ConfigParserError("Invalid Config File: No GWN section found in config")
        _LOGGER.debug("Parsing GWN Manager Config")
        secret_key = gwn_section.get("secret_key")
        if not secret_key:
            raise ConfigParserError("gwn.secret_key is missing")
        app_id = gwn_section.get("app_id")
        if not secret_key:
            raise ConfigParserError("gwn.app_id is missing")
        gwnConfig = GwnAuthConfig(app_id=str(app_id),secret_key=str(secret_key))
        gwn_url = gwn_section.get("url")
        if gwn_url:
            gwnConfig.base_url = str(gwn_url)
        _LOGGER.debug(f"GWN Config|URL: '{gwnConfig.base_url}'")

        mqttConfig = MqttConfig()
        mqtt_section = raw.get("mqtt")
        if not isinstance(mqtt_section, dict):
            _LOGGER.debug("No MQTT section found in config")
        else:
            _LOGGER.debug("Parsing MQTT Config")
            host = mqtt_section.get("host")
            if host:
                mqttConfig.host = host
            port = mqtt_section.get("port")
            if port:
                mqttConfig.port = port
            username = mqtt_section.get("username")
            if username:
                mqttConfig.username = username
            password = mqtt_section.get("password")
            if password:
                mqttConfig.password = password
            client_id = mqtt_section.get("client_id")
            if client_id:
                mqttConfig.client_id = client_id
            keepalive = mqtt_section.get("keepalive")
            if keepalive:
                mqttConfig.keepalive = keepalive
            topic = mqtt_section.get("topic")
            if topic:
                mqttConfig.topic = topic
            tls = mqtt_section.get("tls")
            if tls:
                mqttConfig.tls = bool(tls)
            verify_tls = mqtt_section.get("verify_tls")
            if verify_tls:
                mqttConfig.verify_tls = bool(verify_tls)
        _LOGGER.debug(f"MQTT Config|Host: '{mqttConfig.host}'|Port: '{mqttConfig.port}'|Keepalive: '{mqttConfig.keepalive}'|Topic: '{mqttConfig.topic}'|TLS: '{mqttConfig.tls}'|Verify TLS: '{mqttConfig.verify_tls}'")
        
        logging_section = raw.get("logging", {})
        logConfig = LoggingConfig()
        if not isinstance(logging_section, dict):
            _LOGGER.debug("No Logging section found in config")
        else:
            _LOGGER.debug("Parsing Logging Config")
            log_level = logging_section.get("level")
            if log_level:
                log_level = str(log_level)
                if log_level not in {"FATAL", "ERROR", "WARNING", "INFO", "DEBUG", "NONE"}:
                    raise ConfigParserError( "logging.location must be one of: FATAL, ERROR, WARNING, INFO, DEBUG, NONE")
                logConfig.level = log_level
            logging_location = logging_section.get("location")
            if logging_location:
                logging_location = str(logging_location)
                if logging_location not in {"syslog", "file", "console"}:
                    raise ConfigParserError( "logging.location must be one of: syslog, file, console")
                logConfig.location = cast(LogLocation, logging_location)
            if logConfig.location == "file":
                output_path = logging_section.get("output_path")
                if not output_path:
                    raise ConfigParserError("logging.output_path is required when logging.location is 'file'")
                logConfig.output_path = Path(output_path).resolve()
            size = logging_section.get("size")
            if size:
                size = int(size)
                if size < 0:
                    raise ConfigParserError("logging.size must be >= 0")
                logConfig.size = size

            files = logging_section.get("files")
            if files:
                files = int(files)
                if files < 1:
                    raise ConfigParserError("logging.files must be >= 1")
                logConfig.files = files

        _LOGGER.debug(f"Logging Config|Level: '{logConfig.level}'|Location: '{logConfig.location}'|Path: '{logConfig.output_path}")

        _LOGGER.info("Successfully loaded the config")
        return AppConfig(mqttConfig, logConfig, gwnConfig)
