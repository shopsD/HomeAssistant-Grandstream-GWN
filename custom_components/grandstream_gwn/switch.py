from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GwnDataUpdateCoordinator
from .sensor import _networks
from gwn.constants import Constants

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: GwnDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
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
            for device in network.get(Constants.DEVICES,[]):
                device_mac: str = device.get(Constants.MAC)
                entities.append(GwnSSIDDeviceSwitch(coordinator, ssid, Constants.TOGGLE_DEVICE, f"Assign: {device_mac}", device_mac))

    async_add_entities(entities)

class GwnSSIDSwitch(CoordinatorEntity[GwnDataUpdateCoordinator], SwitchEntity):
    def __init__(self, coordinator, ssid: dict[str, Any], key: str, name_suffix: str) -> None:
        super().__init__(coordinator)
        self._ssid: dict[str, Any] = ssid
        self._key: str = key
        self._ssid_id: str = self._ssid[Constants.SSID_ID]
        self._name: str = self._ssid[Constants.SSID_NAME]
        self._attr_name: str = f"{self._name} {name_suffix}"
        self._attr_unique_id: str = f"{self._ssid_id}_{key}"

    async def _toggle_value(self, value: bool) -> bool:
        return await self.coordinator.async_set_ssid_value(int(self._ssid[Constants.SSID_ID]), int(self._ssid[Constants.NETWORK_ID]), self._key, value)

    @property
    def is_on(self) -> bool:
        value = self._ssid.get(self._key)
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value == 1
        return False # this is an error

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"ssid_{self._ssid_id}")},
            "name": self._name,
            "manufacturer": "Grandstream",
            "model": self._ssid.get(Constants.NETWORK_NAME, "GWN SSID"),
        }

    async def async_turn_on(self, **kwargs) -> None:
        await self._toggle_value(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._toggle_value(False)


class GwnSSIDDeviceSwitch(CoordinatorEntity[GwnDataUpdateCoordinator], SwitchEntity):
    def __init__(self, coordinator, ssid: dict[str, Any], key: str, name_suffix: str, device_mac: str) -> None:
        super().__init__(coordinator)
        self._ssid: dict[str, Any] = ssid
        self._key: str = key
        self._device_mac: str = device_mac
        self._ssid_id: str = self._ssid[Constants.SSID_ID]
        self._name: str = self._ssid[Constants.SSID_NAME]
        self._attr_name: str = f"{self._name} {name_suffix}"
        self._attr_unique_id: str = f"{self._ssid_id}_{key}_{self._device_mac}"

    async def _toggle_value(self, value: bool) -> bool:
        return await self.coordinator.async_set_ssid_value(int(self._ssid[Constants.SSID_ID]), int(self._ssid[Constants.NETWORK_ID]), self._key, {self._device_mac: value})

    @property
    def is_on(self) -> bool:
        assigned = self._ssid.get(Constants.ASSIGNED_DEVICES, {})
        return isinstance(assigned, dict) and self._device_mac in assigned

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"ssid_{self._ssid_id}")},
            "name": self._name,
            "manufacturer": "Grandstream",
            "model": self._ssid.get(Constants.NETWORK_NAME, "GWN SSID"),
        }

    async def async_turn_on(self, **kwargs) -> None:
        await self._toggle_value(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._toggle_value(False)