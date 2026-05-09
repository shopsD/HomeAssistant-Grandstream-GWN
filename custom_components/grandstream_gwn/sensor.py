from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from gwn.constants import Constants

def _networks(coordinator) -> list[dict[str, object]]:
    raw_data = coordinator.data if isinstance(coordinator.data, dict) else {}
    raw_networks = raw_data.get(Constants.GWN, {}).get(Constants.NETWORKS, [])
    return raw_networks if isinstance(raw_networks, list) else []


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]

    networks: list[dict[str, Any]] = _networks(coordinator)
    entities: list[SensorEntity] = []
    for network in networks:
        entities.append(GwnNetworkSensor(coordinator, network, Constants.NETWORK_NAME, "Name"))
        entities.append(GwnNetworkSensor(coordinator, network, Constants.COUNTRY_DISPLAY, "Country"))
        entities.append(GwnNetworkSensor(coordinator, network, Constants.TIMEZONE, "Timezone"))

        for device in network.get(Constants.DEVICES,[]):
            entities.append(GwnDeviceSensor(coordinator, device, Constants.WIRELESS, "Wireless"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.NETWORK_NAME, "Network"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.STATUS, "Status"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.IPV4, "IPv4"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.IPV6, "IPv6"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.CURRENT_FIRMWARE, "Current Firmware"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.NEW_FIRMWARE, "Available Firmware"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.CPU_USAGE, "CPU Usage"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.TEMPERATURE, "Temperature"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.UP_TIME, "Up Time"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.CHANNEL_2_4, "Current 2.4GHz Channel"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.CHANNEL_5, "Current 5GHz Channel"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.CHANNEL_6, "Current 6GHz Channel"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.AP_2G4_CHANNEL, "2.4Ghz Channel"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.AP_5G_CHANNEL, "5Ghz Channel"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.AP_6G_CHANNEL, "6Ghz Channel"))
            entities.append(GwnDeviceSensor(coordinator, device, Constants.MAC, "MAC"))

        for ssid in network.get(Constants.SSIDS,[]):
            entities.append(GwnSsidSensor(coordinator, ssid, Constants.SSID_ENABLE, "Enabled"))
            entities.append(GwnSsidSensor(coordinator, ssid, Constants.PORTAL_ENABLED, "Captive Portal"))
            entities.append(GwnSsidSensor(coordinator, ssid, Constants.CLIENT_ISOLATION_ENABLED, "Client Isolation"))
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
    def __init__(self, coordinator, network: dict[str, Any], key: str, name_suffix: str) -> None:
        super().__init__(coordinator)
        self._network: dict[str, Any] = network
        self._key: str = key
        self._network_id: str = self._network[Constants.NETWORK_ID]
        self._name: str = self._network[Constants.NETWORK_NAME]
        self._attr_name: str = f"{self._name} {name_suffix}"
        self._attr_unique_id: str = f"{self._network_id}_{key}"

    @property
    def native_value(self):
        return self._network.get(self._key)

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"network_{self._network_id}")},
            "name": self._name,
            "manufacturer": "Grandstream",
            "model": "GWN Network",
            "sw_version": self._network.get(Constants.CURRENT_FIRMWARE),
        }

class GwnNetworkSensor(GwnBaseNetworkSensor):
    pass

class GwnBaseDeviceSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, device: dict[str, Any], key: str, name_suffix: str) -> None:
        super().__init__(coordinator)
        self._device: dict[str, Any] = device
        self._key: str = key
        self._device_mac: str = device[Constants.MAC]
        self._name: str = device[Constants.NAME]
        self._attr_name: str = f"{self._name} {name_suffix}"
        self._attr_unique_id: str = f"{self._device_mac}_{key}"

    @property
    def native_value(self):
        return self._device.get(self._key)

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"device_{self._device_mac}")},
            "name": self._name,
            "manufacturer": "Grandstream",
            "model": self._device.get(Constants.AP_TYPE),
            "sw_version": self._device.get(Constants.CURRENT_FIRMWARE),
        }

class GwnDeviceSensor(GwnBaseDeviceSensor):
    pass

class GwnBaseSsidSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, ssid: dict[str, Any], key: str, name_suffix: str) -> None:
        super().__init__(coordinator)
        self._ssid: dict[str, Any] = ssid
        self._key: str = key
        self._ssid_id: str = self._ssid[Constants.SSID_ID]
        self._name: str = self._ssid[Constants.SSID_NAME]
        self._attr_name: str = f"{self._name} {name_suffix}"
        self._attr_unique_id: str = f"{self._ssid_id}_{key}"

    @property
    def native_value(self):
        return self._ssid.get(self._key)

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"ssid_{self._ssid_id}")},
            "name": self._name,
            "manufacturer": "Grandstream",
            "model": self._ssid.get(Constants.NETWORK_NAME, "GWN SSID"),
        }

class GwnSsidSensor(GwnBaseSsidSensor):
    pass
