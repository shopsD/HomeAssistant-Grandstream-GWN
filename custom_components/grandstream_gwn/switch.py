from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .sensor import _networks
from gwn.constants import Constants

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    networks: list[dict[str, Any]] = _networks(coordinator)
    entities: list[SwitchEntity] = []
    for network in networks:
        for ssid in network.get(Constants.SSIDS,[]):
            entities.append(GwnSSIDSwitch(coordinator, ssid, Constants.SSID_ENABLE, "Enabled"))
            entities.append(GwnSSIDSwitch(coordinator, ssid, Constants.PORTAL_ENABLED, "Captive Portal"))
            entities.append(GwnSSIDSwitch(coordinator, ssid, Constants.SSID_ISOLATION, "Client Isolation"))
            entities.append(GwnSSIDSwitch(coordinator, ssid, Constants.GHZ2_4_ENABLED, "2.4GHz Station"))
            entities.append(GwnSSIDSwitch(coordinator, ssid, Constants.GHZ5_ENABLED, "5GHz Station"))
            entities.append(GwnSSIDSwitch(coordinator, ssid, Constants.GHZ6_ENABLED, "6GHz Station"))
            entities.append(GwnSSIDSwitch(coordinator, ssid, Constants.SSID_HIDDEN, "Hide WiFi"))
    async_add_entities(entities)

class GwnSSIDSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator, ssid: dict[str, Any], key: str, name_suffix: str) -> None:
        super().__init__(coordinator)
        self._ssid: dict[str, Any] = ssid
        self._key: str = key
        self._ssid_id: str = self._ssid[Constants.SSID_ID]
        self._name: str = self._ssid[Constants.SSID_NAME]
        self._attr_name: str = f"{self._name} {name_suffix}"
        self._attr_unique_id: str = f"{self._ssid_id}_{key}"

    @property
    def is_on(self) -> bool:
        return bool(self._ssid.get(self._key) == 1)

    async def async_turn_on(self, **kwargs) -> None:
        self._ssid[self._key] = 1
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self._ssid[self._key] = 0
        self.async_write_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"ssid_{self._ssid_id}")},
            "name": self._name,
            "manufacturer": "Grandstream",
            "model": self._ssid.get(Constants.NETWORK_NAME, "GWN SSID"),
        }
