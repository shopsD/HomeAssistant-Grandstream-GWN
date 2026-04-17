import argparse
import asyncio
import logging
from pathlib import Path

from aiohttp import ClientSession 

from gwn.api import GwnClient
from mqtt.app import MqttGwnManager
from mqtt.connection import ConnectionManager
from mqtt.config import ConfigParser
from mqtt.config import LoggingConfig


_LOGGER = logging.getLogger(__name__)

def init_logger(config: LoggingConfig):
    _LOGGER.info("Initialising Logging")
    _LOGGER.basicConfig(level=config.level)
    _LOGGER.info("Logging Initialised")

async def async_main(config_path: Path) -> None:
    app_config = ConfigParser.load(config_path)
    init_logger(app_config.logging)
    manager = ConnectionManager(app_config.mqtt)
    gwnClient = GwnClient(ClientSession(),app_config.gwn)
    app_manager = MqttGwnManager(manager,gwnClient)
    app_manager.connect()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Grandstream GWN Manager to MQTT")
    parser.add_argument(
        "-c"
        ,"--config_path"
        ,type=Path
        ,default=Path(__file__).resolve().parent / "data" / "config.yml"
        ,help="Path to config YAML file. Defaults to ./data/config.yml relative to mqtt/main.py"
    )
    logging.info("Starting GWN Manager")
    args = parser.parse_args()

    asyncio.run(async_main(args.config_path))
