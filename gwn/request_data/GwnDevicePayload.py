from dataclasses import dataclass
from typing import ClassVar

from gwn.constants.MessageEnums import RadioPower, Width2G, Width5G, BandSteering

@dataclass(slots=True)
class GwnDevicePayload:
    ap_mac: str
    ap_2g4_channel: int | None = None
    ap_2g4_power: RadioPower | None = None
    ap_2g4_ratelimit_enable: bool | None = None
    ap_2g4_rssi: str | None = None
    ap_2g4_rssi_enable: bool | None = None
    ap_2g4_tag: str | None = None
    ap_2g4_width: Width2G | None = None
    ap_5g_channel: int | None = None
    ap_5g_power: RadioPower | None = None
    ap_5g_ratelimit_enable: bool | None = None
    ap_5g_rssi: str | None = None
    ap_5g_rssi_enable: bool | None = None
    ap_5g_tag: str | None = None
    ap_5g_width: Width5G | None = None
    ap_alternate_dns: str | None = None
    ap_band_steering: BandSteering | None = None
    ap_ipv4_route: str | None = None
    ap_ipv4_static: str | None = None
    ap_ipv4_static_mask: str | None = None
    ap_name: str | None = None
    ap_preferred_dns: str | None = None
    ap_static: bool | None = None

    REQUIRED: ClassVar[list[str]] = [
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