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


    def _create_device_ssid_payload(self, state_topic: str, command_topic: str, payload: dict[str, object], network_id: int, network_name: str, device_data: list[list[str]]) -> list[tuple[str, dict[str, object]]]:
        ssid_id: str = str(payload.get(Constants.SSID_ID))
        ssid_id_int: int = int(ssid_id)
        # Use the SSID name and network name as model unless there was an override then use then
        # use the override as the SSID name and the old SSID name as the model
        ssid_name: str = str(payload.get(Constants.SSID_NAME))
        ssid_model: str = network_name if len(network_name) > 0 else "GWN SSID"
        if ssid_id_int in self._config.ssid_name_override:
            ssid_model = ssid_name
            ssid_name = str(self._config.ssid_name_override[ssid_id_int])
        ssid_payload_id: str = f"gwn_ssid_{ssid_id}"
        device = self._ha_device_block(ssid_payload_id, ssid_name, ssid_model)

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
                    self._ha_discovery_topic("switch", f"{ssid_payload_id}_{normalised_device_mac}_device_enable"),
                    {
                        "name": f"Assign {device_name}",
                        "unique_id": f"{ssid_payload_id}_{normalised_device_mac}_device_enable",
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
            self._create_switch_payload(device, f"{ssid_payload_id}_enabled", "Enabled", state_topic, command_topic, Constants.SSID_ENABLE, assigned_devices_json),
            self._create_switch_payload(device, f"{ssid_payload_id}_portal", "Captive Portal", state_topic, command_topic, Constants.PORTAL_ENABLED, assigned_devices_json),
            self._create_switch_payload(device, f"{ssid_payload_id}_client_isolation_enabled", "Client Isolation", state_topic, command_topic, Constants.CLIENT_ISOLATION_ENABLED, assigned_devices_json),
            self._create_switch_payload(device, f"{ssid_payload_id}_enabled_2_4", "2.4GHz Station", state_topic, command_topic, Constants.GHZ2_4_ENABLED, assigned_devices_json),
            self._create_switch_payload(device, f"{ssid_payload_id}_enabled_5", "5GHz Station", state_topic, command_topic, Constants.GHZ5_ENABLED, assigned_devices_json),
            self._create_switch_payload(device, f"{ssid_payload_id}_enabled_6", "6GHz Station", state_topic, command_topic, Constants.GHZ6_ENABLED, assigned_devices_json),
            self._create_switch_payload(device, f"{ssid_payload_id}_hidden", "Hide WiFi", state_topic, command_topic, Constants.SSID_HIDDEN, assigned_devices_json),
            self._create_number_payload(device, f"{ssid_payload_id}_vlan", "VLAN ID", state_topic, command_topic, Constants.SSID_VLAN_ID, 0, 4094, "{{ value_json.%s if value_json.get('%s') else null }}" % (Constants.SSID_VLAN_ID, Constants.SSID_VLAN_ENABLED), assigned_devices_json),
            self._create_text_payload(device, f"{ssid_payload_id}_passphrase", "WiFi Passphrase", state_topic, command_topic, Constants.SSID_KEY, assigned_devices_json),
            self._create_text_payload(device, f"{ssid_payload_id}_ssid_name", "SSID", state_topic, command_topic, Constants.SSID_NAME, assigned_devices_json),
            self._create_numeric_sensor_payload(device, f"{ssid_payload_id}_client_count", "Clients Online", state_topic, Constants.CLIENT_COUNT),
            self._create_sensor_payload(device, f"{ssid_payload_id}_network_name", "Network", state_topic, "{{ %s }}" % json.dumps(network_name),None,False,True)
        ]

    def _create_device_discovery_payload(self, state_topic: str, command_topic: str, payload: dict[str, object], network_id: int, network_name: str, network_names: dict[int, str]) -> list[tuple[str, dict[str, object]]]:
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
        
        device_payload_id: str = f"gwn_device_{normalised_device_mac}"

        device = self._ha_device_block(f"{device_payload_id}", device_name, device_model)

        return [
            self._create_switch_payload(device, f"{device_payload_id}_wireless", "Wireless", state_topic, command_topic, Constants.WIRELESS),
            self._create_button_payload(device, f"{device_payload_id}_reboot", "Reboot", command_topic, Constants.REBOOT),
            self._create_button_payload(device, f"{device_payload_id}_reset", "Reset", command_topic, Constants.RESET, False, True),
            self._create_update_payload(device, f"{device_payload_id}_update_firmware","Update Firmware", state_topic, command_topic, "Firmware Update", Constants.UPDATE_FIRMWARE, Constants.CURRENT_FIRMWARE, Constants.NEW_FIRMWARE, False, True),
            self._create_select_payload(device, f"{device_payload_id}_network_name", "Network", state_topic, command_topic, Constants.NETWORK_NAME, list(network_names.values()),{name: network_id for network_id, name in network_names.items()},"{{ %s }}" % json.dumps(network_name), True, True),
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
            self._create_number_payload(device, f"{device_payload_id}_ap_2g4_channel", "2.4Ghz Channel", state_topic, command_topic, Constants.AP_2G4_CHANNEL, 0, 13),
            self._create_number_payload(device, f"{device_payload_id}_ap_5g_channel", "5Ghz Channel", state_topic, command_topic, Constants.AP_5G_CHANNEL, 0, 165, "{{ 0 if value_json.%s | int(0) < 36 else value_json.%s | int(0) }}" % (Constants.AP_5G_CHANNEL, Constants.AP_5G_CHANNEL)),
            self._create_number_payload(device, f"{device_payload_id}_ap_6g_channel", "6Ghz Channel", state_topic, command_topic, Constants.AP_6G_CHANNEL, 0, 177, "{{ 0 if value_json.%s | int(0) < 36 else value_json.%s | int(0) }}" % (Constants.AP_6G_CHANNEL, Constants.AP_6G_CHANNEL)),
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

    def _generic_application_payload_to_homeassistant(self, state_topic: str, command_topic: str, payload: dict[str, object]) -> list[tuple[str, dict[str, object]]]:
        device = self._ha_device_block("gwn_to_mqtt", "GWN to MQTT Bridge", "GWN Manager to MQTT")
        device["manufacturer"] = "GWNtoMQTT"
        application_payload_id: str = "gwn_to_mqtt"

        return [
            self._create_update_payload(device, f"{application_payload_id}_update_version","Update Application",state_topic, command_topic, "Application Update", Constants.UPDATE_VERSION, Constants.CURRENT_VERSION, Constants.NEW_VERSION, True, True),
            self._create_sensor_payload(device, f"{application_payload_id}_version", "Current Version", state_topic, Constants.CURRENT_VERSION, True, True),
            self._create_sensor_payload(device, f"{application_payload_id}_new_version", "Available Version", state_topic, Constants.NEW_VERSION, True, True),
            self._create_button_payload(device, f"{application_payload_id}_restart", "Restart", command_topic, Constants.RESTART)
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
            ha_network_payload = self._create_network_discovery_payload(state_topic, command_topic, gwn_network)
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
            ha_device_payload = self._create_device_discovery_payload(state_topic, command_topic, device_payload, network_id, network_name, network_names)
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
            ha_ssid_payload = self._create_device_ssid_payload(state_topic, command_topic, ssid_payload, network_id, network_name, devices)
            # now actually publish
            for topic, discovery_payload in ha_ssid_payload:
                await self._interface.publish(topic, json.dumps(discovery_payload), retain=True)
