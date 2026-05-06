from dataclasses import dataclass, fields
from enum import Enum
from typing import Any, ClassVar

from gwn.constants import (SecurityMode, 
                            MultiCastToUnicast, 
                            MacFiltering, 
                            IsolationMode, 
                            BandwidthType, 
                            SSIDSecurityType, 
                            SSID_11W, 
                            SSID_BMS,
                            WpaEncryption,
                            WpaKeyMode)

@dataclass(slots=True)
class GwnSSIDPayload:
    id: int
    networkId: int
    ssidSsid: str | None = None
    ssidRemark: str | None = None
    ssidEnable: bool | None = None
    ssidVlan: bool | None = None
    ssidVlanid: int | None = None
    ssidRadiusDynamicVlan: str | None = None
    ssidNewSsidBand: str | None = None
    ssidSsidHidden: bool | None = None
    ssidWifiClientLimit: int | None = None # that is serialised as a string
    ssidEncryption: SecurityMode | None = None
    ssidWepKey: str | None = None
    ssidWpaKeyMode: WpaKeyMode | None = None
    ssidWpaEncryption: WpaEncryption | None = None
    ssidWpaKey: str | None = None
    ssidBridgeEnable: bool | None = None
    ssidIsolation: bool | None = None
    ssidIsolationMode: IsolationMode | None = None
    ssidGatewayMac: str | None = None
    ssidVoiceEnterprise: bool | None = None
    ssid11V: bool | None = None
    ssid11R: bool | None = None
    ssid11K: bool | None = None
    ssidDtimPeriod: int | None = None
    ssidMcastToUcast: MultiCastToUnicast | None = None
    ssidProxyarp: bool | None = None
    ssidStaIdleTimeout: int | None = None
    ssid11W: SSID_11W | None = None
    ssidBms: SSID_BMS | None = None
    ssidClientIPAssignment: bool | None = None
    bindMacs: list[str] | None = None # documentation says string. tbc via testing. documentation example shows an array
    removeMacs: list[str] | None = None
    ssidPortalEnable: bool | None = None # bool that is serialised as a string
    ssidPortalPolicy: int | None = None
    ssidMaclistBlacks: list[str] | None = None
    ssidMaclistWhites: list[str] | None = None
    ssidMacFiltering: MacFiltering | None = None
    scheduleId: int | None = None
    ssidTimedClientPolicy: str | None = None
    bandwidthType: BandwidthType | None = None
    bandwidthRules: str | None = None # maybe use an int?
    ssidSecurityType: SSIDSecurityType | None = None
    ppskProfile: str | None = None # maybe use an int?
    radiusProfile: str | None = None # maybe use an int?

    # to be parsed into ssidNewSsidBand
    ghz2_4_enabled: bool | None = None 
    ghz5_enabled: bool | None = None 
    ghz6_enabled: bool | None = None 
    ssid_key: str | None = None 
    toggled_macs: dict[str, bool] | None = None 

    REQUIRED: ClassVar[list[str]] = [
        "id",
        "ssidSsid",
        "ssidWepKey",
        "ssidWpaKey",
        "ssidTimedClientPolicy"
    ]

    NON_SERIALISED: ClassVar[list[str]] = [
        "ghz2_4_enabled",
        "ghz5_enabled",
        "ghz6_enabled",
        "ssid_key",
        "toggled_macs"
    ]
    
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

    def build_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for field_info in fields(self):
            name = field_info.name
            if name in self.NON_SERIALISED:
                continue
            value = getattr(self, name)
            if value is None and name not in self.REQUIRED: # required can be None, it just has to be sent
                continue
            if isinstance(value, bool):
                payload[name] = int(value)
            elif isinstance(value, Enum):
                payload[name] = value.value
            elif isinstance(value, list):
                payload[name] = value
            else:
                payload[name] = None if value is None else str(value)

        ssid_bands = "" if self.ssidNewSsidBand is None else self.ssidNewSsidBand
        if self.ghz2_4_enabled is not None:
            if self.ghz2_4_enabled and "2" not in ssid_bands:
                ssid_bands = f"{ssid_bands}{',' if len(ssid_bands) > 0 else ''}2"
            elif not self.ghz2_4_enabled:
                ssid_bands = ssid_bands.replace("2","")
            payload["ssidNewSsidBand"] = ssid_bands
        if self.ghz5_enabled is not None:
            if self.ghz5_enabled and "5" not in ssid_bands:
                ssid_bands = f"{ssid_bands}{',' if len(ssid_bands) > 0 else ''}5"
            elif not self.ghz5_enabled:
                ssid_bands = ssid_bands.replace("5","")
            payload["ssidNewSsidBand"] = ssid_bands
        if self.ghz6_enabled is not None:
            if self.ghz6_enabled and "6" not in ssid_bands:
                ssid_bands = f"{ssid_bands}{',' if len(ssid_bands) > 0 else ''}6"
            elif not self.ghz6_enabled:
                ssid_bands = ssid_bands.replace("6","")
            payload["ssidNewSsidBand"] = ssid_bands

        # if any required item is missing then just abort. The data is invalid
        for required in self.REQUIRED:
            if required not in payload:
                return {}

        return payload
