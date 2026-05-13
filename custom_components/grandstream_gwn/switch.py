from collections.abc import Callable
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_registry import EntityRegistry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GwnDataUpdateCoordinator
from .sensor import _networks
from gwn.constants import Constants

def _create_switch_entity(current_unique_ids: set[str], cached_unique_ids: set[str], new_entities: list[GwnSwitchEntity], entity: GwnSwitchEntity) -> None:
    current_unique_ids.add(entity.gwn_unique_id())
    if entity.gwn_unique_id() not in cached_unique_ids:
        new_entities.append(entity)

def create_entity(current_unique_ids: set[str], cached_unique_ids: set[str], new_entities: list[GwnSwitchEntity], entity_type: Callable[[GwnDataUpdateCoordinator, dict[str, Any], str, str], GwnSwitchEntity], coordinator: GwnDataUpdateCoordinator, data: dict[str, Any], key: str, name_suffix: str) -> None:
    entity: GwnSwitchEntity = entity_type(coordinator, data, key, name_suffix)
    _create_switch_entity(current_unique_ids, cached_unique_ids, new_entities, entity)

def create_ssid_device_entity(current_unique_ids: set[str], cached_unique_ids: set[str], new_entities: list[GwnSwitchEntity], entity_type: Callable[[GwnDataUpdateCoordinator, dict[str, Any], str, str, str], GwnSwitchEntity], coordinator: GwnDataUpdateCoordinator, data: dict[str, Any], key: str, name_suffix: str, device_mac: str) -> None:
    entity: GwnSwitchEntity = entity_type(coordinator, data, key, name_suffix, device_mac)
    _create_switch_entity(current_unique_ids, cached_unique_ids, new_entities, entity)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: GwnDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entity_registry: EntityRegistry = er.async_get(hass)
    cached_unique_ids: set[str] = set()

    @callback
    def _sync_entities() -> None:
        nonlocal cached_unique_ids
        current_unique_ids: set[str] = set()
        new_entities: list[GwnSwitchEntity] = []
        if not coordinator.is_readonly():
            networks: dict[str, dict[str, Any]] = _networks(coordinator)
            for network in networks.values():
                for ssid in network.get(Constants.SSIDS,{}).values():
                    create_entity(current_unique_ids, cached_unique_ids, new_entities, GwnSSIDSwitch, coordinator, ssid, Constants.SSID_ENABLE, "Enabled")
                    create_entity(current_unique_ids, cached_unique_ids, new_entities, GwnSSIDSwitch, coordinator, ssid, Constants.PORTAL_ENABLED, "Captive Portal")
                    create_entity(current_unique_ids, cached_unique_ids, new_entities, GwnSSIDSwitch, coordinator, ssid, Constants.SSID_ISOLATION, "Client Isolation")
                    create_entity(current_unique_ids, cached_unique_ids, new_entities, GwnSSIDSwitch, coordinator, ssid, Constants.GHZ2_4_ENABLED, "2.4GHz Station")
                    create_entity(current_unique_ids, cached_unique_ids, new_entities, GwnSSIDSwitch, coordinator, ssid, Constants.GHZ5_ENABLED, "5GHz Station")
                    create_entity(current_unique_ids, cached_unique_ids, new_entities, GwnSSIDSwitch, coordinator, ssid, Constants.GHZ6_ENABLED, "6GHz Station")
                    create_entity(current_unique_ids, cached_unique_ids, new_entities, GwnSSIDSwitch, coordinator, ssid, Constants.SSID_HIDDEN, "Hide WiFi")
                    for device in network.get(Constants.DEVICES,{}).values():
                        device_mac: str = device.get(Constants.MAC)
                        create_ssid_device_entity(current_unique_ids, cached_unique_ids, new_entities, GwnSSIDDeviceSwitch, coordinator, ssid, Constants.TOGGLE_DEVICE, f"Assign: {device_mac}", device_mac)

        removed_unique_ids = cached_unique_ids - current_unique_ids
        for unique_id in removed_unique_ids:
            network_entity_id: str | None = entity_registry.async_get_entity_id("switch", DOMAIN, unique_id)
            if network_entity_id is not None:
                entity_registry.async_remove(network_entity_id)
        if len(new_entities) > 0:
            async_add_entities(new_entities)
        cached_unique_ids = current_unique_ids

    _sync_entities()
    entry.async_on_unload(coordinator.async_add_listener(_sync_entities))

