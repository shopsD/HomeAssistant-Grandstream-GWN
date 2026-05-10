from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GwnDataUpdateCoordinator
from .sensor import _networks
from gwn.constants import Constants

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: GwnDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    networks: dict[str, dict[str, Any]] = _networks(coordinator)
    entities: list[ButtonEntity] = []
    for network in networks.values():
        for device in network.get(Constants.DEVICES,{}).values():
            entities.append(GwnDeviceButton(coordinator, device, Constants.REBOOT, "Reboot"))
            entities.append(GwnDeviceButton(coordinator, device, Constants.RESET, "Reset"))
            entities.append(GwnDeviceButton(coordinator, device, Constants.UPDATE_FIRMWARE, "Update Firmware"))
    async_add_entities(entities)

class GwnDeviceButton(CoordinatorEntity[GwnDataUpdateCoordinator], ButtonEntity):
    def __init__(self, coordinator: GwnDataUpdateCoordinator, device: dict[str, Any], key: str, name_suffix: str) -> None:
        super().__init__(coordinator)
        self._coordinator: GwnDataUpdateCoordinator = coordinator
        self._key: str = key
        self._device_mac: str = device[Constants.MAC]
        self._name: str = device[Constants.AP_NAME]
        self._attr_name: str = f"{self._name} {name_suffix}"
        self._attr_unique_id: str = f"{self._device_mac}_{key}"
        self._ap_type: str = device[Constants.AP_TYPE]
        self._sw_version: str = device[Constants.CURRENT_FIRMWARE]
        self._network_id: str = device[Constants.NETWORK_ID]

    @property
    def device_info(self) -> DeviceInfo | None:
        return {
            "identifiers": {(DOMAIN, f"device_{self._device_mac}")},
            "name": self._name,
            "manufacturer": "Grandstream",
            "model": self._ap_type,
            "sw_version": self._sw_version
        }

    async def async_press(self) -> None:
        await self._coordinator.async_press_device_action(self._device_mac, self._network_id, self._key)
