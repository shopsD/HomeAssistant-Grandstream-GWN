from dataclasses import dataclass
from pathlib import Path

@dataclass(slots=True)
class AppConfig:
    publish_every_poll: bool = False
    discovery_manifest_path: Path | None = None
