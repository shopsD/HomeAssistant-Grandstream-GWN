from dataclasses import dataclass

@dataclass(slots=True)
class GwnAuthConfig:
    base_url: str
    client_id: str
    client_secret: str
    app_id: str
    secret_key: str
