from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(slots=True)
class GwnToken:
    access_token: str
    token_type: str
    expires_in: int
    scope: str
    expires_at: datetime

    @classmethod
    def from_response(cls, data: dict) -> "GwnToken":
        expires_in = int(data.get("expires_in", 0))
        # Refresh a little early to avoid edge-of-expiry failures.
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=max(expires_in - 60, 0))

        return cls(
            access_token=data["access_token"],
            token_type=data.get("token_type", "bearer"),
            expires_in=expires_in,
            scope=data.get("scope", ""),
            expires_at=expires_at,
        )

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at