class GwnSwitchEntity(CoordinatorEntity[GwnDataUpdateCoordinator], SwitchEntity):
    def __init__(self, coordinator: GwnDataUpdateCoordinator, network_id: str, root_id: str, key: str, name: str, name_suffix: str) -> None:
        super().__init__(coordinator)
        self._coordinator: GwnDataUpdateCoordinator = coordinator
        self._network_id: str = network_id
        self._root_id = root_id
        self._key: str = key
        self._name: str = name

        self._attr_name: str = f"{self._name} {name_suffix}"
        self._attr_unique_id: str = f"{self._root_id}_{key}"

    async def _toggle_value(self, value: bool) -> bool:
        return False

    async def async_turn_on(self, **kwargs) -> None:
        await self._toggle_value(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._toggle_value(False)

    def gwn_unique_id(self) -> str:
        return self._attr_unique_id

class GwnSSIDSwitch(GwnSwitchEntity):
    def __init__(self, coordinator: GwnDataUpdateCoordinator, ssid: dict[str, Any], key: str, name_suffix: str) -> None:
        self._model: str = ssid.get(Constants.NETWORK_NAME, "GWN SSID")

        network_id: str = ssid[Constants.NETWORK_ID]
        ssid_id: str = ssid[Constants.SSID_ID]
        name: str = ssid[Constants.SSID_NAME]
        super().__init__(coordinator, network_id, ssid_id, key, name, name_suffix)

    async def _toggle_value(self, value: bool) -> bool:
        return await self.coordinator.async_set_ssid_value(self._root_id, self._network_id, self._key, value)

    @property
    def is_on(self) -> bool:
        networks: dict[str, dict[str, Any]] = _networks(self._coordinator)
        network: dict[str, Any] | None = networks.get(self._network_id)
        if network is None:
            return False
        ssids: dict[str, Any] = network.get(Constants.SSIDS, {})
        ssid: dict[str, Any] | None = ssids.get(self._root_id)
        if ssid is None:
            return False

        value = ssid.get(self._key)
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value == 1
        return False # this is an error

    @property
    def device_info(self) -> DeviceInfo | None:
        return {
            "identifiers": {(DOMAIN, f"ssid_{self._root_id}")},
            "name": self._name,
            "manufacturer": "Grandstream",
            "model": self._model
        }

class GwnSSIDDeviceSwitch(GwnSSIDSwitch):
    def __init__(self, coordinator: GwnDataUpdateCoordinator, ssid: dict[str, Any], key: str, name_suffix: str, device_mac: str) -> None:
        super().__init__(coordinator, ssid, key, name_suffix)
        self._device_mac: str = device_mac
        self._attr_unique_id: str = f"{self._root_id}_{key}_{self._device_mac}"

    async def _toggle_value(self, value: bool) -> bool:
        return await self.coordinator.async_set_ssid_value(self._root_id, self._network_id, self._key, {self._device_mac: value})

    @property
    def is_on(self) -> bool:
        networks: dict[str, dict[str, Any]] = _networks(self._coordinator)
        network: dict[str, Any] | None = networks.get(self._network_id)
        if network is None:
            return False
        ssids: dict[str, Any] = network.get(Constants.SSIDS, {})
        ssid: dict[str, Any] | None = ssids.get(self._root_id)
        if ssid is None:
            return False
        assigned = ssid.get(Constants.ASSIGNED_DEVICES, {})

        return isinstance(assigned, dict) and self._device_mac in assigned
