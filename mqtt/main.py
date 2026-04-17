import argparse
import asyncio
import logging
from pathlib import Path

from mqtt.connection import ConnectionManager
from mqtt.config import ConfigParser
from mqtt.config import LoggingConfig

def init_logger(config: LoggingConfig):
    logging.basicConfig(level=config.level)

async def async_main(config_path: Path) -> None:
    app_config = ConfigParser.load(config_path)
    init_logger(app_config.logging)
    manager = ConnectionManager(app_config.mqtt)

    try:
        await manager.connect()
        await manager.publish(f"{app_config.mqtt.topic}/status", "online", retain=True)
        await asyncio.Event().wait()
    finally:
        await manager.disconnect()


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
    logging.log(logging.INFO,"Starting GWN Manager")
    args = parser.parse_args()

    asyncio.run(async_main(args.config_path))
