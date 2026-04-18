import argparse
import asyncio
import logging

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
    logging.basicConfig(level=config.level, force=True)
    logging.getLogger(Constants.LOG).setLevel(config.level)
    _LOGGER.info("Logging Initialised")

async def async_main(config_path: Path) -> None:
    app_config = ConfigParser.load(config_path)
    init_logger(app_config.logging)
    manager = MqttClient(app_config.mqtt)
    gwnClient = GwnClient(app_config.gwn)
    app_manager = MqttGwnManager(manager,gwnClient)
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
    _LOGGER.info("Starting GWN Manager")
    args = parser.parse_args()

    asyncio.run(async_main(args.config_path))

if __name__ == "__main__":
    main()
