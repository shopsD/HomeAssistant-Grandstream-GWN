from typing import Any

from homeassistant.components.text import TextEntity
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
    entities: list[TextEntity] = []
    for network in networks.values():
        entities.append(GwnNetworkText(coordinator, network, Constants.NETWORK_NAME, "Name"))

        for ssid in network.get(Constants.SSIDS, {}).values():
            entities.append(GwnSSIDText(coordinator, ssid, Constants.SSID_NAME, "SSID"))
            entities.append(GwnSSIDText(coordinator, ssid, Constants.SSID_KEY, "WiFi Passphrase"))

        for device in network.get(Constants.DEVICES, {}).values():
            entities.append(GwnDeviceText(coordinator, device, Constants.AP_NAME, "Name"))

    async_add_entities(entities)

class GwnNetworkText(CoordinatorEntity[GwnDataUpdateCoordinator], TextEntity):
    def __init__(self, coordinator, network: dict[str, Any], key: str, name_suffix: str) -> None:
        super().__init__(coordinator)
        self._key: str = key
        self._network_id: str = network[Constants.NETWORK_ID]
        self._name: str = network[Constants.NETWORK_NAME]
        self._attr_name: str = f"{self._name} {name_suffix}"
        self._attr_unique_id: str = f"{self._network_id}_{key}"

    @property
    def native_value(self) -> str | None:
        networks: dict[str, dict[str, Any]] = _networks(self.coordinator)
        network: dict[str, Any] | None = networks.get(self._network_id)
        if network is None:
            return None
        value = network.get(self._key)
        return None if value is None else str(value)

    @property
    def device_info(self) -> DeviceInfo | None:
        return {
            "identifiers": {(DOMAIN, f"network_{self._network_id}")},
            "name": self._name,
            "manufacturer": "Grandstream",
            "model": "GWN Network"
        }

    async def async_set_value(self, value: str) -> None:
        await self.coordinator.async_set_network_value(self._network_id, self._key, value)

class GwnDeviceText(CoordinatorEntity[GwnDataUpdateCoordinator], TextEntity):
    def __init__(self, coordinator: GwnDataUpdateCoordinator, device: dict[str, Any], key: str, name_suffix: str) -> None:
        super().__init__(coordinator)
        self._coordinator: GwnDataUpdateCoordinator = coordinator
        self._device: dict[str, Any] = device
        self._key: str = key
        self._device_mac: str = device[Constants.MAC]
        self._name: str = device[Constants.AP_NAME]
        self._attr_name: str = f"{self._name} {name_suffix}"
        self._attr_unique_id: str = f"{self._device_mac}_{key}"
        self._ap_type: str = device[Constants.AP_TYPE]
        self._sw_version: str = device[Constants.CURRENT_FIRMWARE]
        self._network_id: str = device[Constants.NETWORK_ID]

    @property
    def native_value(self) -> str | None:
        networks: dict[str, dict[str, Any]] = _networks(self._coordinator)
        network: dict[str, Any] | None = networks.get(self._network_id)
        if network is None:
            return None
        devices: dict[str, Any] = network.get(Constants.DEVICES, {})
        device: dict[str, Any] | None = devices.get(self._device_mac)
        if device is None:
            return None
        value = device.get(self._key)
        return None if value is None else str(value)

    @property
    def device_info(self) -> DeviceInfo | None:
        return {
            "identifiers": {(DOMAIN, f"device_{self._device_mac}")},
            "name": self._name,
            "manufacturer": "Grandstream",
            "model": self._ap_type,
            "sw_version": self._sw_version
        }

    async def async_set_value(self, value: str) -> None:
        await self.coordinator.async_set_device_value(self._device_mac, self._network_id, self._key, value)

class GwnSSIDText(CoordinatorEntity[GwnDataUpdateCoordinator], TextEntity):
    def __init__(self, coordinator: GwnDataUpdateCoordinator, ssid: dict[str, Any], key: str, name_suffix: str) -> None:
        super().__init__(coordinator)
        self._coordinator: GwnDataUpdateCoordinator = coordinator
        self._key: str = key
        self._ssid_id: str = ssid[Constants.SSID_ID]
        self._name: str = ssid[Constants.SSID_NAME]
        self._attr_name: str = f"{self._name} {name_suffix}"
        self._attr_unique_id: str = f"{self._ssid_id}_{key}"
        self._model: str = ssid.get(Constants.NETWORK_NAME, "GWN SSID")
        self._network_id: str = ssid[Constants.NETWORK_ID]

    @property
    def native_value(self) -> str | None:
        networks: dict[str, dict[str, Any]] = _networks(self._coordinator)
        network: dict[str, Any] | None = networks.get(self._network_id)
        if network is None:
            return None
        ssids: dict[str, Any] = network.get(Constants.SSIDS, {})
        ssid: dict[str, Any] | None = ssids.get(self._ssid_id)
        if ssid is None:
            return None
        value = ssid.get(self._key)
        return None if value is None else str(value)

    @property
    def device_info(self) -> DeviceInfo | None:
        return {
            "identifiers": {(DOMAIN, f"ssid_{self._ssid_id}")},
            "name": self._name,
            "manufacturer": "Grandstream",
            "model": self._model
        }

    async def async_set_value(self, value: str) -> None:
        await self.coordinator.async_set_ssid_value(self._ssid_id, self._network_id, self._key, value)
