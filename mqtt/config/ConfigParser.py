import logging
import platform
import yaml
from pathlib import Path
from typing import cast

from gwn.authentication import GwnConfig
from gwn.constants import Constants
from mqtt.config.AppConfig import AppConfig
from mqtt.config.CoreConfig import CoreConfig
from mqtt.config.MqttConfig import MqttConfig
from mqtt.config.LoggingConfig import LogLocation, LoggingConfig

_LOGGER = logging.getLogger(Constants.LOG)

class ConfigParserError(Exception):
    pass

class ConfigParser:
        
    @staticmethod
    def _load_autodiscovery_modes(value: object, field_name: str, default_mode: bool, key_as_int: bool = True) -> dict[int|str, bool]:
        if value is None:
            return {}

        if not isinstance(value, list):
            raise ConfigParserError(f"mqtt.{field_name} must be a list")

        parsed: dict[int | str, bool] = {}

        for item in value:
            if isinstance(item, int):
                parsed[item] = default_mode
            elif isinstance(item, dict):
                if len(item) != 1:
                    raise ConfigParserError(f"Each mqtt.homeassistant.{field_name} child must contain exactly one key/value pair")
                raw_key, raw_mode = next(iter(item.items()))
                key = int(raw_key) if key_as_int else str(raw_key)
                parsed[key] = bool(raw_mode)
            else:
                raise ConfigParserError(f"Each mqtt.homeassistant.{field_name} child must be either an integer or a single key/value pair")

        return parsed

    @staticmethod
    def _load_name_override_module(value: object, field_name: str, key_as_int: bool = True) -> dict[int|str, str]:
        if value is None:
            return {}

        if not isinstance(value, list):
            raise ConfigParserError(f"mqtt.{field_name} must be a list")

        parsed: dict[int | str, str] = {}

        for item in value:
            if not isinstance(item, dict):
                raise ConfigParserError(f"Each mqtt.homeassistant.{field_name} child must be a key/value pair")
            if len(item) != 1:
                raise ConfigParserError(f"Each mqtt.homeassistant.{field_name} child must contain exactly one key/value pair")
            raw_key, raw_mode = next(iter(item.items()))
            key = int(raw_key) if key_as_int else str(raw_key)
            parsed[key] = str(raw_mode)

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
        # gwn username
        gwn_username = gwn_section.get("username")
        if gwn_username:
            gwn_config.username = str(gwn_username)
        # gwn password/hashed_password
        gwn_password = gwn_section.get("password")
        gwn_hashed_password = gwn_section.get("hashed_password")
        if gwn_password is not None and gwn_hashed_password is not None:
            raise ConfigParserError("gwn.password and gwn.hashed_password cannot be both provided")
        if gwn_password:
            gwn_config.password = GwnConfig.hash_password(gwn_password)
        elif gwn_hashed_password:
            gwn_config.password = str(gwn_hashed_password)
        if gwn_config.username and not gwn_config.password:
            raise ConfigParserError("gwn.username specified but gwn.password/gwn.hashed_password is missing")
        if gwn_config.password and not gwn_config.username:
            error_str: str = f"gwn.{"hashed_" if gwn_password is None else ""}password specified but gwn.username is missing"
            raise ConfigParserError(error_str)
        # gwn restricted API
        restricted_api = gwn_section.get("restricted_api")
        if restricted_api is not None:
            gwn_config.restricted_api = bool(restricted_api)
            if (gwn_config.username is None or gwn_config.password is None) and gwn_config.restricted_api:
                raise ConfigParserError("gwn.restricted_api is True but gwn.username and gwn.password/gwn.hashed_password are missing")
        # gwn ignore failed fetch before update
        ignore_failed_fetch_before_update = gwn_section.get("ignore_failed_fetch_before_update")
        if ignore_failed_fetch_before_update is not None:
            gwn_config.ignore_failed_fetch_before_update = bool(ignore_failed_fetch_before_update)
        # gwn ssid name to device binding
        ssid_name_to_device_binding = gwn_section.get("ssid_name_to_device_binding")
        if ssid_name_to_device_binding is not None:
            gwn_config.ssid_name_to_device_binding = bool(ssid_name_to_device_binding)
        # gwn no publish
        no_publish = gwn_section.get("no_publish")
        if no_publish is not None:
            gwn_config.no_publish = bool(no_publish)
        _LOGGER.debug(f"GWN Config|User/Password Provided: '{bool(gwn_config.username and gwn_config.password)}'|Using Restricted API: '{gwn_config.restricted_api}'|No Publish: '{gwn_config.no_publish}'|URL: '{gwn_config.base_url}'|Page Size: '{gwn_config.page_size}'|Max Pages: '{gwn_config.max_pages}'|Refresh Period: '{gwn_config.refresh_period_s}'|No. of Excluded Networks: '{len(gwn_config.exclude_network)}'|No. of Excluded Devices: '{len(gwn_config.exclude_device)}'|No. of excluded SSIDs: '{len(gwn_config.exclude_ssid)}'|No. of SSIDs with Excluded WEP/WPA Passphrase: '{len(gwn_config.exclude_passphrase)}'")

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
            # mqtt topic manifest path
            topic_manifest_path = mqtt_section.get("topic_manifest_path")
            if topic_manifest_path is not None:
                mqtt_config.topic_manifest_path = str(topic_manifest_path)
            # mqtt verify tls
            no_publish = mqtt_section.get("no_publish")
            if no_publish is not None:
                mqtt_config.no_publish = bool(no_publish)
            homeassistant_sub_section = mqtt_section.get("homeassistant")
            if homeassistant_sub_section is not None:
                if not isinstance(homeassistant_sub_section, dict):
                    raise ConfigParserError("mqtt.homeassistant is invalid")
                # mqtt default application discovery topic
                discovery_topic = homeassistant_sub_section.get("discovery_topic")
                if discovery_topic is not None:
                    mqtt_config.homeassistant.discovery_topic = str(discovery_topic)
                # mqtt default application autodiscovery
                always_publish_autodiscovery = homeassistant_sub_section.get("always_publish_autodiscovery")
                if always_publish_autodiscovery is not None:
                    mqtt_config.homeassistant.always_publish_autodiscovery = bool(always_publish_autodiscovery)
                # mqtt default application autodiscovery
                application_autodiscovery = homeassistant_sub_section.get("application_autodiscovery")
                if application_autodiscovery is not None:
                    mqtt_config.homeassistant.application_autodiscovery = bool(application_autodiscovery)
                # mqtt default network autodiscovery. Must be evaluated before network_autodiscovery
                default_network = homeassistant_sub_section.get("default_network_autodiscovery")
                if default_network is not None:
                    mqtt_config.homeassistant.default_network_autodiscovery = bool(default_network)
                # mqtt default device autodiscovery. Must be evaluated before device_autodiscovery
                default_device = homeassistant_sub_section.get("default_device_autodiscovery")
                if default_device is not None:
                    mqtt_config.homeassistant.default_device_autodiscovery = bool(default_device)
                # mqtt default ssid autodiscovery. Must be evaluated before ssid_autodiscovery
                default_ssid = homeassistant_sub_section.get("default_ssid_autodiscovery")
                if default_ssid is not None:
                    mqtt_config.homeassistant.default_ssid_autodiscovery = bool(default_ssid)
                # mqtt network autodiscovery
                network_autodiscovery = homeassistant_sub_section.get("network_autodiscovery")
                if network_autodiscovery is not None:
                    mqtt_config.homeassistant.network_autodiscovery = ConfigParser._load_autodiscovery_modes(homeassistant_sub_section.get("network_autodiscovery"),"network_autodiscovery", mqtt_config.homeassistant.default_network_autodiscovery)
                # mqtt device autodiscovery
                device_autodiscovery = homeassistant_sub_section.get("device_autodiscovery")
                if device_autodiscovery is not None:
                    mqtt_config.homeassistant.device_autodiscovery = ConfigParser._load_autodiscovery_modes(homeassistant_sub_section.get("device_autodiscovery"),"device_autodiscovery", mqtt_config.homeassistant.default_device_autodiscovery, False)
                # mqtt ssid autodiscovery
                ssid_autodiscovery = homeassistant_sub_section.get("ssid_autodiscovery")
                if ssid_autodiscovery is not None:
                    mqtt_config.homeassistant.ssid_autodiscovery = ConfigParser._load_autodiscovery_modes(homeassistant_sub_section.get("ssid_autodiscovery"),"ssid_autodiscovery", mqtt_config.homeassistant.default_ssid_autodiscovery)
                # mqtt network autodiscovery
                network_name_override = homeassistant_sub_section.get("network_name_override")
                if network_name_override is not None:
                    mqtt_config.homeassistant.network_name_override = ConfigParser._load_name_override_module(homeassistant_sub_section.get("network_name_override"),"network_name_override")
                # mqtt device autodiscovery
                device_name_override = homeassistant_sub_section.get("device_name_override")
                if device_name_override is not None:
                    mqtt_config.homeassistant.device_name_override = ConfigParser._load_name_override_module(homeassistant_sub_section.get("device_name_override"),"device_name_override", False)
                # mqtt ssid autodiscovery
                ssid_name_override = homeassistant_sub_section.get("ssid_name_override")
                if ssid_name_override is not None:
                    mqtt_config.homeassistant.ssid_name_override = ConfigParser._load_name_override_module(homeassistant_sub_section.get("ssid_name_override"),"ssid_name_override")

                _LOGGER.debug(f"MQTT.HomeAssistant Config|Discovery Topic '{mqtt_config.homeassistant.discovery_topic}'|Always Publish Autodiscovery '{mqtt_config.homeassistant.always_publish_autodiscovery}'|Application Auto-discovery '{mqtt_config.homeassistant.application_autodiscovery}'|Default Network Auto-discovery: '{mqtt_config.homeassistant.default_network_autodiscovery}'|Default Device Auto-discovery: '{mqtt_config.homeassistant.default_device_autodiscovery}'|Default SSID Auto-discovery: '{mqtt_config.homeassistant.default_ssid_autodiscovery}'|No. of Custom Network Auto-discoveries: '{len(mqtt_config.homeassistant.network_autodiscovery)}'|No. of Custom Device Auto-discoveries: '{len(mqtt_config.homeassistant.device_autodiscovery)}'|No. of Custom SSID Auto-discoveries: '{len(mqtt_config.homeassistant.ssid_autodiscovery)}'|No. of Network Name Overrides: '{len(mqtt_config.homeassistant.network_name_override)}'|No. of Device Name Overrides: '{len(mqtt_config.homeassistant.device_name_override)}'|No. of SSID Name Overrides: '{len(mqtt_config.homeassistant.ssid_name_override)}'")

        _LOGGER.debug(f"MQTT Config|No Publish: '{mqtt_config.no_publish}'|Host: '{mqtt_config.host}'|Port: '{mqtt_config.port}'|Keepalive: '{mqtt_config.keepalive}'|Topic: '{mqtt_config.topic}'|TLS: '{mqtt_config.tls}'|Verify TLS: '{mqtt_config.verify_tls}'|Topic Manifest Path: '{mqtt_config.topic_manifest_path}'")
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
                if logging_location not in {"system", "file", "console"}:
                    raise ConfigParserError( "logging.location must be one of: system, file, console")
                log_config.location = cast(LogLocation, logging_location)
            if log_config.location == "system":
                if platform.system() != "Windows" and not Path("/dev/log").exists():
                    raise ConfigParserError("logging.location is 'system' but /dev/log does not exist")
            elif log_config.location == "file":
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
        _LOGGER.debug(f"Logging Config|Level: '{log_config.level}'|Location: '{log_config.location}'|Path: '{log_config.output_path}'")
        return log_config

    @staticmethod
    def _load_app(raw) -> AppConfig:
        app_section = raw.get("app", {})
        app_config = AppConfig()
        if not isinstance(app_section, dict):
            _LOGGER.debug("No App section found in config")
        else:
            _LOGGER.debug("Parsing App Config")
            # app verify publish every poll
            publish_every_poll = app_section.get("publish_every_poll")
            if publish_every_poll is not None:
                app_config.publish_every_poll = bool(publish_every_poll)
            # app unpublish initial data
            unpublish_initial_data = app_section.get("unpublish_initial_data")
            if unpublish_initial_data is not None:
                app_config.unpublish_initial_data = bool(unpublish_initial_data)
            # app check for updates
            check_for_updates = app_section.get("check_for_updates")
            if check_for_updates is not None:
                app_config.check_for_updates = bool(check_for_updates)
            # app check for pre release updates
            allow_pre_release_update = app_section.get("allow_pre_release_update")
            if allow_pre_release_update is not None:
                app_config.allow_pre_release_update = bool(allow_pre_release_update)
        _LOGGER.debug(f"App Config|Publish on Poll: '{app_config.publish_every_poll}'|Unpublish Initial Data: '{app_config.unpublish_initial_data}'|Check for Updates: '{app_config.check_for_updates}'|Allow Pre-release Updates: '{app_config.allow_pre_release_update}'")
        return app_config

    @staticmethod
    def get_hash(password: str) -> str:
        return GwnConfig.hash_password(password)

    @staticmethod
    def load(path: str | Path) -> CoreConfig:
        _LOGGER.debug(f"Loading Config from {path}")
        config_path = Path(path)

        if not config_path.exists():
            raise ConfigParserError(f"Config file does not exist: {config_path}")

        with config_path.open("r", encoding="utf-8") as file_handle:
            raw = yaml.safe_load(file_handle) or {}

        gwn_config = ConfigParser._load_gwn(raw) # required section

        app_config = ConfigParser._load_app(raw) # optional section
        mqtt_config = ConfigParser._load_mqtt(raw) # optional section
        log_config = ConfigParser._load_logging(raw) # optional section
        
        _LOGGER.info("Successfully loaded the config")
        return CoreConfig(app_config, gwn_config, log_config, mqtt_config)
