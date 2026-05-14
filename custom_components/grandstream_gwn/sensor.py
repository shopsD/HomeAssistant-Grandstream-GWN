from collections.abc import Callable
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_registry import EntityRegistry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GwnDataUpdateCoordinator
from gwn.constants import Constants


def _networks(coordinator: GwnDataUpdateCoordinator) -> dict[str, dict[str, Any]]:
    raw_data = coordinator.data if isinstance(coordinator.data, dict) else {}
    raw_networks = raw_data.get(Constants.GWN, {}).get(Constants.NETWORKS, {})
    return raw_networks if isinstance(raw_networks, dict) else {}

def _create_sensor_entity(current_unique_ids: set[str], cached_unique_ids: set[str], new_entities: list[GwnSensorEntity], entity: GwnSensorEntity) -> None:
    current_unique_ids.add(entity.gwn_unique_id())
    if entity.gwn_unique_id() not in cached_unique_ids:
        new_entities.append(entity) # cache entities to detect later removal

def create_entity(current_unique_ids: set[str], cached_unique_ids: set[str], new_entities: list[GwnSensorEntity], entity_type: Callable[[GwnDataUpdateCoordinator, dict[str, Any], str, str], GwnSensorEntity], coordinator: GwnDataUpdateCoordinator, data: dict[str, Any], key: str, name_suffix: str) -> None:
    entity: GwnSensorEntity = entity_type(coordinator, data, key, name_suffix)
    _create_sensor_entity(current_unique_ids, cached_unique_ids, new_entities, entity)

