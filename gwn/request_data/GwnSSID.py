from dataclasses import dataclass
from enum import Enum

from gwn.request_data.GwnDevice import GwnDevice

class SecurityMode(Enum):
    WEP64 = 0
    WEP128 = 1
    WPA_WPA2 = 2
    WPA2 = 3
    OPEN = 4
    WPA3 = 7
    WPA2_WPA3 = 5
    WPA3_192 = 8
    
class MacFiltering(Enum):
    Disabled = 0
    Whitelist = 1
    Blacklist = 2

class IsolationMode(Enum):
    Radio = 0
    Internet = 1
    Gateway = 2

@dataclass(slots=True)
class GwnSSID:
    # get data
    id: str
    ssidName: str
    wifiEnabled: bool
    onlineDevices: int
    scheduleEnabled: bool
    portalEnabled: bool
    securityMode: SecurityMode
    macFilteringEnabled: MacFiltering
    clientIsolationEnabled: bool

    # ssid config
    ssidIsolationMode: IsolationMode | None
    ssidIsolation: bool
    ssidSsidHidden: bool
    ssidNewSsidBand: str
    ssidVlanid: int | None
    ssidVlanEnabled: bool
    ssidEnable: bool
    ssidRemark: str
    ssidKey: str | None

    # parsed from above data
    ghz2_4_Enabled: bool
    ghz5_Enabled: bool
    ghz6_Enabled: bool

    devices: list[GwnDevice]