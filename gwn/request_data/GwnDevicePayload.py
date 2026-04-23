from dataclasses import dataclass
from enum import Enum

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

class BandSteering(Enum):
    Disable = 0
    Priority_2G4 = 1
    Priority_5G = 2
    Priority_Balance = 3

@dataclass(slots=True)
class GwnDevicePayload:
    ap_2g4_channel: int | None
    ap_2g4_power: RadioPower | None
    ap_2g4_ratelimit_enable: bool | None
    ap_2g4_rssi: str | None
    ap_2g4_rssi_enable: bool | None
    ap_2g4_tag: str | None
    ap_2g4_width: Width2G | None
    ap_5g_channel: int | None
    ap_5g_power: RadioPower | None
    ap_5g_ratelimit_enable: bool | None
    ap_5g_rssi: str | None
    ap_5g_rssi_enable: bool | None
    ap_5g_tag: str | None
    ap_5g_width: Width5G | None
    ap_alternate_dns: str | None
    ap_band_steering: BandSteering | None
    ap_ipv4_route: str | None
    ap_ipv4_static: str | None
    ap_ipv4_static_mask: str | None
    ap_mac: str | None
    ap_name: str | None
    ap_preferred_dns: str | None
    ap_static: bool | None

    REQUIRED: list[str] = [
        "ap_2g4_channel",
        "ap_2g4_power",
        "ap_2g4_ratelimit_enable",
        "ap_2g4_rssi",
        "ap_2g4_rssi_enable",
        "ap_2g4_tag",
        "ap_2g4_width",
        "ap_5g_channel",
        "ap_5g_power",
        "ap_5g_ratelimit_enable",
        "ap_5g_rssi",
        "ap_5g_rssi_enable",
        "ap_5g_tag",
        "ap_5g_width",
        "ap_alternate_dns",
        "ap_band_steering",
        "ap_mac",
        "ap_name"
    ]

    def build_payload(self) -> dict[str, str]:
        # serialise everything to strings
        return {}