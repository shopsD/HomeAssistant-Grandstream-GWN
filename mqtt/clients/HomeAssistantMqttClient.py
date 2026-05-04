import logging
import json
from typing import Any

from gwn.constants import Constants
from mqtt.clients.MqttPublisherClient import MqttPublisherClient
from mqtt.config import HomeAssistantConfig

_LOGGER = logging.getLogger(Constants.LOG)

class HomeAssistantMqttClient(MqttPublisherClient):

    def __init__(self, config: HomeAssistantConfig) -> None:
        self._config: HomeAssistantConfig = config
        self._application_published: bool = False
        self._networks_published: set[str] = set()
        self._devices_published: set[str] = set()
        self._ssids_published: set[str] = set()

    def _normalise_macs(self, macs: dict[int | str, Any] ) -> dict[str, Any]:
        normalised: dict[str, Any] = {}
        for mac, enabled in macs.items():
            normalised[MqttPublisherClient.strip_mac(str(mac))] = enabled
        return normalised

    def _ha_device_block(self, identifier: str, name: str, model: str) -> dict[str, object]:
        return {
            "identifiers": [identifier],
            "name": name,
            "manufacturer": "Grandstream",
            "model": model
        }

    def _ha_discovery_topic(self, component: str, object_id: str) -> str:
        return f"{self._config.discovery_topic}/{component}/{object_id}/{Constants.CONFIG}"

    def _create_switch_payload(self, device: dict[str, object], unique_id: str, name: str, state_topic: str, command_topic:str, payload_key: str, assigned_devices_json: str | None = None ) -> tuple[str, dict[str, object]]:
        
        payload_on: str = '{"%s":"%s","%s":true}' % (Constants.ACTION, payload_key, Constants.VALUE)
        payload_off: str = '{"%s":"%s","%s":false}' % (Constants.ACTION, payload_key, Constants.VALUE)
        if assigned_devices_json is not None:
            payload_on = '{"%s":%s, "%s":%s}' % (Constants.ACTION, payload_on, Constants.DEVICE_MACS, assigned_devices_json)
            payload_off = '{"%s":%s, "%s":%s}' % (Constants.ACTION, payload_off, Constants.DEVICE_MACS, assigned_devices_json)
        
        return (
            self._ha_discovery_topic("switch", unique_id),
            {
                "name": name,
                "unique_id": unique_id,
                "state_topic": state_topic,
                "command_topic": command_topic,
                "value_template": "{{ value_json.%s == 1}}" % payload_key,
                "payload_on": payload_on,
                "payload_off": payload_off,
                "state_on": True,
                "state_off": False,
                "device": device
            }
        )

    def _create_number_payload(self, device: dict[str, object], unique_id: str, name: str, state_topic: str, command_topic:str, payload_key: str, min: int, max: int, value_template: str | None = None, assigned_devices_json: str | None = None ) -> tuple[str, dict[str, object]]:
        
        command_template: str = '{"%s":"%s","%s":{{ value | int }}}' % (Constants.ACTION, payload_key, Constants.VALUE)
        if assigned_devices_json is not None:
            command_template = '{"%s":%s, "%s":%s}' % (Constants.ACTION, command_template, Constants.DEVICE_MACS, assigned_devices_json)
        if value_template is None:
            value_template =  "{{ value_json.%s | int(0) }}" % payload_key

        return (
            self._ha_discovery_topic("number", unique_id),
            {
                "name": name,
                "unique_id": unique_id,
                "state_topic": state_topic,
                "command_topic": command_topic,
                "value_template": value_template,
                "command_template": command_template,
                "min": min,
                "max": max,
                "step": 1,
                "mode": "box",
                "device": device
            }
        )

    def _create_text_payload(self, device: dict[str, object], unique_id: str, name: str, state_topic: str, command_topic:str, payload_key: str, assigned_devices_json: str | None = None ) -> tuple[str, dict[str, object]]:
        command_template: str = '{"%s":"%s","%s":{{ value | tojson }}}' % (Constants.ACTION, payload_key, Constants.VALUE)
        if assigned_devices_json is not None:
            command_template = '{"%s":%s, "%s":%s}' % (Constants.ACTION, command_template, Constants.DEVICE_MACS, assigned_devices_json)

        return (
            self._ha_discovery_topic("text", unique_id),
            {
                "name": name,
                "unique_id": unique_id,
                "state_topic": state_topic,
                "command_topic": command_topic,
                "value_template": "{{ value_json.%s }}" % payload_key,
                "command_template": command_template,
                "device": device
            }
        )

    def _create_button_payload(self, device: dict[str, object], unique_id: str, name: str, command_topic:str, payload_key: str, enabled_by_default: bool | None = None, is_config: bool = False, assigned_devices_json: str | None = None ) -> tuple[str, dict[str, object]]:
        payload_press: str = '{"%s": "%s"}' % (Constants.ACTION, payload_key)
        if assigned_devices_json is not None:
            payload_press = '{"%s":%s, "%s":%s}' % (Constants.ACTION, payload_press, Constants.DEVICE_MACS, assigned_devices_json)

        payload: dict[str, object] = {
            "name": name,
            "unique_id": unique_id,
            "payload_press": payload_press,
            "command_topic": command_topic,
            "device": device
        }

        if is_config:
            payload["entity_category"] = "config"
        if enabled_by_default is not None:
            payload["enabled_by_default"] = enabled_by_default

        return (self._ha_discovery_topic("button", unique_id),payload)

    def _create_select_payload(self, device: dict[str, object], unique_id: str, name: str, state_topic: str, command_topic:str, payload_key: str, select_options: list[str], command_options: dict[str, Any], value_template: str | None = None, enabled_by_default: bool | None = None, is_config: bool = False, assigned_devices_json: str | None = None ) -> tuple[str, dict[str, object]]:
        
        command_template: str = '{"%s":"%s","%s":%s[{{ value | tojson }}]}'% (Constants.ACTION, payload_key, Constants.VALUE, json.dumps(command_options))
        if assigned_devices_json is not None:
            command_template = '{"%s":%s, "%s":%s}' % (Constants.ACTION, command_template, Constants.DEVICE_MACS, assigned_devices_json)
        
        if value_template is None:
            value_template =  "{{ value_json.%s }}" % payload_key

        payload: dict[str, object] = {
                "name": name,
                "unique_id": unique_id,
                "state_topic": state_topic,
                "command_topic": command_topic,
                "value_template": value_template,
                "options": select_options,
                "command_template": command_template,
                "device": device
            }

        if is_config:
            payload["entity_category"] = "config"
        if enabled_by_default is not None:
            payload["enabled_by_default"] = enabled_by_default

        return (self._ha_discovery_topic("select", unique_id), payload)
    
    def _create_update_payload(self, device: dict[str, object], unique_id: str, name: str, state_topic: str, command_topic:str, title: str, payload_key: str, payload_key_current: str, payload_key_new: str, enabled_by_default: bool | None = None, is_config: bool = False, assigned_devices_json: str | None = None ) -> tuple[str, dict[str, object]]:
        payload_install: str = '{"%s": "%s"}' % (Constants.ACTION, payload_key)

        if assigned_devices_json is not None: # currently unused. Possibly useful if creating an Apply button
            payload_install = '{"%s":%s, "%s":%s}' % (Constants.ACTION, payload_install, Constants.DEVICE_MACS, assigned_devices_json)
        
        payload: dict[str, object] = {
            "name": name,
            "unique_id": unique_id,
            "value_template": '{{ {"installed_version": value_json.%s,"latest_version": value_json.%s} | tojson }}' % (payload_key_current, payload_key_new),
            "payload_install": payload_install,
            "state_topic": state_topic,
            "command_topic": command_topic,
            "title": title,
            "device": device
        }

        if is_config:
            payload["entity_category"] = "config"
        if enabled_by_default is not None:
            payload["enabled_by_default"] = enabled_by_default
        return (self._ha_discovery_topic("update", unique_id),payload)

    def _create_sensor_payload(self, device: dict[str, object], unique_id: str, name: str, state_topic: str, payload_key_template: str, enabled_by_default: bool | None = None, is_config: bool = False, payload_is_template: bool = False) -> tuple[str, dict[str, object]]:
        
        if not payload_is_template:
            payload_key_template = "{{ value_json.%s }}" % payload_key_template

        payload: dict[str, object] = {
            "name": name,
            "unique_id": unique_id,
            "state_topic": state_topic,
            "value_template": payload_key_template,
            "device": device
        }
        if is_config:
            payload["entity_category"] = "config"
        if enabled_by_default is not None:
            payload["enabled_by_default"] = enabled_by_default
        return (self._ha_discovery_topic("sensor", unique_id),payload)

    def _create_numeric_sensor_payload(self, device: dict[str, object], unique_id: str, name: str, state_topic: str, payload_key_template: str, measurement_unit: str | None = None, enabled_by_default: bool | None = None, is_config: bool = False, payload_is_template: bool = False ) -> tuple[str, dict[str, object]]:
        
        if not payload_is_template:
            payload_key_template = "{{ value_json.%s | int(0) }}" % payload_key_template

        payload = self._create_sensor_payload(device, unique_id, name, state_topic, payload_key_template, enabled_by_default, is_config, payload_is_template)
        payload[1]["state_class"] = "measurement"
        payload[1]["value_template"] = payload_key_template

        if measurement_unit is not None:
            payload[1]["unit_of_measurement"] = measurement_unit

        return payload

    def _create_binary_sensor_payload(self, device: dict[str, object], unique_id: str, name: str, state_topic: str, payload_key_template: str, enabled_by_default: bool | None = None, is_config: bool = False, payload_is_template: bool = False ) -> tuple[str, dict[str, object]]:
        
        if not payload_is_template:
            payload_key_template = "{{ value_json.%s }}" % payload_key_template

        payload: dict[str, object] = {
            "name": name,
            "unique_id": unique_id,
            "state_topic": state_topic,
            "value_template": payload_key_template,
            "payload_on": True,
            "payload_off": False,
            "device": device
        }
        if is_config:
            payload["entity_category"] = "config"
        if enabled_by_default is not None:
            payload["enabled_by_default"] = enabled_by_default

        return (self._ha_discovery_topic("binary_sensor", unique_id),payload)


    def _create_device_ssid_payload(self, state_topic: str, command_topic: str, payload: dict[str, object], device_data: dict[str, str], is_readonly: bool) -> list[tuple[str, dict[str, object]]]:
        ssid_id: str = str(payload.get(Constants.SSID_ID))
        ssid_id_int: int = int(ssid_id)
        # Use the SSID name and network name as model unless there was an override then use then
        # use the override as the SSID name and the old SSID name as the model
        ssid_name: str = str(payload.get(Constants.SSID_NAME))
        network_name: str = str(payload.get(Constants.NETWORK_NAME))
        ssid_model: str = network_name if len(network_name) > 0 else "GWN SSID"
        if ssid_id_int in self._config.ssid_name_override:
            ssid_model = ssid_name
            ssid_name = str(self._config.ssid_name_override[ssid_id_int])
        ssid_payload_id: str = f"gwn_ssid_{ssid_id}"
        device = self._ha_device_block(ssid_payload_id, ssid_name, ssid_model)

        network_id: int = int(str(payload.get(Constants.NETWORK_ID)))
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
        local_device_data: dict[str, str] = {} # dont modify existing due to changing device info
        for data_device_mac, data_device_name in device_data.items():

            if assigned_devices is not None and data_device_mac in assigned_devices:
                raw_device_mac_list.append(data_device_mac)
            local_device_data[data_device_mac] = data_device_name

        hide_ssid_passphrase: bool = payload[Constants.SSID_KEY] is None # it is None if the config has it excluded or it is set to Open (if Open, dont allow setting SSID Key here either)
        assigned_devices_json = json.dumps(raw_device_mac_list) # this is for knowing which device this is for as part of a round-trip check

        for raw_device_mac, device_name in local_device_data.items():
            # see if the device has a custom name assigned in GWN Manager
            if len(device_name) == 0: # No custom name so use the MAC
                device_name = str(raw_device_mac)
            # Last check, see if the config overrides the name and always use this override in display
            # otherwise use whatever was found previously
            normalised_device_mac = MqttPublisherClient.strip_mac(raw_device_mac)
            device_name = str(normalised_name_override_macs.get(normalised_device_mac, device_name))
            if is_readonly:
                device_assignment.append(self._create_binary_sensor_payload(device, f"{ssid_payload_id}_{normalised_device_mac}_device_enable", f"Assign {device_name}", state_topic, "{{ %s in value_json.%s }}" % (json.dumps(raw_device_mac), Constants.ASSIGNED_DEVICES), None, False, True))
            else:
                device_assignment.append(
                    (
                        self._ha_discovery_topic("switch", f"{ssid_payload_id}_{normalised_device_mac}_device_enable"),
                        {
                            "name": f"Assign {device_name}",
                            "unique_id": f"{ssid_payload_id}_{normalised_device_mac}_device_enable",
                            "state_topic": state_topic,
                            "command_topic": command_topic,
                            "value_template": "{{ %s in value_json.%s }}" % (json.dumps(raw_device_mac), Constants.ASSIGNED_DEVICES),
                            "payload_on": '{"%s":{"%s":"%s","%s":%s}, "%s": %s}' % (Constants.ACTION, Constants.ACTION, Constants.TOGGLE_DEVICE, Constants.VALUE, json.dumps(list(set([raw_device_mac] + raw_device_mac_list))), Constants.DEVICE_MACS, assigned_devices_json),
                            "payload_off": '{"%s":{"%s":"%s","%s":%s}, "%s": %s}' % (Constants.ACTION, Constants.ACTION, Constants.TOGGLE_DEVICE, Constants.VALUE, json.dumps([mac for mac in raw_device_mac_list if mac != raw_device_mac]), Constants.DEVICE_MACS, assigned_devices_json),
                            "state_on": True,
                            "state_off": False,
                            "device": device
                        }
                    )
                )

        return device_assignment + [
            (self._create_binary_sensor_payload(device, f"{ssid_payload_id}_enabled", "Enabled", state_topic, Constants.SSID_ENABLE) if is_readonly else self._create_switch_payload(device, f"{ssid_payload_id}_enabled", "Enabled", state_topic, command_topic, Constants.SSID_ENABLE, assigned_devices_json)),
            (self._create_binary_sensor_payload(device, f"{ssid_payload_id}_portal", "Captive Portal", state_topic, Constants.PORTAL_ENABLED) if is_readonly else self._create_switch_payload(device, f"{ssid_payload_id}_portal", "Captive Portal", state_topic, command_topic, Constants.PORTAL_ENABLED, assigned_devices_json)),
            (self._create_binary_sensor_payload(device, f"{ssid_payload_id}_client_isolation_enabled", "Client Isolation", state_topic, Constants.CLIENT_ISOLATION_ENABLED) if is_readonly else self._create_switch_payload(device, f"{ssid_payload_id}_client_isolation_enabled", "Client Isolation", state_topic, command_topic, Constants.CLIENT_ISOLATION_ENABLED, assigned_devices_json)),
            (self._create_binary_sensor_payload(device, f"{ssid_payload_id}_enabled_2_4", "2.4GHz Station", state_topic, Constants.GHZ2_4_ENABLED) if is_readonly else self._create_switch_payload(device, f"{ssid_payload_id}_enabled_2_4", "2.4GHz Station", state_topic, command_topic, Constants.GHZ2_4_ENABLED, assigned_devices_json)),
            (self._create_binary_sensor_payload(device, f"{ssid_payload_id}_enabled_5", "5GHz Station", state_topic, Constants.GHZ5_ENABLED) if is_readonly else self._create_switch_payload(device, f"{ssid_payload_id}_enabled_5", "5GHz Station", state_topic, command_topic, Constants.GHZ5_ENABLED, assigned_devices_json)),
            (self._create_binary_sensor_payload(device, f"{ssid_payload_id}_enabled_6", "6GHz Station", state_topic, Constants.GHZ6_ENABLED) if is_readonly else self._create_switch_payload(device, f"{ssid_payload_id}_enabled_6", "6GHz Station", state_topic, command_topic, Constants.GHZ6_ENABLED, assigned_devices_json)),
            (self._create_binary_sensor_payload(device, f"{ssid_payload_id}_hidden", "Hide WiFi", state_topic, Constants.SSID_HIDDEN) if is_readonly else self._create_switch_payload(device, f"{ssid_payload_id}_hidden", "Hide WiFi", state_topic, command_topic, Constants.SSID_HIDDEN, assigned_devices_json)),
            (self._create_binary_sensor_payload(device, f"{ssid_payload_id}_vlan", "VLAN ID", state_topic, Constants.SSID_VLAN_ID) if is_readonly else self._create_number_payload(device, f"{ssid_payload_id}_vlan", "VLAN ID", state_topic, command_topic, Constants.SSID_VLAN_ID, 0, 4094, "{{ value_json.%s if value_json.get('%s') else null }}" % (Constants.SSID_VLAN_ID, Constants.SSID_VLAN_ENABLED), assigned_devices_json)),
            (self._create_sensor_payload(device, f"{ssid_payload_id}_passphrase", "WiFi Passphrase", state_topic, Constants.SSID_KEY) if is_readonly or hide_ssid_passphrase else self._create_text_payload(device, f"{ssid_payload_id}_passphrase", "WiFi Passphrase", state_topic, command_topic, Constants.SSID_KEY, assigned_devices_json)),
            (self._create_sensor_payload(device, f"{ssid_payload_id}_ssid_name", "SSID", state_topic, Constants.SSID_NAME) if is_readonly else self._create_text_payload(device, f"{ssid_payload_id}_ssid_name", "SSID", state_topic, command_topic, Constants.SSID_NAME, assigned_devices_json)),
            self._create_numeric_sensor_payload(device, f"{ssid_payload_id}_client_count", "Clients Online", state_topic, Constants.CLIENT_COUNT),
            self._create_sensor_payload(device, f"{ssid_payload_id}_network_name", "Network", state_topic, "{{ %s }}" % json.dumps(network_name),None,False,True)
        ]

    def _create_device_discovery_payload(self, state_topic: str, command_topic: str, payload: dict[str, object], network_names: dict[int, str], is_readonly: bool) -> list[tuple[str, dict[str, object]]]:
        # For the device block
        device_mac: str = str(payload.get(Constants.MAC))
        normalised_device_mac = MqttPublisherClient.strip_mac(device_mac)
        # override the names in Home Assistant. This will not change anything underlying, only what is displayed in home assistant
        normalised_name_override_macs = self._normalise_macs(self._config.device_name_override)
        device_model: str = device_mac
        device_name: str = str(payload.get(Constants.NAME))
        network_name: str = str(payload.get(Constants.NETWORK_NAME))
        # if no name is given, then use the AP type as a name otherwise, use the network name if there is one, otherwise, use 
        # 'GWN Device' as the name
        if len(device_name) == 0:
            device_name = str(payload.get(Constants.AP_TYPE, network_name if len(network_name) > 0 else "GWN Device"))

        # now actually check if the device name was overridden then use the original name as the model
        # if it exists, otherwise the MAC becomes the model and use the override name as the new name
        if normalised_device_mac in normalised_name_override_macs:
            device_model = device_name if len(device_name) > 0 else device_mac
            device_name = str(normalised_name_override_macs[normalised_device_mac])

        # For the SSID list sensor
        # build the list of SSID names and use the overrides if any names have been overriden in the config
        raw_ssids = payload[Constants.SSIDS]
        ssids: list[dict[str, str]] = raw_ssids if isinstance(raw_ssids,list) else []
        ssid_names: list[str] = []
        for ssid in ssids:
            ssid_name = ssid.get(Constants.SSID_NAME)
            ssid_id: int = int(str(ssid.get(Constants.SSID_ID)))
            if ssid_name is not None and ssid_id is not None:
                ssid_names.append(str(self._config.ssid_name_override.get(ssid_id,ssid_name)))

        # For the Network Name Select input
        network_id: int = int(str(payload.get(Constants.NETWORK_ID)))
        found_names: list[str] = []

        local_network_names = network_names.copy()
        for id in local_network_names:
            new_network_name = local_network_names[id]
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
            local_network_names[id] = new_network_name
        
        device_payload_id: str = f"gwn_device_{normalised_device_mac}"

        device = self._ha_device_block(f"{device_payload_id}", device_name, device_model)

        return [
            self._create_binary_sensor_payload(device, f"{device_payload_id}_wireless", "Wireless", state_topic, Constants.WIRELESS),
            self._create_button_payload(device, f"{device_payload_id}_reboot", "Reboot", command_topic, Constants.REBOOT),
            self._create_button_payload(device, f"{device_payload_id}_reset", "Reset", command_topic, Constants.RESET, False, True),
            self._create_update_payload(device, f"{device_payload_id}_update_firmware","Update Firmware", state_topic, command_topic, "Firmware Update", Constants.UPDATE_FIRMWARE, Constants.CURRENT_FIRMWARE, Constants.NEW_FIRMWARE, False, True),
            (self._create_sensor_payload(device, f"{device_payload_id}_network_name", "Network", state_topic, Constants.NETWORK_NAME) if is_readonly else self._create_select_payload(device, f"{device_payload_id}_network_name", "Network", state_topic, command_topic, Constants.NETWORK_NAME, list(local_network_names.values()),{name: network_id for network_id, name in local_network_names.items()},"{{ %s }}" % json.dumps(network_name), True, True)),
            self._create_binary_sensor_payload(device, f"{device_payload_id}_status", "Status", state_topic, Constants.STATUS),
            self._create_sensor_payload(device, f"{device_payload_id}_ipv4", "IPv4", state_topic, Constants.IPV4),
            self._create_sensor_payload(device, f"{device_payload_id}_ipv6", "IPv6", state_topic, Constants.IPV6),
            self._create_sensor_payload(device, f"{device_payload_id}_firmware", "Current Firmware", state_topic, Constants.CURRENT_FIRMWARE, True, True),
            self._create_sensor_payload(device, f"{device_payload_id}_firmware_new", "Available Firmware", state_topic, Constants.NEW_FIRMWARE, True, True),
            self._create_numeric_sensor_payload(device, f"{device_payload_id}_cpu_usage", "CPU Usage", state_topic, "{{ value_json.%s | replace('%%', '') | int(0) }}" % Constants.CPU_USAGE,"%",None,False,True),
            self._create_numeric_sensor_payload(device, f"{device_payload_id}_temperature", "Temperature", state_topic, "{{ value_json.%s | replace('℃', '') | replace('°C', '') | int(0) }}" % Constants.TEMPERATURE,"°C",None,False,True),
            self._create_sensor_payload(device, f"{device_payload_id}_ssid_names", "SSIDs", state_topic, "{{ %s | join(', ') if %s else 'No SSIDs' }}" % (json.dumps(ssid_names), json.dumps(ssid_names)), False, False, True),
            self._create_numeric_sensor_payload(device, f"{device_payload_id}_uptime", "Up Time", state_topic, Constants.UP_TIME,"s"),
            self._create_sensor_payload(device, f"{device_payload_id}_channel_2_4", "Current 2.4GHz Channel", state_topic, Constants.CHANNEL_2_4),
            self._create_sensor_payload(device, f"{device_payload_id}_channel_5", "Current 5GHz Channel", state_topic, Constants.CHANNEL_5),
            self._create_sensor_payload(device, f"{device_payload_id}_channel_6", "Current 6GHz Channel", state_topic, Constants.CHANNEL_6),
            (self._create_sensor_payload(device, f"{device_payload_id}_ap_2g4_channel", "2.4Ghz Channel", state_topic, Constants.AP_2G4_CHANNEL) if is_readonly else self._create_number_payload(device, f"{device_payload_id}_ap_2g4_channel", "2.4Ghz Channel", state_topic, command_topic, Constants.AP_2G4_CHANNEL, 0, 13)),
            (self._create_sensor_payload(device, f"{device_payload_id}_ap_5g_channel", "5Ghz Channel", state_topic, Constants.AP_5G_CHANNEL) if is_readonly else self._create_number_payload(device, f"{device_payload_id}_ap_5g_channel", "5Ghz Channel", state_topic, command_topic, Constants.AP_5G_CHANNEL, 0, 165, "{{ 0 if value_json.%s | int(0) < 36 else value_json.%s | int(0) }}" % (Constants.AP_5G_CHANNEL, Constants.AP_5G_CHANNEL))),
            (self._create_sensor_payload(device, f"{device_payload_id}_ap_6g_channel", "6Ghz Channel", state_topic, Constants.AP_6G_CHANNEL) if is_readonly else self._create_number_payload(device, f"{device_payload_id}_ap_6g_channel", "6Ghz Channel", state_topic, command_topic, Constants.AP_6G_CHANNEL, 0, 177, "{{ 0 if value_json.%s | int(0) < 36 else value_json.%s | int(0) }}" % (Constants.AP_6G_CHANNEL, Constants.AP_6G_CHANNEL))),
            self._create_sensor_payload(device, f"{device_payload_id}_mac", "MAC", state_topic, Constants.MAC, True, True)
        ]

    def _create_network_discovery_payload(self, state_topic: str, command_topic: str, payload: dict[str, object]) -> list[tuple[str, dict[str, object]]]:
        network_id: str = str(payload.get(Constants.NETWORK_ID))
        network_id_int: int = int(network_id)

        network_name: str = str(payload.get(Constants.NETWORK_NAME))
        network_model: str = "GWN Network"
        if network_id_int in self._config.network_name_override:
            network_model = network_name
            network_name = str(self._config.network_name_override[network_id_int])

        network_payload_id: str = f"gwn_network_{network_id}"

        device = self._ha_device_block(network_payload_id, network_name, network_model)

        return [
            self._create_text_payload(device, f"{network_payload_id}_name", "Name", state_topic, command_topic, Constants.NETWORK_NAME),
            self._create_sensor_payload(device, f"{network_payload_id}_country", "Country", state_topic, Constants.COUNTRY_DISPLAY),
            self._create_sensor_payload(device, f"{network_payload_id}_timezone", "Timezone", state_topic, Constants.TIMEZONE)
        ]

    def _create_application_discovery_payload(self, state_topic: str, command_topic: str, payload: dict[str, object]) -> list[tuple[str, dict[str, object]]]:
        device = self._ha_device_block("gwn_to_mqtt", "GWN to MQTT Bridge", "GWN Manager to MQTT")
        device["manufacturer"] = "GWNtoMQTT"
        application_payload_id: str = "gwn_to_mqtt"

        return [
            self._create_update_payload(device, f"{application_payload_id}_update_version","Update Application",state_topic, command_topic, "Application Update", Constants.UPDATE_VERSION, Constants.CURRENT_VERSION, Constants.NEW_VERSION, True, True),
            self._create_sensor_payload(device, f"{application_payload_id}_version", "Current Version", state_topic, Constants.CURRENT_VERSION, True, True),
            self._create_sensor_payload(device, f"{application_payload_id}_new_version", "Available Version", state_topic, Constants.NEW_VERSION, True, True),
            self._create_button_payload(device, f"{application_payload_id}_restart", "Restart", command_topic, Constants.RESTART)
        ]

    def build_application_discovery_payload(self, state_topic: str, application_topic: str, application_payload: dict[str, object], clear: bool) -> list[tuple[str, dict[str, object]]]:
        command_topic: str = f"{application_topic}/{Constants.SET}"
        ha_application_payload: list[tuple[str, dict[str, object]]] = []
        if clear or (self._config.application_autodiscovery and not self._application_published):
            ha_application_payload = self._create_application_discovery_payload(state_topic, command_topic, application_payload)
        if clear:
            self._application_published = False
        return ha_application_payload

    def build_network_discovery_payload(self, state_topic: str, network_topic: str, network_payload: dict[str, object], clear: bool) -> list[tuple[str, dict[str, object]]]:
        network_id: int = int(str(network_payload.get(Constants.NETWORK_ID)))
        auto_discovery: bool = (self._config.default_network_autodiscovery 
            if network_id not in self._config.network_autodiscovery
            else self._config.network_autodiscovery[network_id]
        )
        command_topic: str = f"{network_topic}/{Constants.SET}"
        ha_network_payload: list[tuple[str, dict[str, object]]] = []
        if clear or (auto_discovery and network_topic not in self._networks_published):
            ha_network_payload = self._create_network_discovery_payload(state_topic, command_topic, network_payload)
        if clear and network_topic in self._networks_published:
            self._networks_published.remove(network_topic)
        return ha_network_payload

    def build_device_discovery_payload(self, state_topic: str, device_topic: str, device_payload: dict[str, object], network_names: dict[int, str], is_readonly: bool, clear: bool) -> list[tuple[str, dict[str, object]]]:
        normalised_macs = self._normalise_macs(self._config.device_autodiscovery)
        device_mac = str(device_payload.get(Constants.MAC))
        normalised_device_mac = MqttPublisherClient.strip_mac(device_mac)
        auto_discovery: bool = (self._config.default_device_autodiscovery 
            if normalised_device_mac not in normalised_macs
            else normalised_macs[normalised_device_mac]
        )
        ha_device_payload: list[tuple[str, dict[str, object]]] = []
        if clear or (auto_discovery and device_topic not in self._devices_published):
            command_topic: str = f"{device_topic}/{Constants.SET}"
            ha_device_payload = self._create_device_discovery_payload(state_topic, command_topic, device_payload, network_names, is_readonly)
        if clear and device_topic in self._devices_published:
            self._devices_published.remove(device_topic)
        return ha_device_payload

    def build_ssid_discovery_payload(self, state_topic: str, ssid_topic: str, ssid_payload: dict[str, object], devices: dict[str, str], is_readonly: bool, clear: bool) -> list[tuple[str, dict[str, object]]]:
        ssid_id: int = int(str(ssid_payload.get(Constants.SSID_ID)))
        auto_discovery: bool = (self._config.default_ssid_autodiscovery 
            if ssid_id not in self._config.ssid_autodiscovery
            else self._config.ssid_autodiscovery[ssid_id]
        )
        ha_ssid_payload: list[tuple[str, dict[str, object]]] = []
        if clear or (auto_discovery and ssid_topic not in self._ssids_published):
            command_topic: str = f"{ssid_topic}/{Constants.SET}"
            ha_ssid_payload = self._create_device_ssid_payload(state_topic, command_topic, ssid_payload, devices, is_readonly)
        if clear and ssid_topic in self._ssids_published:
            self._ssids_published.remove(ssid_topic)
        return ha_ssid_payload

    def application_published(self) -> None:
        self._application_published = not self._config.always_publish_autodiscovery

    def networks_published(self, network_topic: str) -> None:
        if not self._config.always_publish_autodiscovery:
            self._networks_published.add(network_topic)

    def devices_published(self, device_topic: str) -> None:
        if not self._config.always_publish_autodiscovery:
            self._devices_published.add(device_topic)

    def ssids_published(self, ssid_topic: str) -> None:
        if not self._config.always_publish_autodiscovery:
            self._ssids_published.add(ssid_topic)

    def reset_networks(self, network_topic: str | None = None) -> None:
        if network_topic is None:
            self._networks_published = set()
        else:
            self._networks_published.discard(network_topic)

    def reset_devices(self, device_topic: str | None = None) -> None:
        if device_topic is None:
            self._devices_published = set()
        else:
            self._devices_published.discard(device_topic)

    def reset_ssids(self, ssid_topic: str | None = None) -> None:
        if ssid_topic is None:
            self._ssids_published = set()
        else:
            self._ssids_published.discard(ssid_topic)
