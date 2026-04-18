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
    channel: str
    channel5g: str
    clients: int
    versionFirmware: str 
    networkId: str
    ipv6: str

    # detailed info
    wireless: int
    vlanCount: int
    ssidNumber: int # supported SSID count
    temperature: str
    bootVersion: str
    
    ipv4: str
    deviceName: str
    network: str
    usedMemory: str
    cpuUsage: str
    channelload_2g4: str
    channelload_5g: str
    channelload_6g: str
    ssid: list[GwnSSID]
    linkSpeed: str

