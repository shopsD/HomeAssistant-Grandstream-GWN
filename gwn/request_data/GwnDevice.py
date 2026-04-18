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
    networkId: str
    ipv6: str

    # firmware info
    newFirmware: str 

    # detailed info port
    wireless: bool
    vlanCount: int
    ssidNumber: int # supported SSID count
    online: bool
    model: str
    deviceType: str

    # detailed info client
    channel_5: int
    channel_2_4: int
    channel_6: int
    partNumber: str
    bootVersion: str
    network: str
    temperature: str
    usedMemory: str
    channelload_2g4: str
    channelload_6g: str
    cpuUsage: str
    channelload_5g: str

    ssids: list[GwnSSID]

