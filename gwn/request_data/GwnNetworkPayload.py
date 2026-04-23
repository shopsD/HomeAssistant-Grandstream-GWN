from dataclasses import dataclass
from typing import Any, ClassVar

@dataclass(slots=True)
class GwnNetworkPayload:
    id: str
    networkName: str | None = None
    country: str | None = None
    timezone: str | None = None
    networkAdministrators: list[str] | None = None

    REQUIRED: ClassVar[list[str]] = [
        "id",
        "networkName",
        "country",
        "timezone",
        "networkAdministrators",
    ]

    def build_payload(self) -> dict[str, Any]:
        return {}