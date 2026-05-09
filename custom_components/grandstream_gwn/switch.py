from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([GwnEnabledSwitch(coordinator, device) for device in coordinator.data["devices"]])

class GwnEnabledSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator, device: dict) -> None:
        super().__init__(coordinator)
        self._device_id = device["id"]
        self._attr_name = f'{device["name"]} Enabled'
        self._attr_unique_id = f'{device["id"]}_enabled'

    @property
    def _device(self) -> dict:
        for device in self.coordinator.data["devices"]:
            if device["id"] == self._device_id:
                return device
        return {}

    @property
    def is_on(self) -> bool:
        return bool(self._device.get("enabled", False))

    async def async_turn_on(self, **kwargs) -> None:
        self._device["enabled"] = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self._device["enabled"] = False
        self.async_write_ha_state()

    @property
    def device_info(self):
        return {"identifiers": {("grandstream_gwn", self._device_id)} }