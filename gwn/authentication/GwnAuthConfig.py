from dataclasses import dataclass

@dataclass(slots=True)
class GwnAuthConfig:
    base_url: str = "https://localhost:8443"
    client_id: str | None = None
    client_secret: str | None = None
    app_id: str | None = None
    secret_key: str | None = None
