from dataclasses import dataclass

@dataclass(slots=True)
class GwnConfig:
    app_id: str
    secret_key: str
    base_url: str = "https://localhost:8443"
    page_size: int = 10
    max_pages: int = 0 # 0 for unlimited
    refresh_period_s: int = 30 # number of seconds between each poll
    exclude_passphrase: list[int] = []
    exclude_ssid: list[int] = []
    exclude_devices: list[str] = []
    exclude_networks: list[int] = []

    @staticmethod
    def normalise_mac(mac: str) -> str:
        mac = mac.replace(":", "").replace("-", "").upper()
        return ":".join(mac[i:i+2] for i in range(0, 12, 2))