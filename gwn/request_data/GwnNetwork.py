from dataclasses import dataclass

from gwn.request_data.GwnDevice import GwnDevice

@dataclass(slots=True)
class GwnNetwork:
    id: str
    networkName: str
    countryDisplay: str
    country: str
    timezone: str
    devices: list[GwnDevice]

    

