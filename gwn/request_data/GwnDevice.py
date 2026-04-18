from dataclasses import dataclass

from gwn.request_data.GwnSSID import GwnSSID

@dataclass(slots=True)
class GwnDevice:
    status: bool
    apType: str
    mac: str
    name: str
    ip: str
    upTime: str
    usage: int
    upload: int
    download: int
    clients: int
    versionFirmware: str 
    newFirmware: str 
    networkId: str
    ipv6: str

    # detailed info
    wireless: bool
    vlanCount: int
    ssidNumber: int # supported SSID count
    temperature: str
    bootVersion: str
    online: bool

    deviceType: str
    model: str
    network: str
    usedMemory: str
    cpuUsage: str
    channelload_2g4: str
    channelload_5g: str
    channelload_6g: str

    channel_2_4: int
    channel_5: int
    channel_6: int
    ssid: list[GwnSSID]

