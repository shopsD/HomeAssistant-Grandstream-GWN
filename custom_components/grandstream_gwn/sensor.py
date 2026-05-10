from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GwnDataUpdateCoordinator
from gwn.constants import Constants

def _networks(coordinator: GwnDataUpdateCoordinator) -> dict[str, dict[str, Any]]:
    raw_data = coordinator.data if isinstance(coordinator.data, dict) else {}
    raw_networks = raw_data.get(Constants.GWN, {}).get(Constants.NETWORKS, {})
    return raw_networks if isinstance(raw_networks, dict) else {}

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: GwnDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    networks: dict[str, dict[str, Any]] = _networks(coordinator)
    entities: list[SensorEntity] = []
    for network in networks.values():
        entities.append(GwnNetworkSensor(coordinator, network, Constants.NETWORK_NAME, "Name"))
        entities.append(GwnNetworkSensor(coordinator, network, Constants.COUNTRY_DISPLAY, "Country"))
        entities.append(GwnNetworkSensor(coordinator, network, Constants.TIMEZONE, "Timezone"))

        for device in network.get(Constants.DEVICES,{}).values():
            entities.append(GwnDeviceSensor(coordinator, device, Constants.WIRELESS, "Wireless"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.NETWORK_NAME, "Network"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.STATUS, "Status"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.IPV4, "IPv4"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.IPV6, "IPv6"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.CURRENT_FIRMWARE, "Current Firmware"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.NEW_FIRMWARE, "Available Firmware"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.CPU_USAGE, "CPU Usage", ["%"]))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.TEMPERATURE, "Temperature", ["℃", "°C"]))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.UP_TIME, "Up Time", ["s"]))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.CHANNEL_2_4, "Current 2.4GHz Channel"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.CHANNEL_5, "Current 5GHz Channel"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.CHANNEL_6, "Current 6GHz Channel"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.AP_2G4_CHANNEL, "2.4Ghz Channel"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.AP_5G_CHANNEL, "5Ghz Channel"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.AP_6G_CHANNEL, "6Ghz Channel"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.MAC, "MAC"))

        for ssid in network.get(Constants.SSIDS,{}).values():
            entities.append(GwnSsidSensor(coordinator, ssid, Constants.SSID_ENABLE, "Enabled"))
            entities.append(GwnSsidSensor(coordinator, ssid, Constants.PORTAL_ENABLED, "Captive Portal"))
            entities.append(GwnSsidSensor(coordinator, ssid, Constants.SSID_ISOLATION, "Client Isolation"))
            entities.append(GwnSsidSensor(coordinator, ssid, Constants.GHZ2_4_ENABLED, "2.4GHz Station"))
            entities.append(GwnSsidSensor(coordinator, ssid, Constants.GHZ5_ENABLED, "5GHz Station"))
            entities.append(GwnSsidSensor(coordinator, ssid, Constants.GHZ6_ENABLED, "6GHz Station"))
            entities.append(GwnSsidSensor(coordinator, ssid, Constants.SSID_HIDDEN, "Hide WiFi"))
            entities.append(GwnSsidSensor(coordinator, ssid, Constants.SSID_VLAN_ID, "VLAN ID"))
            entities.append(GwnSsidSensor(coordinator, ssid, Constants.SSID_KEY, "WiFi Passphrase"))
            entities.append(GwnSsidSensor(coordinator, ssid, Constants.SSID_NAME, "SSID"))
            entities.append(GwnSsidSensor(coordinator, ssid, Constants.CLIENT_COUNT, "Clients Online"))
            entities.append(GwnSsidSensor(coordinator, ssid, Constants.NETWORK_NAME, "Network"))

    async_add_entities(entities)

class GwnBaseNetworkSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: GwnDataUpdateCoordinator, network: dict[str, Any], key: str, name_suffix: str) -> None:
        super().__init__(coordinator)
        self._key: str = key
        self._coordinator: GwnDataUpdateCoordinator = coordinator
        self._network_id: str = network[Constants.NETWORK_ID]
        self._name: str = network[Constants.NETWORK_NAME]
        self._attr_name: str = f"{self._name} {name_suffix}"
        self._attr_unique_id: str = f"{self._network_id}_{key}"

    @property
    def native_value(self) -> None | str:
        networks: dict[str, dict[str, Any]] = _networks(self._coordinator)
        network: dict[str, Any] | None = networks.get(self._network_id)
        return None if network is None else network.get(self._key)

    @property
    def device_info(self) -> DeviceInfo | None:
        return {
            "identifiers": {(DOMAIN, f"network_{self._network_id}")},
            "name": self._name,
            "manufacturer": "Grandstream",
            "model": "GWN Network"
        }

class GwnNetworkSensor(GwnBaseNetworkSensor):
    pass

class GwnBaseDeviceSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: GwnDataUpdateCoordinator, device: dict[str, Any], key: str, name_suffix: str, units: list[str] | None = None) -> None:
        super().__init__(coordinator)
        self._coordinator: GwnDataUpdateCoordinator = coordinator
        self._key: str = key
        self._units: list[str] | None = units
        self._device_mac: str = device[Constants.MAC]
        self._name: str = device[Constants.AP_NAME]
        self._attr_name: str = f"{self._name} {name_suffix}"
        self._attr_unique_id: str = f"{self._device_mac}_{key}"
        self._ap_type: str = device[Constants.AP_TYPE]
        self._sw_version: str = device[Constants.CURRENT_FIRMWARE]
        self._network_id: str = device[Constants.NETWORK_ID]

    def _int_value_normaliser(self, value: str) -> int | None:
        if value is None or self._units is None:
            return None
        for unit in self._units:
            value = value.replace(unit, "")
        return int(value.strip())

    @property
    def native_value(self) -> None | str | int:
        networks: dict[str, dict[str, Any]] = _networks(self._coordinator)
        network: dict[str, Any] | None = networks.get(self._network_id)
        if network is None:
            return None
        devices: dict[str, Any] = network.get(Constants.DEVICES, {})
        device: dict[str, Any] | None = devices.get(self._device_mac)
        if device is None:
            return None
        value: int | str | None = device.get(self._key)
        if self._units is not None and isinstance(value, str):
            return self._int_value_normaliser(value)
        else: 
            return value

    @property
    def device_info(self) -> DeviceInfo | None:
        return {
            "identifiers": {(DOMAIN, f"device_{self._device_mac}")},
            "name": self._name,
            "manufacturer": "Grandstream",
            "model": self._ap_type,
            "sw_version": self._sw_version
        }

class GwnDeviceSensor(GwnBaseDeviceSensor):
    pass

class GwnBaseSsidSensor(CoordinatorEntity, SensorEntity):
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
    def native_value(self) -> None | str | int | bool:
        networks: dict[str, dict[str, Any]] = _networks(self._coordinator)
        network: dict[str, Any] | None = networks.get(self._network_id)
        if network is None:
            return None
        ssids: dict[str, Any] = network.get(Constants.SSIDS, {})
        ssid: dict[str, Any] | None = ssids.get(self._ssid_id)
        return None if ssid is None else ssid.get(self._key)

    @property
    def device_info(self) -> DeviceInfo | None:
        return {
            "identifiers": {(DOMAIN, f"ssid_{self._ssid_id}")},
            "name": self._name,
            "manufacturer": "Grandstream",
            "model": self._model
        }

class GwnSsidSensor(GwnBaseSsidSensor):
    pass
