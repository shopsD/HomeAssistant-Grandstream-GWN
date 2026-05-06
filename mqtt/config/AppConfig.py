from dataclasses import dataclass

@dataclass(slots=True)
class AppConfig:
    publish_every_poll: bool = False
    unpublish_initial_data: bool = False
