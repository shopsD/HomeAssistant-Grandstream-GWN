from dataclasses import dataclass

from gwn.constants.MessageEnums import SecurityMode,MacFiltering,IsolationMode 
from gwn.response_data.GwnDevice import GwnDevice

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
