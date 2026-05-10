from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GwnDataUpdateCoordinator
from .sensor import _networks
from gwn.constants import Constants

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    networks: list[dict[str, Any]] = _networks(coordinator)
    entities: list[SelectEntity] = []
    for network in networks:
        for device in network.get(Constants.DEVICES, []):
            entities.append(GwnDeviceSelect(coordinator, device, Constants.AP_2G4_CHANNEL, Constants.CHANNEL_LISTS_2G4, "2.4Ghz Channel"))
            entities.append(GwnDeviceSelect(coordinator, device, Constants.AP_5G_CHANNEL, Constants.CHANNEL_LISTS_5G, "5Ghz Channel"))
            entities.append(GwnDeviceSelect(coordinator, device, Constants.AP_6G_CHANNEL, Constants.CHANNEL_LISTS_6G, "6Ghz Channel"))

    async_add_entities(entities)

class GwnDeviceSelect(CoordinatorEntity[GwnDataUpdateCoordinator], SelectEntity):
    def __init__(self, coordinator, device: dict[str, Any], key: str, options_key: str, name_suffix: str) -> None:
        super().__init__(coordinator)
        self._device: dict[str, Any] = device
        self._key: str = key
        self._options_key: str = options_key

        self._device_mac: str = device[Constants.MAC]
        self._name: str = device[Constants.AP_NAME]
        self._attr_name: str = f"{self._name} {name_suffix}"
        self._attr_unique_id: str = f"{self._device_mac}_{key}"

    @property
    def _option_map(self) -> dict[int, str]:
        raw_options = self._device.get(self._options_key, {})
        return raw_options if isinstance(raw_options, dict) else {}

    @property
    def options(self) -> list[str]:
        return list(self._option_map.values())

    @property
    def current_option(self) -> str | None:
        current_value = self._device.get(self._key)
        if current_value is None:
            return None
        return self._option_map.get(int(current_value))

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"device_{self._device_mac}")},
            "name": self._name,
            "manufacturer": "Grandstream",
            "model": self._device.get(Constants.AP_TYPE),
            "sw_version": self._device.get(Constants.CURRENT_FIRMWARE),
        }

    async def async_select_option(self, option: str) -> None:
        for value, label in self._option_map.items():
            if label == option:
                await self.coordinator.async_set_device_value(self._device_mac, int(self._device[Constants.NETWORK_ID]), self._key, value)
                return
