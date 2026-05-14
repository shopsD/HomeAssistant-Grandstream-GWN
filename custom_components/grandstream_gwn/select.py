from collections.abc import Callable
from typing import Any

from homeassistant.components.select import SelectEntity
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

def create_entity(current_unique_ids: set[str], cached_unique_ids: set[str], new_entities: list[GwnSelectEntity], entity_type: Callable[[GwnDataUpdateCoordinator, dict[str, Any], str, str, str], GwnSelectEntity], coordinator: GwnDataUpdateCoordinator, data: dict[str, Any], key: str, options_key: str, name_suffix: str) -> None:
    entity: GwnSelectEntity = entity_type(coordinator, data, key, options_key, name_suffix)
    current_unique_ids.add(entity.gwn_unique_id())
    if entity.gwn_unique_id() not in cached_unique_ids:
        new_entities.append(entity) # cache entities to detect later removal

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: GwnDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entity_registry: EntityRegistry = er.async_get(hass)
    cached_unique_ids: set[str] = set()
    @callback
    def _sync_entities() -> None:
        nonlocal cached_unique_ids
        current_unique_ids: set[str] = set()
        new_entities: list[GwnSelectEntity] = []
        if not coordinator.is_readonly():
            networks: dict[str, dict[str, Any]] = _networks(coordinator)
            for network in networks.values():
                for device in network.get(Constants.DEVICES, {}).values():
                    create_entity(current_unique_ids, cached_unique_ids, new_entities, GwnDeviceSelect, coordinator, device, Constants.NETWORK_ID, Constants.NETWORKS, "Network")
                    create_entity(current_unique_ids, cached_unique_ids, new_entities, GwnDeviceSelect, coordinator, device, Constants.AP_2G4_CHANNEL, Constants.CHANNEL_LISTS_2G4, "2.4Ghz Channel")
                    create_entity(current_unique_ids, cached_unique_ids, new_entities, GwnDeviceSelect, coordinator, device, Constants.AP_5G_CHANNEL, Constants.CHANNEL_LISTS_5G, "5Ghz Channel")
                    create_entity(current_unique_ids, cached_unique_ids, new_entities, GwnDeviceSelect, coordinator, device, Constants.AP_6G_CHANNEL, Constants.CHANNEL_LISTS_6G, "6Ghz Channel")

        # Remove any device that is not in the cache since it likely means they are have been removed from gwn manager (removed network, device or ssid)
        removed_unique_ids = cached_unique_ids - current_unique_ids
        for unique_id in removed_unique_ids:
            network_entity_id: str | None = entity_registry.async_get_entity_id("select", DOMAIN, unique_id)
            if network_entity_id is not None:
                entity_registry.async_remove(network_entity_id)
        if len(new_entities) > 0:
            async_add_entities(new_entities)
        cached_unique_ids = current_unique_ids

    _sync_entities()
    entry.async_on_unload(coordinator.async_add_listener(_sync_entities))

class GwnSelectEntity(CoordinatorEntity[GwnDataUpdateCoordinator], SelectEntity):
    def __init__(self, coordinator: GwnDataUpdateCoordinator, network_id: str, root_id: str, key: str, options_key: str, name: str, name_suffix: str, base: str) -> None:

        super().__init__(coordinator)
        self._coordinator: GwnDataUpdateCoordinator = coordinator
        self._network_id: str = network_id
        self._root_id = root_id
        self._key: str = key
        self._name: str = name
        self._options_key: str = options_key

        self._attr_name: str = name_suffix
        self._attr_unique_id: str = f"{base}_{self._root_id}_{key}"

    @property
    def _option_map(self) -> dict[int, str]:
        return {}

    @property
    def _unique_option_map(self) -> dict[int, str]:
        raw_options: dict[int, str] = self._option_map
        found_options: set[str] = set()
        for option_key, option_name in raw_options.items():
            if option_name in found_options:
                raw_options[option_key] = f"{option_name} - ({option_key})"
            else:
                found_options.add(option_name)
        return raw_options

    @property
    def options(self) -> list[str]:
        return list(self._unique_option_map.values())

    def gwn_unique_id(self) -> str:
        return self._attr_unique_id

class GwnDeviceSelect(GwnSelectEntity):
    def __init__(self, coordinator: GwnDataUpdateCoordinator, device: dict[str, Any], key: str, options_key: str, name_suffix: str) -> None:
        self._ap_type: str = device[Constants.AP_TYPE]
        self._sw_version: str = device[Constants.CURRENT_FIRMWARE]
        network_id: str = device[Constants.NETWORK_ID]
        device_mac: str = device[Constants.MAC]
        name: str = device[Constants.AP_NAME]
        super().__init__(coordinator, network_id, device_mac, key, options_key, name, name_suffix, "device")

    @property
    def _option_map(self) -> dict[int, str]:
        device: dict[str, Any] | None = self._current_data()
        if device is None:
            return {}
        raw_options = device.get(self._options_key, {})
        return raw_options if isinstance(raw_options, dict) else {}

    @property
    def current_option(self) -> str | None:
        device: dict[str, Any] | None = self._current_data()
        if device is None:
            return None

        current_value = device.get(self._key)
        return None if current_value is None else self._unique_option_map.get(int(current_value))

    @property
    def device_info(self) -> DeviceInfo | None:
        if self._current_data() is None:
            return None
        return {
            "identifiers": {(DOMAIN, f"device_{self._root_id}")},
            "name": self._name,
            "manufacturer": "Grandstream",
            "model": self._ap_type,
            "sw_version": self._sw_version
        }

    def _current_data(self) -> dict[str, Any] | None:
        networks: dict[str, dict[str, Any]] = _networks(self._coordinator)
        network: dict[str, Any] | None = networks.get(self._network_id)
        device: dict[str, Any] | None = None
        devices: dict[str, Any] = {}
        if network is not None:
            devices = network.get(Constants.DEVICES, {})
            device = devices.get(self._root_id)
        if device is None:
            # device may have moved network so now check every other network for it
            for network in networks.values():
                devices = network.get(Constants.DEVICES, {})
                if isinstance(devices, dict):
                    device = devices.get(self._root_id)
                    if device is not None:
                        break
        if device is not None:
            # update the stored data to the newer one
            self._ap_type = device[Constants.AP_TYPE]
            self._sw_version = device[Constants.CURRENT_FIRMWARE]
            self._name = device[Constants.AP_NAME]
            self._network_id = device[Constants.NETWORK_ID]
        return device

    async def async_select_option(self, option: str) -> None:
        for value, label in self._unique_option_map.items():
            if label == option:
                await self.coordinator.async_set_device_value(self._root_id, self._network_id, self._key, value)
                return
