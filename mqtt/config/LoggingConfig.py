from dataclasses import dataclass
from typing import Literal
from pathlib import Path

LogLocation = Literal["syslog", "file", "console"]

@dataclass(slots=True)
class LoggingConfig:
    level: str = "INFO"
    location: LogLocation = "console"
    output_path: Path | None = None
    size: int = 0
    files: int = 1
