from dataclasses import dataclass

from gwn.request_data.GwnDevice import GwnDevice
from gwn.request_data.GwnSSID import GwnSSID

@dataclass(slots=True)
class GwnNetwork:
    id: str
    networkName: str
    countryDisplay: str
    country: str
    timezone: str
    devices: list[GwnDevice]
    ssids: list[GwnSSID]

    

