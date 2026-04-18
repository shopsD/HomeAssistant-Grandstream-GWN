from pathlib import Path
from typing import cast

import logging
import yaml

from gwn.authentication import GwnConfig
from gwn.constants import Constants
from mqtt.config.AppConfig import AppConfig
from mqtt.config.MqttConfig import MqttConfig
from mqtt.config.LoggingConfig import LogLocation, LoggingConfig

_LOGGER = logging.getLogger(Constants.LOG)

class ConfigParserError(Exception):
    pass

class ConfigParser:

    @staticmethod
    def _load_gwn(raw) -> GwnConfig:
        gwn_section = raw.get("gwn", {})
        # load the required first
        if not isinstance(gwn_section, dict):
            raise ConfigParserError("Invalid Config File: No GWN section found in config")
        _LOGGER.debug("Parsing GWN Manager Config")
        # gwn secret_key
        secret_key = gwn_section.get("secret_key")
        if not secret_key:
            raise ConfigParserError("gwn.secret_key is missing")
        # gwn app id
        app_id = gwn_section.get("app_id")
        if not app_id:
            raise ConfigParserError("gwn.app_id is missing")
        
        # now load the optional config parameters
        gwn_config = GwnConfig(app_id=str(app_id),secret_key=str(secret_key))
        # gwn url
        gwn_url = gwn_section.get("url")
        if gwn_url:
            gwn_config.base_url = str(gwn_url)
        # gwn page size
        gwn_page_size = gwn_section.get("page_size")
        if gwn_page_size:
            gwn_page_size = int(gwn_page_size)
            if gwn_page_size < 0:
                raise ConfigParserError("gwn.page_size must be >= 1")
            gwn_config.page_size = gwn_page_size
        # gwn max pages
        gwn_max_pages = gwn_section.get("max_pages")
        if gwn_max_pages:
            gwn_max_pages = int(gwn_max_pages)
            if gwn_max_pages < 0:
                raise ConfigParserError("gwn.max_pages must be >= 0")
            gwn_config.max_pages = gwn_max_pages
        # gwn refresh period
        gwn_refresh_period_s = gwn_section.get("refresh_period_s")
        if gwn_refresh_period_s:
            gwn_refresh_period_s = int(gwn_refresh_period_s)
            if gwn_refresh_period_s < 0:
                raise ConfigParserError("gwn.refresh_period_s must be >= 0")
            gwn_config.refresh_period_s = gwn_refresh_period_s
        _LOGGER.debug(f"GWN Config|URL: '{gwn_config.base_url}'|Page Size: '{gwn_config.page_size}'|Max Pages: '{gwn_config.max_pages}'|Refresh Period: '{gwn_config.refresh_period_s}'")

        return gwn_config

    @staticmethod
    def _load_mqtt(raw) -> MqttConfig:
        mqtt_config = MqttConfig()
        mqtt_section = raw.get("mqtt")
        if not isinstance(mqtt_section, dict):
            _LOGGER.debug("No MQTT section found in config")
        else:
            _LOGGER.debug("Parsing MQTT Config")
            # mqtt host
            host = mqtt_section.get("host")
            if host:
                mqtt_config.host = host
            # mqtt port
            port = mqtt_section.get("port")
            if port:
                mqtt_config.port = port
            # mqtt username
            username = mqtt_section.get("username")
            if username:
                mqtt_config.username = username
            # mqtt password
            password = mqtt_section.get("password")
            if password:
                mqtt_config.password = password
            # mqtt client id
            client_id = mqtt_section.get("client_id")
            if client_id:
                mqtt_config.client_id = client_id
            # mqtt keep alive
            keepalive = mqtt_section.get("keepalive")
            if keepalive:
                mqtt_config.keepalive = keepalive
            # mqtt topic
            topic = mqtt_section.get("topic")
            if topic:
                mqtt_config.topic = topic
            # mqtt tls
            tls = mqtt_section.get("tls")
            if tls:
                mqtt_config.tls = bool(tls)
            # mqtt verify tls
            verify_tls = mqtt_section.get("verify_tls")
            if verify_tls:
                mqtt_config.verify_tls = bool(verify_tls)
        _LOGGER.debug(f"MQTT Config|Host: '{mqtt_config.host}'|Port: '{mqtt_config.port}'|Keepalive: '{mqtt_config.keepalive}'|Topic: '{mqtt_config.topic}'|TLS: '{mqtt_config.tls}'|Verify TLS: '{mqtt_config.verify_tls}'")
        return mqtt_config

    @staticmethod
    def _load_logging(raw) -> LoggingConfig:
        logging_section = raw.get("logging", {})
        log_config = LoggingConfig()
        if not isinstance(logging_section, dict):
            _LOGGER.debug("No Logging section found in config")
        else:
            _LOGGER.debug("Parsing Logging Config")

            # logging level
            log_level = logging_section.get("level")
            if log_level:
                log_level = str(log_level)
                if log_level not in {"FATAL", "ERROR", "WARNING", "INFO", "DEBUG", "NONE"}:
                    raise ConfigParserError( "logging.location must be one of: FATAL, ERROR, WARNING, INFO, DEBUG, NONE")
                log_config.level = log_level
            # logging location
            logging_location = logging_section.get("location")
            if logging_location:
                logging_location = str(logging_location)
                if logging_location not in {"syslog", "file", "console"}:
                    raise ConfigParserError( "logging.location must be one of: syslog, file, console")
                log_config.location = cast(LogLocation, logging_location)
            if log_config.location == "file":
                output_path = logging_section.get("output_path")
                if not output_path:
                    raise ConfigParserError("logging.output_path is required when logging.location is 'file'")
                log_config.output_path = Path(output_path).resolve()
            # logging size
            size = logging_section.get("size")
            if size:
                size = int(size)
                if size < 0:
                    raise ConfigParserError("logging.size must be >= 0")
                log_config.size = size
            # logging files
            files = logging_section.get("files")
            if files:
                files = int(files)
                if files < 1:
                    raise ConfigParserError("logging.files must be >= 1")
                log_config.files = files
        _LOGGER.debug(f"Logging Config|Level: '{log_config.level}'|Location: '{log_config.location}'|Path: '{log_config.output_path}")
        return log_config

    @staticmethod
    def load(path: str | Path) -> AppConfig:
        _LOGGER.debug(f"Loading Config from {path}")
        config_path = Path(path)

        if not config_path.exists():
            raise ConfigParserError(f"Config file does not exist: {config_path}")

        with config_path.open("r", encoding="utf-8") as file_handle:
            raw = yaml.safe_load(file_handle) or {}

        gwn_config = ConfigParser._load_gwn(raw) # required section

        mqtt_config = ConfigParser._load_mqtt(raw) # optional section
        log_config = ConfigParser._load_logging(raw) # optional section
        
        _LOGGER.info("Successfully loaded the config")
        return AppConfig(mqtt_config, log_config, gwn_config)
