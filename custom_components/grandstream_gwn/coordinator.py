import logging

from datetime import timedelta

from gwn.constants import Constants
from gwn.authentication import GwnConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(Constants.LOG)

class GwnDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name="Grandstream GWN",
            update_interval=timedelta(seconds=30),
        )
        self._entry = entry
        self._gwn_config = _build_gwn_config(self._entry)

def _parse_int_list(value: str | None) -> list[int]:
    if value is None or value.strip() == "":
        return []
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def _parse_str_list(value: str | None) -> list[str]:
    if value is None or value.strip() == "":
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _build_gwn_config(entry: ConfigEntry) -> GwnConfig:
    data = entry.data

    return GwnConfig(
        app_id=str(data["app_id"]),
        secret_key=str(data["secret_key"]),
        restricted_api=bool(data.get("restricted_api", False)),
        username=data.get("username"),
        password=data.get("password") if data.get("password") else data.get("hashed_password"),
        base_url=str(data.get("url", "https://localhost:8443")),
        page_size=int(data.get("page_size", 10)),
        refresh_period_s=int(data.get("refresh_period_s", 30)),
        exclude_passphrase=_parse_int_list(data.get("exclude_passphrase")),
        exclude_ssid=_parse_int_list(data.get("exclude_ssid")),
        exclude_device=[GwnConfig.normalise_mac(mac) for mac in _parse_str_list(data.get("exclude_device"))],
        exclude_network=_parse_int_list(data.get("exclude_network")),
        ignore_failed_fetch_before_update=bool(data.get("ignore_failed_fetch_before_update", False)),
        ssid_name_to_device_binding=bool(data.get("ssid_name_to_device_binding", True)),
        no_publish=bool(data.get("no_publish", False)),
    )


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
