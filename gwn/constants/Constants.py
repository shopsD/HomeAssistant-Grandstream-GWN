from dataclasses import dataclass
from typing import ClassVar

@dataclass(slots=True)
class Constants:
    LOG:ClassVar[str] = "gwn_mqtt"
    APP_VERSION:ClassVar[str] = "0.0.1"
