from pathlib import Path
from typing import cast

import logging
import yaml

from gwn.authentication import GwnConfig
from gwn.constants import Constants
from mqtt.config.AppConfig import AppConfig
from mqtt.config.MqttConfig import MqttConfig, MqttPayloadFormat
from mqtt.config.LoggingConfig import LogLocation, LoggingConfig

_LOGGER = logging.getLogger(Constants.LOG)

class ConfigParserError(Exception):
    pass

class ConfigParser:

    @staticmethod
    def _get_payload_mode(mode: str, field_name: str) -> MqttPayloadFormat:
        valid_modes = {"generic", "homeassistant", "both"}
        mode = mode.lower()
        if mode not in valid_modes:
            raise ConfigParserError(f"mqtt.{field_name} mode must be one of: generic, homeassistant, both")
        
        return (MqttPayloadFormat.BOTH if mode == "both"
            else MqttPayloadFormat.GENERIC if mode == "generic"
            else MqttPayloadFormat.HOMEASSISTANT
        )
        
    @staticmethod
    def _load_payload_modes(value: object, field_name: str, default_mode: MqttPayloadFormat, key_as_int: bool = True) -> dict[int|str, MqttPayloadFormat]:
        if value is None:
            return {}

        if not isinstance(value, list):
            raise ConfigParserError(f"mqtt.{field_name} must be a list")

        parsed: dict[int | str, MqttPayloadFormat] = {}

        for item in value:
            if isinstance(item, int):
                parsed[item] = default_mode
            elif isinstance(item, dict):
                if len(item) != 1:
                    raise ConfigParserError(f"Each mqtt.{field_name} item must contain exactly one key/value pair")
                raw_key, raw_mode = next(iter(item.items()))
                key = int(raw_key) if key_as_int else str(raw_key)
                parsed[key] = ConfigParser._get_payload_mode(raw_mode, field_name)
            else:
                raise ConfigParserError(f"Each mqtt.{field_name} item must be either an integer or a single key/value pair")

        return parsed

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
        if gwn_page_size is not None:
            gwn_page_size = int(gwn_page_size)
            if gwn_page_size < 1:
                raise ConfigParserError("gwn.page_size must be >= 1")
            gwn_config.page_size = gwn_page_size
        # gwn max pages
        gwn_max_pages = gwn_section.get("max_pages")
        if gwn_max_pages is not None:
            gwn_max_pages = int(gwn_max_pages)
            if gwn_max_pages < 0:
                raise ConfigParserError("gwn.max_pages must be >= 0")
            gwn_config.max_pages = gwn_max_pages
        # gwn refresh period
        gwn_refresh_period_s = gwn_section.get("refresh_period_s")
        if gwn_refresh_period_s is not None:
            gwn_refresh_period_s = int(gwn_refresh_period_s)
            if gwn_refresh_period_s < 0:
                raise ConfigParserError("gwn.refresh_period_s must be >= 0")
            gwn_config.refresh_period_s = gwn_refresh_period_s
        # gwn exclude passphrase
        gwn_exclude_passphrase = gwn_section.get("exclude_passphrase")
        if gwn_exclude_passphrase:
            if not isinstance(gwn_exclude_passphrase, list):
                raise ConfigParserError("gwn.exclude_passphrase must be a list of SSID IDs")
            gwn_config.exclude_passphrase = [int(ssid_id) for ssid_id in gwn_exclude_passphrase]
        # gwn exclude networks
        gwn_exclude_network = gwn_section.get("exclude_network")
        if gwn_exclude_network:
            if not isinstance(gwn_exclude_network, list):
                raise ConfigParserError("gwn.exclude_network must be a list of SSID IDs")
            gwn_config.exclude_network = [int(network_id) for network_id in gwn_exclude_network]
        # gwn exclude devices
        gwn_exclude_device = gwn_section.get("exclude_device")
        if gwn_exclude_device:
            if not isinstance(gwn_exclude_device, list):
                raise ConfigParserError("gwn.exclude_device must be a list of MAC Addresses")
            gwn_config.exclude_device = [GwnConfig.normalise_mac(mac) for mac in gwn_exclude_device]
        # gwn exclude passphrase
        gwn_exclude_ssid = gwn_section.get("exclude_ssid")
        if gwn_exclude_ssid:
            if not isinstance(gwn_exclude_ssid, list):
                raise ConfigParserError("gwn.exclude_ssid must be a list of SSID IDs")
            gwn_config.exclude_ssid = [int(ssid_id) for ssid_id in gwn_exclude_ssid]

        _LOGGER.debug(f"GWN Config|URL: '{gwn_config.base_url}'|Page Size: '{gwn_config.page_size}'|Max Pages: '{gwn_config.max_pages}'|Refresh Period: '{gwn_config.refresh_period_s}'|No. of Excluded Networks: '{len(gwn_config.exclude_network)}'|No. of Excluded Devices: '{len(gwn_config.exclude_device)}'|No. of excluded SSIDs: '{len(gwn_config.exclude_ssid)}'|No. of SSIDs with Excluded WEP/WPA Passphrase: '{len(gwn_config.exclude_passphrase)}'")

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
            if tls is not None:
                mqtt_config.tls = bool(tls)
            # mqtt verify tls
            verify_tls = mqtt_section.get("verify_tls")
            if verify_tls is not None:
                mqtt_config.verify_tls = bool(verify_tls)
            # mqtt default network payload. Must be evaluated before network_payload
            default_network_payload = mqtt_section.get("default_network_payload")
            if default_network_payload:
                mqtt_config.default_network_payload = ConfigParser._get_payload_mode(default_network_payload,"default_network_payload")
            # mqtt default device payload. Must be evaluated before device_payload
            default_device_payload = mqtt_section.get("default_device_payload")
            if default_device_payload:
                mqtt_config.default_device_payload = ConfigParser._get_payload_mode(default_device_payload,"default_device_payload")
            # mqtt default ssid payload. Must be evaluated before ssid_payload
            default_ssid_payload = mqtt_section.get("default_ssid_payload")
            if default_ssid_payload:
                mqtt_config.default_ssid_payload = ConfigParser._get_payload_mode(default_ssid_payload,"default_ssid_payload")
            # mqtt network payload
            network_payload = mqtt_section.get("network_payload")
            if network_payload is not None:
                mqtt_config.network_payload = ConfigParser._load_payload_modes(mqtt_section.get("network_payload"),"network_payload", mqtt_config.default_network_payload)
            # mqtt device payload
            device_payload = mqtt_section.get("device_payload")
            if device_payload is not None:
                mqtt_config.device_payload = ConfigParser._load_payload_modes(mqtt_section.get("device_payload"),"device_payload", mqtt_config.default_device_payload, False)
            # mqtt ssid payload
            ssid_payload = mqtt_section.get("ssid_payload")
            if ssid_payload is not None:
                mqtt_config.ssid_payload = ConfigParser._load_payload_modes(mqtt_section.get("ssid_payload"),"ssid_payload", mqtt_config.default_ssid_payload)
        
        _LOGGER.debug(f"MQTT Config|Host: '{mqtt_config.host}'|Port: '{mqtt_config.port}'|Keepalive: '{mqtt_config.keepalive}'|Topic: '{mqtt_config.topic}'|TLS: '{mqtt_config.tls}'|Verify TLS: '{mqtt_config.verify_tls}'|Default Network Payload: '{mqtt_config.default_network_payload.name}'|Default Device Payload: '{mqtt_config.default_device_payload.name}'|Default SSID Payload: '{mqtt_config.default_ssid_payload.name}'|No. of Custom Network Payloads: '{len(mqtt_config.network_payload)}'|No. of Custom Device Payloads: '{len(mqtt_config.device_payload)}'|No. of SSID Network Payloads: '{len(mqtt_config.ssid_payload)}'")
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
