from dataclasses import dataclass, fields
from enum import Enum
from typing import ClassVar

from gwn.constants.MessageEnums import RadioPower, Width2G, Width5G, Width6G, BandSteering, BooleanEnum

@dataclass(slots=True)
class GwnDevicePayload:
    ap_mac: str
    networkId: int
    ap_2g4_channel: int | None = None
    ap_2g4_power: RadioPower | None = None
    ap_2g4_ratelimit_enable: BooleanEnum | None = None
    ap_2g4_rssi: int | None = None
    ap_2g4_rssi_enable: BooleanEnum | None = None
    ap_2g4_tag: str | None = None
    ap_2g4_width: Width2G | None = None
    ap_5g_channel: int | None = None
    ap_5g_power: RadioPower | None = None
    ap_5g_ratelimit_enable: BooleanEnum | None = None
    ap_5g_rssi: int | None = None
    ap_5g_rssi_enable: BooleanEnum | None = None
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

    # 6GHz is Undocumented but grandstream customer support said it is available
    ap_6g_channel: int | None = None
    ap_6g_power: RadioPower | None = None
    ap_6g_ratelimit_enable: BooleanEnum | None = None
    ap_6g_rssi: int | None = None
    ap_6g_rssi_enable: BooleanEnum | None = None
    ap_6g_tag: str | None = None
    ap_6g_width: Width6G | None = None

    target_network: int | None = None
    # commands
    reboot: bool = False
    reset: bool = False
    update: bool = False

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
        "ap_name",
        # since 6GHz is undocumented but grandstream customer support said it is available based on 2.4GHz and 5GHz
        "ap_6g_channel",
        "ap_6g_power",
        "ap_6g_ratelimit_enable",
        "ap_6g_rssi",
        "ap_6g_rssi_enable",
        "ap_6g_tag",
        "ap_6g_width"
    ]

    NON_SERIALISED: ClassVar[list[str]] = ["networkId", "reboot", "reset", "update", "target_network"]

    @classmethod
    def validate_metadata(cls) -> None:
        valid_fields = {field.name for field in fields(cls)}
        invalid_required = [name for name in cls.REQUIRED if name not in valid_fields]
        invalid_non_serialised = [name for name in cls.NON_SERIALISED if name not in valid_fields]

        if invalid_required or invalid_non_serialised:
            raise ValueError(
                f"{cls.__name__} has invalid metadata: "
                f"REQUIRED={invalid_required}, "
                f"NON_SERIALISED={invalid_non_serialised}"
            )

    def build_payload(self) -> dict[str, str]:
        payload: dict[str, str] = {}
        for field_info in fields(self):
            name = field_info.name
            if name in self.NON_SERIALISED:
                continue
            value = getattr(self, name)
            if value is None and name not in self.REQUIRED: # required can be None, it just has to be sent
                continue
            if isinstance(value, bool):
                payload[name] = "1" if value else "0"
            elif isinstance(value, Enum):
                payload[name] = str(value.value)
            else:
                payload[name] = None if value is None else str(value)

        # if any required item is missing then just abort. The data is invalid
        for required in self.REQUIRED:
            if required not in payload:
                return {}
        return payload
