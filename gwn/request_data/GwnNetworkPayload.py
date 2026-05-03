from dataclasses import dataclass, fields
from typing import Any, ClassVar

@dataclass(slots=True)
class GwnNetworkPayload:
    id: int
    networkName: str | None = None
    country: str | None = None
    timezone: str | None = None
    networkAdministrators: list[int] | None = None

    REQUIRED: ClassVar[list[str]] = [
        "id",
        "networkName",
        "country",
        "timezone",
        "networkAdministrators",
    ]

    NON_SERIALISED: ClassVar[list[str]] = []

    @classmethod
    def validate_metadata(cls) -> None:
        valid_fields = {field.name for field in fields(cls)}
        invalid_required = [name for name in cls.REQUIRED if name not in valid_fields]
        invalid_non_serialised = [name for name in cls.NON_SERIALISED if name not in valid_fields]

        if invalid_required or invalid_non_serialised:
            raise ValueError(
                f"{cls.__name__} has invalid metadata: "
                f"REQUIRED={invalid_required}, "
                f"NON_SERIALISED={invalid_non_serialised}"
            )

    def build_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for field_info in fields(self):
            name = field_info.name
            if name in self.NON_SERIALISED:
                continue
            value = getattr(self, name)
            if value is None and name not in self.REQUIRED: # required can be None, it just has to be sent
                continue
            if isinstance(value, bool):
                payload[name] = int(value)
            elif isinstance(value, list):
                payload[name] = value
            else:
                payload[name] = None if value is None else str(value)

        # if any required item is missing then just abort. The data is invalid
        for required in self.REQUIRED:
            if required not in payload:
                return {}
        return payload
