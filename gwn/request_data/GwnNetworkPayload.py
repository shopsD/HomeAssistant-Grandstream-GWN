from dataclasses import dataclass
from typing import Any

@dataclass(slots=True)
class GwnNetworkPayload:
    id: str | None
    networkName: str | None
    country: str | None
    timezone: str | None
    networkAdministrators: list[str] | None

    REQUIRED: list[str] = [
        "id",
        "networkName",
        "country",
        "timezone",
        "networkAdministrators",
    ]

    def build_payload(self) -> dict[str, Any]:
        return {}