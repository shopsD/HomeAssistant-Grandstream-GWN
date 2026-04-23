from dataclasses import dataclass
from enum import Enum
from typing import Any

class SecurityMode(Enum):
    WEP64 = 0
    WEP128 = 1
    WPA_WPA2 = 2
    WPA2 = 3
    OPEN = 4
    WPA = 5 # undocumented and unconfirmed
    WPA2_WPA3 = 6
    WPA3 = 7
    WPA3_192 = 8
    
class MacFiltering(Enum):
    Disabled = 0
    Whitelist = 1
    Blacklist = 2

class IsolationMode(Enum):
    Radio = 0
    Internet = 1
    Gateway = 2

class MultiCastToUnicast(Enum):
    Disabled = 0
    Passive = 1
    Active = 2

class SSID_11W(Enum):
    Disabled = 0
    Optional = 1
    Required = 2

class SSID_BMS(Enum):
    Disabled = 0
    Enabled = 1
    Enable_With_Proxy_ARP = 2

class BandwidthType(Enum):
    NONE = ""
    PerSSID = "0"
    PerClient = "3"

class SSIDSecurityType(Enum):
    Open = 0
    Personal = 1
    Enterprise = 2
    PPSKWithoutRADIUS = 3
    Hotspot2_0_OSEN = 4
    PPSKWithRADIUS = 5

@dataclass(slots=True)
class GwnSSIDPayload:
    id: str | None
    ssidSsid: str | None
    ssidRemark: str | None
    ssidEnable: bool | None
    ssidVlan: bool | None
    ssidVlanid: int | None
    ssidRadiusDynamicVlan: str | None
    ssidNewSsidBand: str | None
    ssidSsidHidden: bool | None
    ssidWifiClientLimit: int | None # that is serialised as a string
    ssidEncryption: SecurityMode | None
    ssidWepKey: str | None
    ssidWpaKeyMode: bool | None
    ssidWpaEncryption: bool | None
    ssidWpaKey: str | None
    ssidBridgeEnable: bool | None
    ssidIsolation: bool | None
    ssidIsolationMode: IsolationMode | None
    ssidGatewayMac: str | None
    ssidVoiceEnterprise: bool | None
    ssid11V: bool | None
    ssid11R: bool | None
    ssid11K: bool | None
    ssidDtimPeriod: int | None
    ssidMcastToUcast: MultiCastToUnicast | None
    ssidProxyarp: bool | None
    ssidStaIdleTimeout: bool | None
    ssid11W: SSID_11W | None
    ssidBms: SSID_BMS | None
    ssidClientIPAssignment: bool | None
    bindMacs: list[str] # documentation says string. tbc via testing. documentation example shows an array
    removeMacs: list[str] | None
    ssidPortalEnable: bool | None # bool that is serialised as a string
    ssidPortalPolicy: bool | None
    ssidMaclistBlacks: list[str] | None
    ssidMaclistWhites: list[str] | None
    ssidMacFiltering: MacFiltering | None
    scheduleId: int | None
    ssidTimedClientPolicy: str | None
    bandwidthType: BandwidthType | None
    bandwidthRules: str | None # maybe use an int?
    ssidSecurityType: SSIDSecurityType | None
    ppskProfile: str | None # maybe use an int?
    radiusProfile: str | None # maybe use an int?

    REQUIRED: list[str] = [
        "id",
        "ssidSsid",
        "ssidWepKey",
        "ssidWpaKey",
        "ssidTimedClientPolicy"
    ]

    def build_payload(self) -> dict[str, Any]:
        return {}