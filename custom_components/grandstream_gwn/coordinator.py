import logging

from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from gwn.constants import Constants

_LOGGER = logging.getLogger(Constants.LOG)

class GwnDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name="Grandstream GWN",
            update_interval=timedelta(seconds=30),
        )
        self.entry = entry

    async def _async_update_data(self):
        return {
            {
                "data": {
                    "result": [
                        {
                            "status": 1,
                            "apType": "GWN7600",
                            "mac": "00:0B:82:AA:AA:AA",
                            "name": "",
                            "ip": "192.168.126.146",
                            "upTime": 1021744,
                            "usage": 6695047434,
                            "upload": 343241087,
                            "download": 6351806347,
                            "channel": 6,
                            "channel5g": 48,
                            "clients": 0,
                            "lastFwVersion": "1.0.13.3",
                            "versionFirmware": "1.0.13.3",
                            "networkId": 9581
                        }
                    ]
                }
            }
        }
