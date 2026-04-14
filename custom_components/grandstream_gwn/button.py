from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([GwnRebootButton(coordinator, device) for device in coordinator.data["devices"]])


class GwnRebootButton(CoordinatorEntity, ButtonEntity):
    def __init__(self, coordinator, device: dict) -> None:
        super().__init__(coordinator)
        self._device_id = device["id"]
        self._attr_name = f'{device["name"]} Reboot'
        self._attr_unique_id = f'{device["id"]}_reboot'

    async def async_press(self) -> None:
        return

    @property
    def device_info(self):
        return {"identifiers": {("grandstream_gwn", self._device_id)}}
