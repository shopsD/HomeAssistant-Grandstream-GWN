import logging
import json

from gwn.constants import Constants
from mqtt.config import MqttConfig, MqttPayloadFormat
from mqtt.connection.MqttInterface import MqttInterface

_LOGGER = logging.getLogger(Constants.LOG)

class MqttClient:
    def __init__(self, config: MqttConfig) -> None:
        self._config = config
        self._interface = MqttInterface(config)

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
        ssid_id: str = str(payload.get("ssidName"))
        device = self._ha_device_block(f"gwn_ssid_{ssid_id}",f"SSID {ssid_id}", "GWN SSID")

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
                    "value_template": "{{ value_json.ssidVlanid }}",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_ssid_{ssid_id}_assigned_names"),
                {
                    "name": "Devices",
                    "unique_id": f"gwn_ssid_{ssid_id}_devices",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.assignedDevices | map(attribute='name') | join(', ') }}",
                    "device": device
                }
            ),
        ]

    def _generic_device_payload_to_homeassistant(self, state_topic: str, payload: dict[str, object]) -> list[tuple[str, dict[str, object]]]:
        device_mac = str(payload.get("mac"))
        device = self._ha_device_block(f"gwn_device_{device_mac}", str(payload.get("name") or device_mac), str(payload.get("apType", "GWN Device")))

        return [
            (
                self._ha_discovery_topic("binary_sensor", f"gwn_device_{device_mac}_status"),
                {
                    "name": "Status",
                    "unique_id": f"gwn_device_{device_mac}_status",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.status }}",
                    "payload_on": True,
                    "payload_off": False,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{device_mac}_ip"),
                {
                    "name": "IP",
                    "unique_id": f"gwn_device_{device_mac}_ip",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.ip }}",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{device_mac}_firmware"),
                {
                    "name": "Firmware",
                    "unique_id": f"gwn_device_{device_mac}_firmware",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.versionFirmware }}",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{device_mac}_firmware_new"),
                {
                    "name": "Available Firmware",
                    "unique_id": f"gwn_device_{device_mac}_firmware_new",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.newFirmware }}",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{device_mac}_temperature"),
                {
                    "name": "Temperature",
                    "unique_id": f"gwn_device_{device_mac}_temperature",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.temperature }}",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{device_mac}_ssid_names"),
                {
                    "name": "SSIDs",
                    "unique_id": f"gwn_device_{device_mac}_ssid_names",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.ssids | map(attribute='ssidName') | join(', ') }}",
                    "device": device
                }
            )
        ]

    def _generic_network_payload_to_homeassistant(self, state_topic: str, payload: dict[str, object]) -> list[tuple[str, dict[str, object]]]:
        network_id: str = str(payload.get("id"))
        device = self._ha_device_block(f"gwn_network_{network_id}", f"{payload.get('networkName')}", "GWN Network")

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
        payload_format: MqttPayloadFormat = MqttPayloadFormat.BOTH if gwn_network_id_int not in self._config.network_payload else self._config.network_payload[gwn_network_id_int]
        if payload_format != MqttPayloadFormat.HOMEASSISTANT:
            await self._interface.publish(f"{network_topic}/state",json.dumps(gwn_network),retain=True)
        if payload_format != MqttPayloadFormat.GENERIC:
            ha_network_payload = self._generic_network_payload_to_homeassistant(f"{network_topic}/state", gwn_network)
            await self._interface.publish(f"{network_topic}/homeassistant/state",json.dumps(ha_network_payload),retain=True)
        return network_topic
    
    async def publish_device(self, network_topic: str, device_mac:str, device_payload: dict[str, object]) -> None:
        device_topic = f"{network_topic}/devices/{device_mac}"
        
        payload_format: MqttPayloadFormat = MqttPayloadFormat.BOTH if device_mac not in self._config.device_payload else self._config.device_payload[device_mac]
        if payload_format != MqttPayloadFormat.HOMEASSISTANT:
            await self._interface.publish(f"{device_topic}/state",json.dumps(device_payload), retain=True)
        if payload_format != MqttPayloadFormat.GENERIC:
            ha_device_payload = self._generic_device_payload_to_homeassistant(f"{device_topic}/state", device_payload)
            await self._interface.publish(f"{device_topic}/homeassistant/state",json.dumps(ha_device_payload), retain=True)

    async def publish_ssid(self, network_topic: str, gwn_ssid_id: str, ssid_payload: dict[str, object]) -> None:
        ssid_topic = f"{network_topic}/ssids/{gwn_ssid_id}"
        gwn_ssid_id_int: int = int(gwn_ssid_id)
        payload_format: MqttPayloadFormat = MqttPayloadFormat.BOTH if gwn_ssid_id_int not in self._config.ssid_payload else self._config.ssid_payload[gwn_ssid_id_int]
        if payload_format != MqttPayloadFormat.HOMEASSISTANT:
            await self._interface.publish(f"{ssid_topic}/state",json.dumps(ssid_payload), retain=True)
        if payload_format != MqttPayloadFormat.GENERIC:
            ha_ssid_payload = self._generic_ssid_payload_to_homeassistant(f"{ssid_topic}/state", ssid_payload)
            await self._interface.publish(f"{ssid_topic}/homeassistant/state",json.dumps(ha_ssid_payload), retain=True)
