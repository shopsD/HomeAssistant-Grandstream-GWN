from dataclasses import dataclass

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

    # channel info
    ap_2g4_channel: int
    ap_5g_channel: int
    ap_6g_channel: int

    # parsed channel info
    channel_lists_2g4: dict[int, str]
    channel_lists_5g: dict[int, str]
    channel_lists_6g: dict[int, str]
