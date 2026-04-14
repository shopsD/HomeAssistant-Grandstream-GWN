from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []
    for device in coordinator.data["devices"]:
        entities.append(GwnClientCountSensor(coordinator, device))
        entities.append(GwnIpSensor(coordinator, device))
        entities.append(GwnFirmwareSensor(coordinator, device))

    async_add_entities(entities)


class GwnBaseSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, device: dict, key: str, name_suffix: str) -> None:
        super().__init__(coordinator)
        self._device_id = device["id"]
        self._key = key
        self._attr_name = f'{device["name"]} {name_suffix}'
        self._attr_unique_id = f'{device["id"]}_{key}'

    @property
    def _device(self) -> dict:
        for device in self.coordinator.data["devices"]:
            if device["id"] == self._device_id:
                return device
        return {}

    @property
    def native_value(self):
        return self._device.get(self._key)

    @property
    def device_info(self):
        device = self._device
        return {
            "identifiers": {("grandstream_gwn", self._device_id)},
            "name": device.get("name"),
            "manufacturer": "Grandstream",
            "model": "GWN Device",
            "sw_version": device.get("firmware"),
        }


class GwnClientCountSensor(GwnBaseSensor):
    def __init__(self, coordinator, device: dict) -> None:
        super().__init__(coordinator, device, "clients", "Client Count")


class GwnIpSensor(GwnBaseSensor):
    def __init__(self, coordinator, device: dict) -> None:
        super().__init__(coordinator, device, "ip", "IP")


class GwnFirmwareSensor(GwnBaseSensor):
    def __init__(self, coordinator, device: dict) -> None:
        super().__init__(coordinator, device, "firmware", "Firmware")
