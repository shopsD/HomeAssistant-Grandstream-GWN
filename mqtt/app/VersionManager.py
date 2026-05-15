import asyncio
import logging

from mqtt.config import AppConfig

_LOGGER = logging.getLogger(Constants.LOG)

class VersionManager:
    def __init__(self) -> None:
        self._update_url: str = "https://github.com/shopsD/homeassistant-grandstream-gwn"

    def get_latest_version(self) -> str:
        return "0.0.1"
