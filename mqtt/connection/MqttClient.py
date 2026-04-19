import logging
import json
from typing import Any

from gwn.constants import Constants
from mqtt.config import MqttConfig
from mqtt.connection.MqttInterface import MqttInterface

_LOGGER = logging.getLogger(Constants.LOG)

class MqttClient:
    def __init__(self, config: MqttConfig) -> None:
        self._config = config
        self._interface = MqttInterface(config)

    def _strip_mac(self, mac: str) -> str:
        return mac.replace(":", "").replace("-","").lower()

    def _normalise_macs(self, macs:dict[int | str, Any] ) -> dict[str, Any]:
        normalised: dict[str, Any] = {}
        for mac, enabled in macs.items():
            normalised[self._strip_mac(str(mac))] = enabled
        return normalised

    def _ha_device_block(self, identifier: str, name: str, model: str) -> dict[str, object]:
        return {
            "identifiers": [identifier],
            "name": name,
            "manufacturer": "Grandstream",
            "model": model
        }

    def _ha_discovery_topic(self, component: str, object_id: str) -> str:
        return f"homeassistant/{component}/{object_id}/config"

    def _generic_ssid_payload_to_homeassistant(self, state_topic: str, payload: dict[str, object]) -> list[tuple[str, dict[str, object]]]:
        ssid_id: str = str(payload.get("id"))
        ssid_id_int: int = int(ssid_id)

        ssid_name: str = str(payload.get('ssidName'))
        ssid_model: str = "GWN SSID"
        if ssid_id_int in self._config.homeassistant.ssid_name_override:
            ssid_model = ssid_name
            ssid_name = str(self._config.homeassistant.ssid_name_override[ssid_id_int])
        
        device = self._ha_device_block(f"gwn_ssid_{ssid_id}", ssid_name, ssid_model)

        return [
            (
                self._ha_discovery_topic("binary_sensor", f"gwn_ssid_{ssid_id}_enabled"),
                {
                    "name": "Enabled",
                    "unique_id": f"gwn_ssid_{ssid_id}_enabled",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.ssidEnable }}",
                    "payload_on": True,
                    "payload_off": False,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("binary_sensor", f"gwn_ssid_{ssid_id}_portal"),
                {
                    "name": "Captive Portal",
                    "unique_id": f"gwn_ssid_{ssid_id}_portal",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.portalEnabled }}",
                    "payload_on": True,
                    "payload_off": False,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_ssid_{ssid_id}_vlan"),
                {
                    "name": "VLAN ID",
                    "unique_id": f"gwn_ssid_{ssid_id}_vlan",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.ssidVlanid if value_json.get('ssidVlanEnabled') else 'No VLAN' }}",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_ssid_{ssid_id}_assigned_names"),
                {
                    "name": "Devices",
                    "unique_id": f"gwn_ssid_{ssid_id}_devices",
                    "state_topic": state_topic,
                    "value_template": "{% set devices = value_json.get('assignedDevices', []) %}{% if devices %}{% for dev in devices %}{{ dev.name if dev.name else dev.mac }}{% if not loop.last %}, {% endif %}{% endfor %}{% else %}None{% endif %}",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("binary_sensor", f"gwn_ssid_{ssid_id}_client_isolation_enabled"),
                {
                    "name": "Client Isolation",
                    "unique_id": f"gwn_ssid_{ssid_id}_client_isolation_enabled",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.clientIsolationEnabled }}",
                    "payload_on": True,
                    "payload_off": False,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("binary_sensor", f"gwn_ssid_{ssid_id}_enabled_2_4"),
                {
                    "name": "2.4GHz Station",
                    "unique_id": f"gwn_ssid_{ssid_id}_enabled_2_4",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.ghz2_4_Enabled }}",
                    "payload_on": True,
                    "payload_off": False,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("binary_sensor", f"gwn_ssid_{ssid_id}_enabled_5"),
                {
                    "name": "5GHz Station",
                    "unique_id": f"gwn_ssid_{ssid_id}_enabled_5",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.ghz5_Enabled }}",
                    "payload_on": True,
                    "payload_off": False,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("binary_sensor", f"gwn_ssid_{ssid_id}_enabled_6"),
                {
                    "name": "6GHz Station",
                    "unique_id": f"gwn_ssid_{ssid_id}_enabled_6",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.ghz6_Enabled }}",
                    "payload_on": True,
                    "payload_off": False,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_ssid_{ssid_id}_passphrase"),
                {
                    "name": "WiFi Passphrase",
                    "unique_id": f"gwn_ssid_{ssid_id}_passphrase",
                    "state_topic": state_topic,
                     "value_template": "{{ value_json.ssidKey }}",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("binary_sensor", f"gwn_ssid_{ssid_id}_hidden"),
                {
                    "name": "WiFi Hidden",
                    "unique_id": f"gwn_ssid_{ssid_id}_hidden",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.ssidSsidHidden }}",
                    "payload_on": True,
                    "payload_off": False,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_ssid_{ssid_id}_client_count"),
                {
                    "name": "Clients Online",
                    "unique_id": f"gwn_ssid_{ssid_id}_client_count",
                    "state_topic": state_topic,
                     "value_template": "{{ value_json.onlineDevices }}",
                    "device": device
                }
            )
        ]

    def _generic_device_payload_to_homeassistant(self, state_topic: str, payload: dict[str, object]) -> list[tuple[str, dict[str, object]]]:
        device_mac = str(payload.get("mac"))
        normalised_device_mac = self._strip_mac(device_mac)

        normalised_name_override_macs = self._normalise_macs(self._config.homeassistant.device_name_override)
        device_model: str = device_mac
        device_name: str = payload.get("name")
        if len(device_name) == 0:
            device_name = str(payload.get("apType", "GWN Device"))

        if normalised_device_mac in normalised_name_override_macs:
            device_model = device_name if len(device_name) > 0 else device_mac
            device_name = str(normalised_name_override_macs[normalised_device_mac])

        device = self._ha_device_block(f"gwn_device_{normalised_device_mac}", device_name, device_model)

        return [
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{normalised_device_mac}_network_name"),
                {
                    "name": "Network",
                    "unique_id": f"gwn_device_{normalised_device_mac}_network_name",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.networkName }}",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("binary_sensor", f"gwn_device_{normalised_device_mac}_status"),
                {
                    "name": "Status",
                    "unique_id": f"gwn_device_{normalised_device_mac}_status",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.status }}",
                    "payload_on": True,
                    "payload_off": False,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("binary_sensor", f"gwn_device_{normalised_device_mac}_wireless"),
                {
                    "name": "Wireless Status",
                    "unique_id": f"gwn_device_{normalised_device_mac}_wireless",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.wireless }}",
                    "payload_on": True,
                    "payload_off": False,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{normalised_device_mac}_ipv4"),
                {
                    "name": "IPv4",
                    "unique_id": f"gwn_device_{normalised_device_mac}_ipv4",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.ip }}",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{normalised_device_mac}_ipv6"),
                {
                    "name": "IPv6",
                    "unique_id": f"gwn_device_{normalised_device_mac}_ipv6",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.ipv6 }}",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{normalised_device_mac}_firmware"),
                {
                    "name": "Current Firmware",
                    "unique_id": f"gwn_device_{normalised_device_mac}_firmware",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.versionFirmware }}",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{normalised_device_mac}_firmware_new"),
                {
                    "name": "Available Firmware",
                    "unique_id": f"gwn_device_{normalised_device_mac}_firmware_new",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.newFirmware }}",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{normalised_device_mac}_cpu_usage"),
                {
                    "name": "CPU Usage",
                    "unique_id": f"gwn_device_{normalised_device_mac}_cpu_usage",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.cpuUsage }}",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{normalised_device_mac}_temperature"),
                {
                    "name": "Temperature",
                    "unique_id": f"gwn_device_{normalised_device_mac}_temperature",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.temperature }}",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{normalised_device_mac}_ssid_names"),
                {
                    "name": "SSIDs",
                    "unique_id": f"gwn_device_{normalised_device_mac}_ssid_names",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.ssids | map(attribute='ssidName') | join(', ') }}",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{normalised_device_mac}_uptime"),
                {
                    "name": "Up Time",
                    "unique_id": f"gwn_device_{normalised_device_mac}_uptime",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.upTime }}",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{normalised_device_mac}_channel_2_4"),
                {
                    "name": "2.4Ghz Channel",
                    "unique_id": f"gwn_device_{normalised_device_mac}_channel_2_4",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.channel_2_4 }}",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{normalised_device_mac}_channel_5"),
                {
                    "name": "5Ghz Channel",
                    "unique_id": f"gwn_device_{normalised_device_mac}_channel_5",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.channel_5 }}",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{normalised_device_mac}_channel_6"),
                {
                    "name": "6Ghz Channel",
                    "unique_id": f"gwn_device_{normalised_device_mac}_channel_6",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.channel_6 }}",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{normalised_device_mac}_mac"),
                {
                    "name": "MAC",
                    "unique_id": f"gwn_device_{normalised_device_mac}_mac",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.mac }}",
                    "device": device
                }
            ),
        ]

    def _generic_network_payload_to_homeassistant(self, state_topic: str, payload: dict[str, object]) -> list[tuple[str, dict[str, object]]]:
        network_id: str = str(payload.get("id"))
        network_id_int: int = int(network_id)

        network_name: str = str(payload.get('networkName'))
        network_model: str = "GWN Network"
        if network_id_int in self._config.homeassistant.network_name_override:
            network_model = network_name
            network_name = str(self._config.homeassistant.network_name_override[network_id_int])

        device = self._ha_device_block(f"gwn_network_{network_id}", network_name, network_model)

        return [
            (
                self._ha_discovery_topic("sensor", f"gwn_network_{network_id}_name"),
                {
                    "name": "Name",
                    "unique_id": f"gwn_network_{network_id}_name",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.networkName }}",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_network_{network_id}_country"),
                {
                    "name": "Country",
                    "unique_id": f"gwn_network_{network_id}_country",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.countryDisplay }}",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_network_{network_id}_timezone"),
                {
                    "name": "Timezone",
                    "unique_id": f"gwn_network_{network_id}_timezone",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.timezone }}",
                    "device": device
                }
            )
        ]

    @property
    def is_connected(self) -> bool:
        return self._interface.is_connected

    async def connect(self) -> bool:
        return await self._interface.connect()

    async def disconnect(self) -> None:
        return await self._interface.disconnect()

    async def publish_online(self) -> None:
        await self._interface.publish(f"{self._interface.topic}/status", "online", retain=True)

    async def publish_network(self, gwn_network_id: str, gwn_network: dict[str, object]) -> str:
        network_topic = f"{self._interface.topic}/networks/{gwn_network_id}"

        gwn_network_id_int: int = int(gwn_network_id)
        auto_discovery: bool = (self._config.homeassistant.default_network_autodiscovery 
            if gwn_network_id_int not in self._config.homeassistant.network_autodiscovery
            else self._config.homeassistant.network_autodiscovery[gwn_network_id_int]
        )
        await self._interface.publish(f"{network_topic}/state",json.dumps(gwn_network),retain=True)
        if auto_discovery:
            ha_network_payload = self._generic_network_payload_to_homeassistant(f"{network_topic}/state", gwn_network)
            # now actually publish
            for topic, discovery_payload in ha_network_payload:
                await self._interface.publish(topic, json.dumps(discovery_payload), retain=True)

        return network_topic
    
    async def publish_device(self, network_topic: str, device_mac:str, device_payload: dict[str, object]) -> None:
        device_mac = self._strip_mac(device_mac)
        normalised_macs = self._normalise_macs(self._config.homeassistant.device_autodiscovery)
        device_topic = f"{network_topic}/devices/{device_mac}"
        
        auto_discovery: bool = (self._config.homeassistant.default_device_autodiscovery 
            if device_mac not in normalised_macs
            else normalised_macs[device_mac]
        )
        await self._interface.publish(f"{device_topic}/state",json.dumps(device_payload), retain=True)
        if auto_discovery:
            ha_device_payload = self._generic_device_payload_to_homeassistant(f"{device_topic}/state", device_payload)
            # now actually publish
            for topic, discovery_payload in ha_device_payload:
                await self._interface.publish(topic, json.dumps(discovery_payload), retain=True)

    async def publish_ssid(self, network_topic: str, gwn_ssid_id: str, ssid_payload: dict[str, object]) -> None:
        ssid_topic = f"{network_topic}/ssids/{gwn_ssid_id}"
        gwn_ssid_id_int: int = int(gwn_ssid_id)
        
        auto_discovery: bool = (self._config.homeassistant.default_ssid_autodiscovery 
            if gwn_ssid_id_int not in self._config.homeassistant.ssid_autodiscovery 
            else self._config.homeassistant.ssid_autodiscovery[gwn_ssid_id_int]
        )

        await self._interface.publish(f"{ssid_topic}/state",json.dumps(ssid_payload), retain=True)
        if auto_discovery:
            ha_ssid_payload = self._generic_ssid_payload_to_homeassistant(f"{ssid_topic}/state", ssid_payload)
            # now actually publish
            for topic, discovery_payload in ha_ssid_payload:
                await self._interface.publish(topic, json.dumps(discovery_payload), retain=True)