def create_device_entity(current_unique_ids: set[str], cached_unique_ids: set[str], new_entities: list[GwnSensorEntity], entity_type: Callable[[GwnDataUpdateCoordinator, dict[str, Any], str, str, list[str] | None], GwnSensorEntity], coordinator: GwnDataUpdateCoordinator, data: dict[str, Any], key: str, name_suffix: str, units: list[str] | None = None) -> None:
    entity: GwnSensorEntity = entity_type(coordinator, data, key, name_suffix, units)
    _create_sensor_entity(current_unique_ids, cached_unique_ids, new_entities, entity)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: GwnDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entity_registry: EntityRegistry = er.async_get(hass)
    cached_unique_ids: set[str] = set()
    @callback
    def _sync_entities() -> None:
        nonlocal cached_unique_ids
        current_unique_ids: set[str] = set()
        new_entities: list[GwnSensorEntity] = []
        networks: dict[str, dict[str, Any]] = _networks(coordinator)
        for network in networks.values():
            if coordinator.is_readonly():
                create_entity(current_unique_ids, cached_unique_ids, new_entities, GwnNetworkSensor, coordinator, network, Constants.NETWORK_NAME, "Name")
            create_entity(current_unique_ids, cached_unique_ids, new_entities, GwnNetworkSensor, coordinator, network, Constants.COUNTRY_DISPLAY, "Country")
            create_entity(current_unique_ids, cached_unique_ids, new_entities, GwnNetworkSensor, coordinator, network, Constants.TIMEZONE, "Timezone")

            for device in network.get(Constants.DEVICES,{}).values():
                if coordinator.is_readonly():

                    create_device_entity(current_unique_ids, cached_unique_ids, new_entities, GwnDeviceSensor, coordinator, device, Constants.NETWORK_NAME, "Network")
                    create_device_entity(current_unique_ids, cached_unique_ids, new_entities, GwnDeviceSensor, coordinator, device, Constants.AP_NAME, "Name")
                    create_device_entity(current_unique_ids, cached_unique_ids, new_entities, GwnDeviceSensor, coordinator, device, Constants.AP_2G4_CHANNEL, "2.4Ghz Channel")
                    create_device_entity(current_unique_ids, cached_unique_ids, new_entities, GwnDeviceSensor, coordinator, device, Constants.AP_5G_CHANNEL, "5Ghz Channel")
                    create_device_entity(current_unique_ids, cached_unique_ids, new_entities, GwnDeviceSensor, coordinator, device, Constants.AP_6G_CHANNEL, "6Ghz Channel")
                create_device_entity(current_unique_ids, cached_unique_ids, new_entities, GwnDeviceSensor, coordinator, device, Constants.WIRELESS, "Wireless")
                create_device_entity(current_unique_ids, cached_unique_ids, new_entities, GwnDeviceSensor, coordinator, device, Constants.STATUS, "Status")
                create_device_entity(current_unique_ids, cached_unique_ids, new_entities, GwnDeviceSensor, coordinator, device, Constants.IPV4, "IPv4")
                create_device_entity(current_unique_ids, cached_unique_ids, new_entities, GwnDeviceSensor, coordinator, device, Constants.IPV6, "IPv6")
                create_device_entity(current_unique_ids, cached_unique_ids, new_entities, GwnDeviceSensor, coordinator, device, Constants.CURRENT_FIRMWARE, "Current Firmware")
                create_device_entity(current_unique_ids, cached_unique_ids, new_entities, GwnDeviceSensor, coordinator, device, Constants.NEW_FIRMWARE, "Available Firmware")
                create_device_entity(current_unique_ids, cached_unique_ids, new_entities, GwnDeviceSensor, coordinator, device, Constants.CPU_USAGE, "CPU Usage", ["%"])
                create_device_entity(current_unique_ids, cached_unique_ids, new_entities, GwnDeviceSensor, coordinator, device, Constants.TEMPERATURE, "Temperature", ["℃", "°C"])
                create_device_entity(current_unique_ids, cached_unique_ids, new_entities, GwnDeviceSensor, coordinator, device, Constants.UP_TIME, "Up Time", ["s"])
                create_device_entity(current_unique_ids, cached_unique_ids, new_entities, GwnDeviceSensor, coordinator, device, Constants.CHANNEL_2_4, "Current 2.4GHz Channel")
                create_device_entity(current_unique_ids, cached_unique_ids, new_entities, GwnDeviceSensor, coordinator, device, Constants.CHANNEL_5, "Current 5GHz Channel")
                create_device_entity(current_unique_ids, cached_unique_ids, new_entities, GwnDeviceSensor, coordinator, device, Constants.CHANNEL_6, "Current 6GHz Channel")
                create_device_entity(current_unique_ids, cached_unique_ids, new_entities, GwnDeviceSensor, coordinator, device, Constants.MAC, "MAC")

            for ssid in network.get(Constants.SSIDS,{}).values():
                if coordinator.is_readonly():
                    create_entity(current_unique_ids, cached_unique_ids, new_entities, GwnSSIDSensor, coordinator, ssid, Constants.SSID_ENABLE, "Enabled")
                    create_entity(current_unique_ids, cached_unique_ids, new_entities, GwnSSIDSensor, coordinator, ssid, Constants.PORTAL_ENABLED, "Captive Portal")
                    create_entity(current_unique_ids, cached_unique_ids, new_entities, GwnSSIDSensor, coordinator, ssid, Constants.SSID_ISOLATION, "Client Isolation")
                    create_entity(current_unique_ids, cached_unique_ids, new_entities, GwnSSIDSensor, coordinator, ssid, Constants.GHZ2_4_ENABLED, "2.4GHz Station")
                    create_entity(current_unique_ids, cached_unique_ids, new_entities, GwnSSIDSensor, coordinator, ssid, Constants.GHZ5_ENABLED, "5GHz Station")
                    create_entity(current_unique_ids, cached_unique_ids, new_entities, GwnSSIDSensor, coordinator, ssid, Constants.GHZ6_ENABLED, "6GHz Station")
                    create_entity(current_unique_ids, cached_unique_ids, new_entities, GwnSSIDSensor, coordinator, ssid, Constants.SSID_HIDDEN, "Hide WiFi")
                    create_entity(current_unique_ids, cached_unique_ids, new_entities, GwnSSIDSensor, coordinator, ssid, Constants.SSID_VLAN_ID, "VLAN ID")
                    create_entity(current_unique_ids, cached_unique_ids, new_entities, GwnSSIDSensor, coordinator, ssid, Constants.SSID_KEY, "WiFi Passphrase")
                    create_entity(current_unique_ids, cached_unique_ids, new_entities, GwnSSIDSensor, coordinator, ssid, Constants.SSID_NAME, "SSID")
                create_entity(current_unique_ids, cached_unique_ids, new_entities, GwnSSIDSensor, coordinator, ssid, Constants.CLIENT_COUNT, "Clients Online")
                create_entity(current_unique_ids, cached_unique_ids, new_entities, GwnSSIDSensor, coordinator, ssid, Constants.NETWORK_NAME, "Network")

        # Remove any device that is not in the cache since it likely means they are have been removed from gwn manager (removed network, device or ssid)
        removed_unique_ids = cached_unique_ids - current_unique_ids
        for unique_id in removed_unique_ids:
            network_entity_id: str | None = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
            if network_entity_id is not None:
                entity_registry.async_remove(network_entity_id)
        if len(new_entities) > 0:
            async_add_entities(new_entities)
        cached_unique_ids = current_unique_ids

    _sync_entities()
    entry.async_on_unload(coordinator.async_add_listener(_sync_entities))

