import logging
import json
from typing import Any

from gwn.constants import Constants
from mqtt.config import HomeAssistantConfig
from mqtt.connection.MqttInterface import MqttInterface

_LOGGER = logging.getLogger(Constants.LOG)

class HomeAssistantMqttClient:

    def __init__(self, config: HomeAssistantConfig, interface: MqttInterface) -> None:
        self._config: HomeAssistantConfig = config
        self._interface: MqttInterface = interface

    def _normalise_macs(self, macs: dict[int | str, Any] ) -> dict[str, Any]:
        normalised: dict[str, Any] = {}
        for mac, enabled in macs.items():
            normalised[self.strip_mac(str(mac))] = enabled
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
    
    def _generic_ssid_payload_to_homeassistant(self, state_topic: str, command_topic: str, payload: dict[str, object], network_id: int, network_name: str, device_data: list[list[str]]) -> list[tuple[str, dict[str, object]]]:
        ssid_id: str = str(payload.get(Constants.SSID_ID))
        ssid_id_int: int = int(ssid_id)
        # Use the SSID name and network name as model unless there was an override then use then
        # use the override as the SSID name and the old SSID name as the model
        ssid_name: str = str(payload.get(Constants.SSID_NAME))
        ssid_model: str = network_name if len(network_name) > 0 else "GWN SSID"
        if ssid_id_int in self._config.ssid_name_override:
            ssid_model = ssid_name
            ssid_name = str(self._config.ssid_name_override[ssid_id_int])
        
        device = self._ha_device_block(f"gwn_ssid_{ssid_id}", ssid_name, ssid_model)

        if network_id in self._config.network_name_override:
            network_name = self._config.network_name_override[network_id]
        if len(network_name) == 0:
            network_name = f"Network ID: {network_id}"

        # now create the device assignment options
        device_assignment: list[tuple[str, dict[str, object]]] = []

        assigned_devices = payload.get(Constants.ASSIGNED_DEVICES)
        assigned_devices = assigned_devices if isinstance(assigned_devices, dict) else {}
        normalised_name_override_macs = self._normalise_macs(self._config.device_name_override)
        
        raw_device_mac_list: list[str] = []
        # first build a list of assigned devices
        for device_info in device_data:
            raw_device_mac:str = device_info[0]
            if len(device_info) == 2:
                device_info.append("")
            device_info[2] = "true" if bool(assigned_devices is not None and raw_device_mac in assigned_devices) else ""
            if bool(device_info[2]):
                raw_device_mac_list.append(raw_device_mac)

        assigned_devices_json = json.dumps(raw_device_mac_list) # this is for knowing which device this is for as part of a round-trip check

        for device_info in device_data:
            # see if the device has a custom name assigned in GWN Manager
            raw_device_mac = device_info[0]
            device_name: str = device_info[1]
            is_assigned: bool = device_info[2].lower() == "true"
            if len(device_name) == 0: # No custom name so use the MAC
                device_name = str(raw_device_mac)
            # Last check, see if the config overrides the name and always use this override in display
            # otherwise use whatever was found previously
            normalised_device_mac = self.strip_mac(raw_device_mac)
            device_name = str(normalised_name_override_macs.get(normalised_device_mac, device_name))
            device_assignment.append(
                (
                    self._ha_discovery_topic("switch", f"gwn_ssid_{ssid_id}_{normalised_device_mac}_device_enable"),
                    {
                        "name": f"Assign {device_name}",
                        "unique_id": f"gwn_ssid_{ssid_id}_{normalised_device_mac}_device_enable",
                        "state_topic": state_topic,
                        "command_topic": command_topic,
                        "value_template": "{{ %s == 1 }}" % int(is_assigned),
                        "payload_on": '{"%s":{"%s":"%s","%s":%s}, "%s": %s}' % (Constants.ACTION, Constants.ACTION, Constants.TOGGLE_DEVICE, Constants.VALUE, json.dumps(list(set([raw_device_mac] + raw_device_mac_list))), Constants.DEVICE_MACS, assigned_devices_json),
                        "payload_off": '{"%s":{"%s":"%s","%s":%s}, "%s": %s}' % (Constants.ACTION, Constants.ACTION, Constants.TOGGLE_DEVICE, Constants.VALUE, json.dumps([mac for mac in raw_device_mac_list if mac != raw_device_mac]), Constants.DEVICE_MACS, assigned_devices_json),
                        "state_on": True,
                        "state_off": False,
                        "device": device
                    }
                )
            )

        return device_assignment + [
            (
                self._ha_discovery_topic("switch", f"gwn_ssid_{ssid_id}_enabled"),
                {
                    "name": "Enabled",
                    "unique_id": f"gwn_ssid_{ssid_id}_enabled",
                    "state_topic": state_topic,
                    "command_topic": command_topic,
                    "value_template": "{{ value_json.%s == 1}}" % Constants.SSID_ENABLE,
                    "payload_on": '{"%s":{"%s":"%s","%s":true}, "%s":%s}' % (Constants.ACTION, Constants.ACTION, Constants.SSID_ENABLE, Constants.VALUE, Constants.DEVICE_MACS, assigned_devices_json),
                    "payload_off": '{"%s":{"%s":"%s","%s":false}, "%s":%s}' % (Constants.ACTION, Constants.ACTION, Constants.SSID_ENABLE, Constants.VALUE, Constants.DEVICE_MACS, assigned_devices_json),
                    "state_on": True,
                    "state_off": False,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("switch", f"gwn_ssid_{ssid_id}_portal"),
                {
                    "name": "Captive Portal",
                    "unique_id": f"gwn_ssid_{ssid_id}_portal",
                    "state_topic": state_topic,
                    "command_topic": command_topic,
                    "value_template": "{{ value_json.%s == 1}}" % Constants.PORTAL_ENABLED,
                    "payload_on": '{"%s":{"%s":"%s","%s":true}, "%s":%s}' % (Constants.ACTION, Constants.ACTION, Constants.PORTAL_ENABLED, Constants.VALUE, Constants.DEVICE_MACS, assigned_devices_json),
                    "payload_off": '{"%s":{"%s":"%s","%s":false}, "%s":%s}' % (Constants.ACTION, Constants.ACTION, Constants.PORTAL_ENABLED, Constants.VALUE, Constants.DEVICE_MACS, assigned_devices_json),
                    "state_on": True,
                    "state_off": False,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("number", f"gwn_ssid_{ssid_id}_vlan"),
                {
                    "name": "VLAN ID",
                    "unique_id": f"gwn_ssid_{ssid_id}_vlan",
                    "state_topic": state_topic,
                    "command_topic": command_topic,
                    "value_template": "{{ value_json.%s if value_json.get('%s') else 'No VLAN' }}" % (Constants.SSID_VLAN_ID, Constants.SSID_VLAN_ENABLED),
                    "command_template": '{"%s":{"%s":"%s","%s":{{ value | int }}}, "%s":%s}' % (Constants.ACTION, Constants.ACTION, Constants.SSID_VLAN_ID, Constants.VALUE, Constants.DEVICE_MACS, assigned_devices_json),
                    "min": 0,
                    "max": 4094,
                    "step": 1,
                    "mode": "box",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("switch", f"gwn_ssid_{ssid_id}_client_isolation_enabled"),
                {
                    "name": "Client Isolation",
                    "unique_id": f"gwn_ssid_{ssid_id}_client_isolation_enabled",
                    "state_topic": state_topic,
                    "command_topic": command_topic,
                    "value_template": "{{ value_json.%s == 1}}" % Constants.CLIENT_ISOLATION_ENABLED,
                    "payload_on": '{"%s":{"%s":"%s","%s":true}, "%s":%s}' % (Constants.ACTION, Constants.ACTION, Constants.CLIENT_ISOLATION_ENABLED, Constants.VALUE, Constants.DEVICE_MACS, assigned_devices_json),
                    "payload_off": '{"%s":{"%s":"%s","%s":false}, "%s":%s}' % (Constants.ACTION, Constants.ACTION, Constants.CLIENT_ISOLATION_ENABLED, Constants.VALUE, Constants.DEVICE_MACS, assigned_devices_json),
                    "state_on": True,
                    "state_off": False,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("switch", f"gwn_ssid_{ssid_id}_enabled_2_4"),
                {
                    "name": "2.4GHz Station",
                    "unique_id": f"gwn_ssid_{ssid_id}_enabled_2_4",
                    "state_topic": state_topic,
                    "command_topic": command_topic,
                    "value_template": "{{ value_json.%s == 1}}" % Constants.GHZ2_4_ENABLED,
                    "payload_on": '{"%s":{"%s":"%s","%s":true}, "%s":%s}' % (Constants.ACTION, Constants.ACTION, Constants.GHZ2_4_ENABLED, Constants.VALUE, Constants.DEVICE_MACS, assigned_devices_json),
                    "payload_off": '{"%s":{"%s":"%s","%s":false}, "%s":%s}' % (Constants.ACTION, Constants.ACTION, Constants.GHZ2_4_ENABLED, Constants.VALUE, Constants.DEVICE_MACS, assigned_devices_json),
                    "state_on": True,
                    "state_off": False,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("switch", f"gwn_ssid_{ssid_id}_enabled_5"),
                {
                    "name": "5GHz Station",
                    "unique_id": f"gwn_ssid_{ssid_id}_enabled_5",
                    "state_topic": state_topic,
                    "command_topic": command_topic,
                    "value_template": "{{ value_json.%s == 1}}" % Constants.GHZ5_ENABLED,
                    "payload_on": '{"%s":{"%s":"%s","%s":true}, "%s":%s}' % (Constants.ACTION, Constants.ACTION, Constants.GHZ5_ENABLED, Constants.VALUE, Constants.DEVICE_MACS, assigned_devices_json),
                    "payload_off": '{"%s":{"%s":"%s","%s":false}, "%s":%s}' % (Constants.ACTION, Constants.ACTION, Constants.GHZ5_ENABLED, Constants.VALUE, Constants.DEVICE_MACS, assigned_devices_json),
                    "state_on": True,
                    "state_off": False,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("switch", f"gwn_ssid_{ssid_id}_enabled_6"),
                {
                    "name": "6GHz Station",
                    "unique_id": f"gwn_ssid_{ssid_id}_enabled_6",
                    "state_topic": state_topic,
                    "command_topic": command_topic,
                    "value_template": "{{ value_json.%s == 1}}" % Constants.GHZ6_ENABLED,
                    "payload_on": '{"%s":{"%s":"%s","%s":true}, "%s":%s}' % (Constants.ACTION, Constants.ACTION, Constants.GHZ6_ENABLED, Constants.VALUE, Constants.DEVICE_MACS, assigned_devices_json),
                    "payload_off": '{"%s":{"%s":"%s","%s":false}, "%s":%s}' % (Constants.ACTION, Constants.ACTION, Constants.GHZ6_ENABLED, Constants.VALUE, Constants.DEVICE_MACS, assigned_devices_json),
                    "state_on": True,
                    "state_off": False,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("text", f"gwn_ssid_{ssid_id}_passphrase"),
                {
                    "name": "WiFi Passphrase",
                    "unique_id": f"gwn_ssid_{ssid_id}_passphrase",
                    "state_topic": state_topic,
                    "command_topic": command_topic,
                    "value_template": "{{ value_json.%s }}" % Constants.SSID_KEY,
                    "command_template": '{"%s":{"%s":"%s","%s":{{ value | tojson }}}, "%s":%s}' % (Constants.ACTION, Constants.ACTION, Constants.SSID_KEY, Constants.VALUE, Constants.DEVICE_MACS, assigned_devices_json),
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("switch", f"gwn_ssid_{ssid_id}_hidden"),
                {
                    "name": "Hide WiFi",
                    "unique_id": f"gwn_ssid_{ssid_id}_hidden",
                    "state_topic": state_topic,
                    "command_topic": command_topic,
                    "value_template": "{{ value_json.%s == 1}}" % Constants.SSID_HIDDEN,
                    "payload_on": '{"%s":{"%s":"%s","%s":true}, "%s":%s}' % (Constants.ACTION, Constants.ACTION, Constants.SSID_HIDDEN, Constants.VALUE, Constants.DEVICE_MACS, assigned_devices_json),
                    "payload_off": '{"%s":{"%s":"%s","%s":false}, "%s":%s}' % (Constants.ACTION, Constants.ACTION, Constants.SSID_HIDDEN, Constants.VALUE, Constants.DEVICE_MACS, assigned_devices_json),
                    "state_on": True,
                    "state_off": False,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_ssid_{ssid_id}_client_count"),
                {
                    "name": "Clients Online",
                    "unique_id": f"gwn_ssid_{ssid_id}_client_count",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.%s | int(0) }}" % Constants.CLIENT_COUNT,
                    "state_class": "measurement",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_ssid_{ssid_id}_network_name"),
                {
                    "name": "Network",
                    "unique_id": f"gwn_ssid_{ssid_id}_network_name",
                    "state_topic": state_topic,
                    "value_template": "{{ %s }}" % json.dumps(network_name),
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("text", f"gwn_ssid_{ssid_id}_ssid_name"),
                {
                    "name": "SSID",
                    "unique_id": f"gwn_ssid_{ssid_id}_ssid_name",
                    "state_topic": state_topic,
                    "command_topic": command_topic,
                    "value_template": "{{ value_json.%s }}" % Constants.SSID_NAME,
                    "command_template": '{"%s":{"%s":"%s","%s":{{ value | tojson }}}, "%s":%s}' % (Constants.ACTION, Constants.ACTION, Constants.SSID_NAME, Constants.VALUE, Constants.DEVICE_MACS, assigned_devices_json),
                    "device": device
                }
            )
        ]

    def _generic_device_payload_to_homeassistant(self, state_topic: str, command_topic: str, payload: dict[str, object], network_id: int, network_name: str, network_names: dict[int, str]) -> list[tuple[str, dict[str, object]]]:
        device_mac = str(payload.get(Constants.MAC))
        normalised_device_mac = self.strip_mac(device_mac)

        # override the names in Home Assistant. This will not change anything underlying, only what is displayed in home assistant
        normalised_name_override_macs = self._normalise_macs(self._config.device_name_override)
        device_model: str = device_mac
        device_name: str = str(payload.get(Constants.NAME))

        # if no name is given, then use the AP type as a name otherwise, use the network name if there is one, otherwise, use 
        # 'GWN Device' as the name
        if len(device_name) == 0:
            device_name = str(payload.get(Constants.AP_TYPE, network_name if len(network_name) > 0 else "GWN Device"))

        # now actually check if the device name was overridden then use the original name as the model
        # if it exists, otherwise the MAC becomes the model and use the override name as the new name
        if normalised_device_mac in normalised_name_override_macs:
            device_model = device_name if len(device_name) > 0 else device_mac
            device_name = str(normalised_name_override_macs[normalised_device_mac])

        # build the list of SSID names and use the overrides if any names have been overriden in the config
        raw_ssids = payload[Constants.SSIDS]
        ssids: list[dict[str, str]] = raw_ssids if isinstance(raw_ssids,list) else []
        ssid_names: list[str] = []
        for ssid in ssids:
            ssid_name = ssid.get(Constants.SSID_NAME)
            ssid_id = ssid.get(Constants.SSID_ID)
            if ssid_name is not None and ssid_id is not None:
                ssid_names.append(str(self._config.ssid_name_override.get(ssid_id,ssid_name)))

       


        found_names: list[str] = []
        for id in network_names:
            new_network_name = network_names[id]
            # now see if the network name was overriden in the config. If it was, then use the overridden name otherwise
            # see if it has a name. If it doesnt, then use the normal name
            if id in self._config.network_name_override:
                new_network_name = self._config.network_name_override[id]
            if new_network_name in found_names:
                new_network_name = f"{new_network_name} - ({id})"
            else:
                found_names.append(new_network_name)
            if network_id == id:
                network_name = new_network_name
            network_names[id] = new_network_name
        

        device = self._ha_device_block(f"gwn_device_{normalised_device_mac}", device_name, device_model)

        return [
            (
                self._ha_discovery_topic("button", f"gwn_device_{normalised_device_mac}_reboot"),
                {
                    "name": "Reboot",
                    "unique_id": f"gwn_device_{normalised_device_mac}_reboot",
                    "payload_press": '{"%s": "%s"}' % (Constants.ACTION, Constants.REBOOT),
                    "command_topic": command_topic,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("update", f"gwn_device_{normalised_device_mac}_update_firmware"),
                {
                    "name": "Update Firmware",
                    "unique_id": f"gwn_device_{normalised_device_mac}_update_firmware",
                    "value_template": '{{ {"installed_version": value_json.%s,"latest_version": value_json.%s} | tojson }}' % (Constants.CURRENT_FIRMWARE, Constants.NEW_FIRMWARE),
                    "payload_install": '{"%s": "%s"}' % (Constants.ACTION, Constants.UPDATE_FIRMWARE),
                    "state_topic": state_topic,
                    "command_topic": command_topic,
                    "title": "Device Firmware",
                    "enabled_by_default": False,
                    "entity_category": "config",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("button", f"gwn_device_{normalised_device_mac}_reset"),
                {
                    "name": "Reset",
                    "unique_id": f"gwn_device_{normalised_device_mac}_reset",
                    "payload_press": '{"%s": "%s"}' % (Constants.ACTION, Constants.RESET),
                    "command_topic": command_topic,
                    "enabled_by_default": False,
                    "entity_category": "config",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("select", f"gwn_device_{normalised_device_mac}_network_name"),
                {
                    "name": "Network",
                    "unique_id": f"gwn_device_{normalised_device_mac}_network_name",
                    "state_topic": state_topic,
                    "command_topic": command_topic,
                    "value_template": "{{ %s }}" % json.dumps(network_name),
                    "options": list(network_names.values()),
                    "command_template": '{"%s":"%s","%s":%s[{{ value | tojson }}]}'% (Constants.ACTION, Constants.NETWORK_NAME, Constants.VALUE, json.dumps({name: network_id for network_id, name in network_names.items()})),
                    "entity_category": "config",
                    "enabled_by_default": True,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("binary_sensor", f"gwn_device_{normalised_device_mac}_status"),
                {
                    "name": "Status",
                    "unique_id": f"gwn_device_{normalised_device_mac}_status",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.%s }}" % Constants.STATUS,
                    "payload_on": True,
                    "payload_off": False,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("switch", f"gwn_device_{normalised_device_mac}_wireless"),
                {
                    "name": "Wireless",
                    "unique_id": f"gwn_device_{normalised_device_mac}_wireless",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.%s == 1}}" % Constants.WIRELESS,
                    "command_topic": command_topic,
                    "payload_on": '{"%s":"%s","%s":true}' % (Constants.ACTION, Constants.WIRELESS, Constants.VALUE),
                    "payload_off": '{"%s":"%s","%s":false}' % (Constants.ACTION, Constants.WIRELESS, Constants.VALUE),
                    "state_on": True,
                    "state_off": False,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{normalised_device_mac}_ipv4"),
                {
                    "name": "IPv4",
                    "unique_id": f"gwn_device_{normalised_device_mac}_ipv4",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.%s }}" % Constants.IPV4,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{normalised_device_mac}_ipv6"),
                {
                    "name": "IPv6",
                    "unique_id": f"gwn_device_{normalised_device_mac}_ipv6",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.%s }}" % Constants.IPV6,
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
                    "entity_category": "config",
                    "enabled_by_default": True,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{normalised_device_mac}_firmware_new"),
                {
                    "name": "Available Firmware",
                    "unique_id": f"gwn_device_{normalised_device_mac}_firmware_new",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.%s }}" % Constants.NEW_FIRMWARE,
                    "entity_category": "config",
                    "enabled_by_default": True,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{normalised_device_mac}_cpu_usage"),
                {
                    "name": "CPU Usage",
                    "unique_id": f"gwn_device_{normalised_device_mac}_cpu_usage",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.%s | replace('%%', '') | int(0) }}" % Constants.CPU_USAGE,
                    "unit_of_measurement": "%",
                    "state_class": "measurement",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{normalised_device_mac}_temperature"),
                {
                    "name": "Temperature",
                    "unique_id": f"gwn_device_{normalised_device_mac}_temperature",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.%s | replace('℃', '') | replace('°C', '') | int(0) }}" % Constants.TEMPERATURE,
                    "unit_of_measurement": "°C",
                    "state_class": "measurement",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{normalised_device_mac}_ssid_names"),
                {
                    "name": "SSIDs",
                    "unique_id": f"gwn_device_{normalised_device_mac}_ssid_names",
                    "state_topic": state_topic,
                    "value_template": "{{ %s | join(', ') if %s else 'No SSIDs' }}" % (json.dumps(ssid_names), json.dumps(ssid_names)),
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{normalised_device_mac}_uptime"),
                {
                    "name": "Up Time",
                    "unique_id": f"gwn_device_{normalised_device_mac}_uptime",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.%s | int(0) }}" % Constants.UP_TIME,
                    "unit_of_measurement": "s",
                    "state_class": "measurement",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{normalised_device_mac}_channel_2_4"),
                {
                    "name": "Current 2.4GHz Channel",
                    "unique_id": f"gwn_device_{normalised_device_mac}_channel_2_4",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.%s | int(0) }}" % Constants.CHANNEL_2_4,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{normalised_device_mac}_channel_5"),
                {
                    "name": "Current 5GHz Channel",
                    "unique_id": f"gwn_device_{normalised_device_mac}_channel_5",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.%s | int(0) }}" % Constants.CHANNEL_5,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{normalised_device_mac}_channel_6"),
                {
                    "name": "Current 6GHz Channel",
                    "unique_id": f"gwn_device_{normalised_device_mac}_channel_6",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.%s | int(0) }}" % Constants.CHANNEL_6,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("number", f"gwn_device_{normalised_device_mac}_ap_2g4_channel"),
                {
                    "name": "2.4Ghz Channel",
                    "unique_id": f"gwn_device_{normalised_device_mac}_ap_2g4_channel",
                    "state_topic": state_topic,
                    "command_topic": command_topic,
                    "value_template": "{{ value_json.%s | int(0) }}" % Constants.AP_2G4_CHANNEL,
                    "command_template": '{"%s":"%s","%s":{{ value | int }}}' % (Constants.ACTION, Constants.AP_2G4_CHANNEL, Constants.VALUE),
                    "min": 0,
                    "max": 13,
                    "step": 1,
                    "mode": "box",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("number", f"gwn_device_{normalised_device_mac}_ap_5g_channel"),
                {
                    "name": "5Ghz Channel",
                    "unique_id": f"gwn_device_{normalised_device_mac}_ap_5g_channel",
                    "state_topic": state_topic,
                    "command_topic": command_topic,
                    "value_template": "{{ 0 if value_json.%s | int(0) < 36 else value_json.%s | int(0) }}" % (Constants.AP_5G_CHANNEL, Constants.AP_5G_CHANNEL),
                    "command_template": '{"%s":"%s","%s":{{ value | int }}}' % (Constants.ACTION, Constants.AP_5G_CHANNEL, Constants.VALUE),
                    "min": 0,
                    "max": 165,
                    "step": 1,
                    "mode": "box",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("number", f"gwn_device_{normalised_device_mac}_ap_6g_channel"),
                {
                    "name": "6Ghz Channel",
                    "unique_id": f"gwn_device_{normalised_device_mac}_ap_6g_channel",
                    "state_topic": state_topic,
                    "command_topic": command_topic,
                    "value_template": "{{ value_json.%s | int(0) }}" % Constants.AP_6G_CHANNEL,
                    "command_template": '{"%s":"%s","%s":{{ value | int }}}' % (Constants.ACTION, Constants.AP_6G_CHANNEL, Constants.VALUE),
                    "min": 0,
                    "max": 177,
                    "step": 1,
                    "mode": "box",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_device_{normalised_device_mac}_mac"),
                {
                    "name": "MAC",
                    "unique_id": f"gwn_device_{normalised_device_mac}_mac",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.%s }}" % Constants.MAC,
                    "entity_category": "config",
                    "enabled_by_default": True,
                    "device": device
                }
            ),
        ]

    def _generic_network_payload_to_homeassistant(self, state_topic: str, command_topic: str, payload: dict[str, object]) -> list[tuple[str, dict[str, object]]]:
        network_id: str = str(payload.get(Constants.NETWORK_ID))
        network_id_int: int = int(network_id)

        network_name: str = str(payload.get(Constants.NETWORK_NAME))
        network_model: str = "GWN Network"
        if network_id_int in self._config.network_name_override:
            network_model = network_name
            network_name = str(self._config.network_name_override[network_id_int])

        device = self._ha_device_block(f"gwn_network_{network_id}", network_name, network_model)

        return [
            (
                self._ha_discovery_topic("text", f"gwn_network_{network_id}_name"),
                {
                    "name": "Name",
                    "unique_id": f"gwn_network_{network_id}_name",
                    "state_topic": state_topic,
                    "command_topic": command_topic,
                    "value_template": "{{ value_json.%s }}" % Constants.NETWORK_NAME,
                    "command_template": '{"%s":"%s","%s":{{ value | tojson }}}' % (Constants.ACTION, Constants.NETWORK_NAME, Constants.VALUE),
                    "device": device,
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_network_{network_id}_country"),
                {
                    "name": "Country",
                    "unique_id": f"gwn_network_{network_id}_country",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.%s }}" % Constants.COUNTRY_DISPLAY,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", f"gwn_network_{network_id}_timezone"),
                {
                    "name": "Timezone",
                    "unique_id": f"gwn_network_{network_id}_timezone",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.%s }}" % Constants.TIMEZONE,
                    "device": device
                }
            )
        ]

    def _generic_application_payload_to_homeassistant(self, state_topic: str, command_topic: str, payload: dict[str, object]) -> list[tuple[str, dict[str, object]]]:
        device = self._ha_device_block("gwn_to_mqtt", "GWN to MQTT Bridge", "GWN Manager to MQTT")
        device["manufacturer"] = "GWNtoMQTT"
        return [
            (
                self._ha_discovery_topic("update", "gwn_to_mqtt_update_version"),
                {
                    "name": "Update Application",
                    "unique_id": "gwn_to_mqtt_update_version",
                    "value_template": '{{ {"installed_version": value_json.%s,"latest_version": value_json.%s} | tojson }}'  % (Constants.CURRENT_VERSION, Constants.NEW_VERSION),
                    "payload_install": '{"%s": "%s"}' % (Constants.ACTION, Constants.UPDATE_VERSION),
                    "state_topic": state_topic,
                    "command_topic": command_topic,
                    "title": "Application Update",
                    "enabled_by_default": True,
                    "entity_category": "config",
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("sensor", "gwn_to_mqtt_new_version"),
                {
                    "name": "Available Version",
                    "unique_id": "gwn_to_mqtt_new_version",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.%s }}" % Constants.NEW_VERSION,
                    "entity_category": "config",
                    "enabled_by_default": True,
                    "device": device
                }
            ),
                        (
                self._ha_discovery_topic("sensor", "gwn_to_mqtt_version"),
                {
                    "name": "Current Version",
                    "unique_id": "gwn_to_mqtt_version",
                    "state_topic": state_topic,
                    "value_template": "{{ value_json.%s }}" % Constants.CURRENT_VERSION,
                    "entity_category": "config",
                    "enabled_by_default": True,
                    "device": device
                }
            ),
            (
                self._ha_discovery_topic("button", "gwn_to_mqtt_update_restart"),
                {
                    "name": "Restart",
                    "unique_id": "gwn_to_mqtt_update_restart",
                    "payload_press": '{"%s": "%s"}' % (Constants.ACTION, Constants.RESTART),
                    "command_topic": command_topic,
                    "device": device
                }
            )
        ]

    def strip_mac(self, mac: str) -> str:
        return mac.replace(":", "").replace("-","").lower()

    async def publish_online(self, state_topic: str, application_topic: str, payload: dict[str, object]) -> None:
        command_topic: str = f"{application_topic}/{Constants.SET}"
        if self._config.application_autodiscovery:
            ha_application_payload = self._generic_application_payload_to_homeassistant(state_topic, command_topic, payload)
            for topic, discovery_payload in ha_application_payload:
                await self._interface.publish(topic, json.dumps(discovery_payload), retain=True)


    async def publish_network(self, state_topic: str, network_topic: str, gwn_network_id: int, gwn_network: dict[str, object]) -> None:

        auto_discovery: bool = (self._config.default_network_autodiscovery 
            if gwn_network_id not in self._config.network_autodiscovery
            else self._config.network_autodiscovery[gwn_network_id]
        )
        command_topic: str = f"{network_topic}/{Constants.SET}"
        if auto_discovery:
            ha_network_payload = self._generic_network_payload_to_homeassistant(state_topic, command_topic, gwn_network)
            # now actually publish
            for topic, discovery_payload in ha_network_payload:
                await self._interface.publish(topic, json.dumps(discovery_payload), retain=True)

    async def publish_device(self, state_topic: str, device_topic: str, network_names: dict[int, str], network_id: int, network_name: str, device_mac:str, device_payload: dict[str, object]) -> None:
        normalised_macs = self._normalise_macs(self._config.device_autodiscovery)
        auto_discovery: bool = (self._config.default_device_autodiscovery 
            if device_mac not in normalised_macs
            else normalised_macs[device_mac]
        )
        if auto_discovery:
            command_topic: str = f"{device_topic}/{Constants.SET}"
            ha_device_payload = self._generic_device_payload_to_homeassistant(state_topic, command_topic, device_payload, network_id, network_name, network_names)
            # now actually publish
            for topic, discovery_payload in ha_device_payload:
                await self._interface.publish(topic, json.dumps(discovery_payload), retain=True)

    async def publish_ssid(self, network_topic: str, network_id: int, network_name: str, state_topic: str, devices: list[list[str]], gwn_ssid_id: int, ssid_topic: str, ssid_payload: dict[str, object]) -> None:
        auto_discovery: bool = (self._config.default_ssid_autodiscovery 
            if gwn_ssid_id not in self._config.ssid_autodiscovery 
            else self._config.ssid_autodiscovery[gwn_ssid_id]
        )
        
        if auto_discovery:
            command_topic: str = f"{ssid_topic}/{Constants.SET}"
            ha_ssid_payload = self._generic_ssid_payload_to_homeassistant(state_topic, command_topic, ssid_payload, network_id, network_name, devices)
            # now actually publish
            for topic, discovery_payload in ha_ssid_payload:
                await self._interface.publish(topic, json.dumps(discovery_payload), retain=True)
