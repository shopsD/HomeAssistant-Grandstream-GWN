from dataclasses import dataclass
from enum import Enum


class SecurityMode(Enum):
    WEP64 = 0
    WEP128 = 1
    WPA_WPA2 = 2
    WPA2 = 3
    OPEN = 4
    
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
    id: int
    ssidName: str
    wifiEnabled: bool
    vlanId: str
    onlineDevices: int
    scheduleEnabled: bool
    portalEnabled: bool
    securityMode: SecurityMode
    macFilteringEnabled: MacFiltering
    clientIsolationEnabled: bool

    # ssid config
    ssidIsolationMode: IsolationMode
    ssidSsidHidden: bool
    ssidNewSsidBand: str
    ssidVlanid: int
    ssidVlan: int
    ssidEnable: bool
    ssidRemark: str


