from typing import Any

from homeassistant.components.text import TextEntity
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
    entities: list[TextEntity] = []
    for network in networks:
        entities.append(GwnNetworkText(coordinator, network, Constants.NETWORK_NAME, "Name"))

        for ssid in network.get(Constants.SSIDS, []):
            entities.append(GwnSSIDText(coordinator, ssid, Constants.SSID_NAME, "SSID"))
            entities.append(GwnSSIDText(coordinator, ssid, Constants.SSID_KEY, "WiFi Passphrase"))

        for device in network.get(Constants.DEVICES, []):
            entities.append(GwnDeviceText(coordinator, device, Constants.AP_NAME, "Name"))

    async_add_entities(entities)

class GwnNetworkText(CoordinatorEntity, TextEntity):
    def __init__(self, coordinator, network: dict[str, Any], key: str, name_suffix: str) -> None:
        super().__init__(coordinator)
        self._network: dict[str, Any] = network
        self._key: str = key
        self._network_id: str = self._network[Constants.NETWORK_ID]
        self._name: str = self._network[Constants.NETWORK_NAME]
        self._attr_name: str = f"{self._name} {name_suffix}"
        self._attr_unique_id: str = f"{self._network_id}_{key}"

    @property
    def native_value(self) -> str:
        value = self._network.get(self._key)
        return "" if value is None else str(value)

    async def async_set_value(self, value: str) -> None:
        self._network[self._key] = value
        self.async_write_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"network_{self._network_id}")},
            "name": self._name,
            "manufacturer": "Grandstream",
            "model": "GWN Network",
            "sw_version": self._network.get(Constants.CURRENT_FIRMWARE),
        }

class GwnDeviceText(CoordinatorEntity, TextEntity):
    def __init__(self, coordinator, device: dict[str, Any], key: str, name_suffix: str) -> None:
        super().__init__(coordinator)
        self._device: dict[str, Any] = device
        self._key: str = key
        self._device_mac: str = device[Constants.MAC]
        self._name: str = device[Constants.AP_NAME]
        self._attr_name: str = f"{self._name} {name_suffix}"
        self._attr_unique_id: str = f"{self._device_mac}_{key}"

    @property
    def native_value(self) -> str:
        value = self._device.get(self._key)
        return "" if value is None else str(value)

    async def async_set_value(self, value: str) -> None:
        self._device[self._key] = value
        self.async_write_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"device_{self._device_mac}")},
            "name": self._name,
            "manufacturer": "Grandstream",
            "model": self._device.get(Constants.AP_TYPE),
            "sw_version": self._device.get(Constants.CURRENT_FIRMWARE),
        }

class GwnSSIDText(CoordinatorEntity, TextEntity):
    def __init__(self, coordinator, ssid: dict[str, Any], key: str, name_suffix: str) -> None:
        super().__init__(coordinator)
        self._ssid: dict[str, Any] = ssid
        self._key: str = key
        self._ssid_id: str = self._ssid[Constants.SSID_ID]
        self._name: str = self._ssid[Constants.SSID_NAME]
        self._attr_name: str = f"{self._name} {name_suffix}"
        self._attr_unique_id: str = f"{self._ssid_id}_{key}"

    @property
    def native_value(self) -> str:
        value = self._ssid.get(self._key)
        return "" if value is None else str(value)

    async def async_set_value(self, value: str) -> None:
        self._ssid[self._key] = value
        self.async_write_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"ssid_{self._ssid_id}")},
            "name": self._name,
            "manufacturer": "Grandstream",
            "model": self._ssid.get(Constants.NETWORK_NAME, "GWN SSID"),
        }
