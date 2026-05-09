from typing import Any

from homeassistant.components.button import ButtonEntity
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
    entities: list[ButtonEntity] = []
    for network in networks:
        for device in network.get(Constants.DEVICES,[]):
            entities.append(GwnDeviceButton(coordinator, device, Constants.REBOOT, "Reboot"))
            entities.append(GwnDeviceButton(coordinator, device, Constants.RESET, "Reset"))
            entities.append(GwnDeviceButton(coordinator, device, Constants.UPDATE_FIRMWARE, "Update Firmware"))
    async_add_entities(entities)

class GwnDeviceButton(CoordinatorEntity, ButtonEntity):
    def __init__(self, coordinator, device: dict[str, Any], key: str, name_suffix: str) -> None:
        super().__init__(coordinator)
        self._device: dict[str, Any] = device
        self._key: str = key
        self._device_mac: str = device[Constants.MAC]
        self._name: str = device[Constants.AP_NAME]
        self._attr_name: str = f"{self._name} {name_suffix}"
        self._attr_unique_id: str = f"{self._device_mac}_{key}"

    async def async_press(self) -> None:
        return

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"device_{self._device_mac}")},
            "name": self._name,
            "manufacturer": "Grandstream",
            "model": self._device.get(Constants.AP_TYPE)
        }
