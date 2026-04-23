from enum import Enum

# Device Enums
class RadioPower(Enum):
    Low = 0
    Medium = 1
    High = 2
    Custom = 3
    UseRadioSetting = 4

class Width2G(Enum):
    MHz_20 = 0
    MHz_20_40 = 1
    MHz_40 = 2
    UseRadioSetting = 3

class Width5G(Enum):
    MHz_20 = 0
    MHz_40 = 1
    MHz_80 = 2
    MHz_160 = 3 # undocumented
    UseRadioSetting = 4

# 6GHz is undocumented so this cannot be confirmed
class Width6G(Enum):
    MHz_20 = 0
    MHz_40 = 1
    MHz_80 = 2
    MHz_160 = 3
    MHz_320 = 4
    UseRadioSetting = 5

class BandSteering(Enum):
    Disable = 0
    Priority_2G4 = 1
    Priority_5G = 2
    Priority_Balance = 3

# SSID Enums
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