class GwnSensorEntity(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: GwnDataUpdateCoordinator, network_id: str, root_id: str, key: str, name: str, name_suffix: str, base: str) -> None:
        super().__init__(coordinator)
        self._coordinator: GwnDataUpdateCoordinator = coordinator
        self._network_id: str = network_id
        self._root_id = root_id
        self._key: str = key
        self._name: str = name

        self._attr_name: str = name_suffix
        self._attr_unique_id: str = f"{base}_{self._root_id}_{key}"

    def gwn_unique_id(self) -> str:
        return self._attr_unique_id

class GwnNetworkSensor(GwnSensorEntity):
    def __init__(self, coordinator: GwnDataUpdateCoordinator, network: dict[str, Any], key: str, name_suffix: str) -> None:
        network_id: str = network[Constants.NETWORK_ID]
        name: str = network[Constants.NETWORK_NAME]
        super().__init__(coordinator, network_id, network_id, key, name, name_suffix, "network")

    @property
    def native_value(self) -> None | str:
        network: dict[str, Any] | None = self._current_data()
        return None if network is None else network.get(self._key)

    @property
    def device_info(self) -> DeviceInfo | None:
        if self._current_data() is None:
            return None
        return {
            "identifiers": {(DOMAIN, f"network_{self._root_id}")},
            "name": self._name,
            "manufacturer": "Grandstream",
            "model": "GWN Network"
        }

    def _current_data(self) -> dict[str, Any] | None:
        networks: dict[str, dict[str, Any]] = _networks(self._coordinator)
        network: dict[str, Any] | None = networks.get(self._network_id)
        if network is not None:
            # update the stored data to the newer one
            self._name = network[Constants.NETWORK_NAME]
        return network

class GwnDeviceSensor(GwnSensorEntity):
    def __init__(self, coordinator: GwnDataUpdateCoordinator, device: dict[str, Any], key: str, name_suffix: str, units: list[str] | None) -> None:
        self._ap_type: str = device[Constants.AP_TYPE]
        self._sw_version: str = device[Constants.CURRENT_FIRMWARE]
        self._units = units

        network_id: str = device[Constants.NETWORK_ID]
        device_mac: str = device[Constants.MAC]
        name: str = device[Constants.AP_NAME]
        super().__init__(coordinator, network_id, device_mac, key, name, name_suffix, "device")

    @property
    def native_value(self) -> None | str | int | bool:
        device: dict[str, Any] | None = self._current_data()
        if device is None:
            return None
        value: int | str | bool | None = device.get(self._key)
        if self._units is not None and isinstance(value, str):
            return self._int_value_normaliser(value)
        else:
            return value

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

    def _int_value_normaliser(self, value: str) -> int | None:
        if value is None or self._units is None:
            return None
        for unit in self._units:
            value = value.replace(unit, "")
        return int(value.strip())

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

class GwnSSIDSensor(GwnSensorEntity):
    def __init__(self, coordinator: GwnDataUpdateCoordinator, ssid: dict[str, Any], key: str, name_suffix: str) -> None:

        self._model: str = ssid.get(Constants.NETWORK_NAME, "GWN SSID")

        network_id: str = ssid[Constants.NETWORK_ID]
        ssid_id: str = ssid[Constants.SSID_ID]
        name: str = ssid[Constants.SSID_NAME]
        super().__init__(coordinator, network_id, ssid_id, key, name, name_suffix, "ssid")

    @property
    def native_value(self) -> None | str | int | bool:
        ssid: dict[str, Any] | None = self._current_data()
        return None if ssid is None else ssid.get(self._key)

    @property
    def device_info(self) -> DeviceInfo | None:
        if self._current_data() is None:
            return None
        return {
            "identifiers": {(DOMAIN, f"ssid_{self._root_id}")},
            "name": self._name,
            "manufacturer": "Grandstream",
            "model": self._model
        }

    def _current_data(self) -> dict[str, Any] | None:
        networks: dict[str, dict[str, Any]] = _networks(self._coordinator)
        network: dict[str, Any] | None = networks.get(self._network_id)
        ssid: dict[str, Any] | None = None
        ssids: dict[str, Any] = {}
        if network is not None:
            ssids = network.get(Constants.SSIDS, {})
            ssid = ssids.get(self._root_id)
        if ssid is None:
            # ssid may have moved network if a new instance of gwn manager was created which reset the ssid ids
            for network in networks.values():
                ssids = network.get(Constants.SSIDS, {})
                if isinstance(ssids, dict):
                    ssid = ssids.get(self._root_id)
                    if ssid is not None:
                        break
        if ssid is not None:
            self._model = ssid.get(Constants.NETWORK_NAME, "GWN SSID")
            self._name = ssid[Constants.SSID_NAME]
            self._network_id = ssid[Constants.NETWORK_ID]
            return ssid
        return None
