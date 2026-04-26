from dataclasses import dataclass
from typing import ClassVar

@dataclass(slots=True)
class Constants:
    LOG:ClassVar[str] = "gwn_mqtt"
    APP_VERSION:ClassVar[str] = "0.0.1"

    # mqtt keys
    # ssid
    SSID_NAME: ClassVar[str] = "ssidName"
    WIFI_ENABLED: ClassVar[str] = "wifiEnabled"
    CLIENT_COUNT: ClassVar[str] = "onlineDevices"
    SCHEDULE_ENABLED: ClassVar[str] = "scheduleEnabled"
    PORTAL_ENABLED: ClassVar[str] = "portalEnabled"
    MAC_FILTERING_ENABLED: ClassVar[str] = "macFilteringEnabled"
    CLIENT_ISOLATION_ENABLED: ClassVar[str] = "clientIsolationEnabled"
    SSID_ISOLATION_MODE: ClassVar[str] = "ssidIsolationMode"
    SSID_ISOLATION: ClassVar[str] = "ssidIsolation"
    SSID_HIDDEN: ClassVar[str] = "ssidSsidHidden"
    SSID_VLAN_ID: ClassVar[str] = "ssidVlanid"
    SSID_VLAN_ENABLED: ClassVar[str] = "ssidVlanEnabled"
    SSID_ENABLE: ClassVar[str] = "ssidEnable"
    SSID_REMARK: ClassVar[str] = "ssidRemark"
    SSID_KEY: ClassVar[str] = "ssidKey"
    GHZ2_4_ENABLED: ClassVar[str] = "ghz2_4_Enabled"
    GHZ5_ENABLED: ClassVar[str] = "ghz5_Enabled"
    GHZ6_ENABLED: ClassVar[str] = "ghz6_Enabled"
    ASSIGNED_DEVICES: ClassVar[str] = "assignedDevices"

    # device
    STATUS: ClassVar[str] = "status"
    AP_TYPE: ClassVar[str] = "apType"
    MAC: ClassVar[str] = "mac"
    NAME: ClassVar[str] = "name"
    IPV4: ClassVar[str] = "ip"
    UP_TIME: ClassVar[str] = "upTime"
    USAGE: ClassVar[str] = "usage"
    UPLOAD: ClassVar[str] = "upload"
    DOWNLOAD: ClassVar[str] = "download"
    CLIENTS: ClassVar[str] = "clients"
    CURRENT_FIRMWARE: ClassVar[str] = "versionFirmware"
    IPV6: ClassVar[str] = "ipv6"
    NEW_FIRMWARE: ClassVar[str] = "newFirmware"
    WIRELESS: ClassVar[str] = "wireless"
    VLAN_MAX_SIZE: ClassVar[str] = "vlanCount"
    SSID_COUNT: ClassVar[str] = "ssidNumber"
    ONLINE_STATUS: ClassVar[str] = "online"
    MODEL: ClassVar[str] = "model"
    DEVICE_TYPE: ClassVar[str] = "deviceType"
    CHANNEL_5: ClassVar[str] = "channel_5"
    CHANNEL_2_4: ClassVar[str] = "channel_2_4"
    CHANNEL_6: ClassVar[str] = "channel_6"
    PART_NUMBER: ClassVar[str] = "partNumber"
    BOOT_VERSION: ClassVar[str] = "bootVersion"
    NETWORK: ClassVar[str] = "network"
    TEMPERATURE: ClassVar[str] = "temperature"
    USED_MEMORY: ClassVar[str] = "usedMemory"
    CHANNEL_LOAD_2G4: ClassVar[str] = "channelload_2g4"
    CHANNEL_LOAD_6G: ClassVar[str] = "channelload_6g"
    CPU_USAGE: ClassVar[str] = "cpuUsage"
    CHANNEL_LOAD_5G: ClassVar[str] = "channelload_5g"
    AP_2G4_CHANNEL: ClassVar[str] = "ap_2g4_channel"
    AP_5G_CHANNEL: ClassVar[str] = "ap_5g_channel"
    AP_6G_CHANNEL: ClassVar[str] = "ap_6g_channel" # potentially unsupported
    # NETWORK_NAME (In Network)
    SSIDS: ClassVar[str] = "ssids"

    # buttons/commands (no GWN Inputs)
    REBOOT: ClassVar[str] = "reboot"
    UPDATE_FIRMWARE: ClassVar[str] = "update_firmware"
    RESET: ClassVar[str] = "reset"

    # network
    COUNTRY_DISPLAY: ClassVar[str] = "countryDisplay"
    TIMEZONE: ClassVar[str] = "timezone"
    NETWORK_NAME: ClassVar[str] = "networkName"

    # application 
    CURRENT_VERSION: ClassVar[str] = "currentVersion"
    NEW_VERSION: ClassVar[str] = "newVersion"
    UPDATE_VERSION: ClassVar[str] = "update_version"
    RESTART: ClassVar[str] = "restart"

    # mqtt command envelope
    ACTION: ClassVar[str] = "action"
    VALUE: ClassVar[str] = "value"
    ACTIONS: ClassVar[str] = "actions"
    NETWORK_ID: ClassVar[str] = "network_id"
    SSID_ID: ClassVar[str] = "ssid_id"
    TOGGLE_DEVICE: ClassVar[str] = "toggle_device"
    DEVICE_MACS: ClassVar[str] = "device_macs"

    # MQTT Topics
    APPLICATION: ClassVar[str] = "application"
    DEVICES: ClassVar[str] = "devices"
    GWN: ClassVar[str] = "gwn"
    NETWORKS: ClassVar[str] = "networks"
    SET: ClassVar[str] = "set"
    STATE: ClassVar[str] = "state"
    CONFIG: ClassVar[str] = "config"

    # Application Processing
    CACHE: ClassVar[str] = "cache"
