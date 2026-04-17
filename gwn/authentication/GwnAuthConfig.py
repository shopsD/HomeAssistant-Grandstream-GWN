from dataclasses import dataclass

@dataclass(slots=True)
class GwnAuthConfig:
    app_id: str
    secret_key: str
    base_url: str = "https://localhost:8443"
