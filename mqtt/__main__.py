import argparse
import asyncio
import getpass
import logging
import platform
from logging.handlers import RotatingFileHandler, SysLogHandler
from pathlib import Path

from gwn.api import GwnClient
from gwn.constants import Constants
from mqtt.app import MqttGwnManager
from mqtt.config import ConfigParser
from mqtt.config import LoggingConfig
from mqtt.connection import MqttClient

_LOGGER = logging.getLogger(Constants.LOG)

def init_logger(config: LoggingConfig) -> None:
    _LOGGER.info("Initialising Logging")
    handler: logging.Handler
    log_level = logging.CRITICAL + 1 if config.level == "NONE" else getattr(logging, config.level)
    formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(name)s:%(message)s")
    if config.location == "file" and config.output_path is not None:
        config.output_path.resolve().parent.mkdir(parents=True, exist_ok=True)
        if config.size > 0:
            handler = RotatingFileHandler(config.output_path, maxBytes=config.size, backupCount=config.files)
        else:
            handler = logging.FileHandler(config.output_path)
    elif config.location == "system":
        if platform.system() == "Windows":
            from logging.handlers import NTEventLogHandler
            handler = NTEventLogHandler(Constants.LOG)
        else:
            handler = SysLogHandler(address="/dev/log")
    else:
        handler = logging.StreamHandler()

    handler.setLevel(log_level)
    handler.setFormatter(formatter)

    logging.basicConfig(level=log_level, handlers=[handler], force=True)
    logging.getLogger(Constants.LOG).setLevel(log_level)
    _LOGGER.info("Logging Initialised")

async def async_main(config_path: Path) -> None:
    core_config = ConfigParser.load(config_path)
    init_logger(core_config.logging)
    mqtt_client = MqttClient(core_config.mqtt)
    gwn_client = GwnClient(core_config.gwn)
    app_manager = MqttGwnManager(core_config.app, mqtt_client, gwn_client)
    if await app_manager.connect():
        await app_manager.run()

def main() -> None:
    logging.basicConfig(level=logging.DEBUG, force=True)
    logging.getLogger(Constants.LOG).setLevel(logging.DEBUG)
    parser = argparse.ArgumentParser(description="Grandstream GWN Manager to MQTT")
    parser.add_argument(
        "-c"
        ,"--config_path"
        ,type=Path
        ,default=Path(__file__).resolve().parent / "data" / "config.yml"
        ,help="Path to config YAML file. Defaults to ./data/config.yml relative to mqtt/main.py"
    )
    parser.add_argument(
        "-p"
        ,"--password"
        ,type=str
        ,nargs="?"
        ,const=""
        ,help="Your password for logging in to GWN Manager. Supplying this option will hash then display the value to use in the config file gwn.hashed_password field, then exit the application"
    )

    args = parser.parse_args()
    if args.password is not None:
        password: str = ""
        if len(args.password) > 0:
            password = args.password
        else:
            password = getpass.getpass("Gwn Manager Password: ")
            confirm_password = getpass.getpass("Confirm Gwn Manager Password: ")
            if password != confirm_password:
                raise ValueError("Passwords do not match")
        return print(ConfigParser.get_hash(password))

    _LOGGER.info("Starting GWN Manager to MQTT")
    asyncio.run(async_main(args.config_path))
    _LOGGER.info("Stopped GWN Manager to MQTT")

if __name__ == "__main__":
    main()
