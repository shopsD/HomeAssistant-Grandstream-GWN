from dataclasses import dataclass

@dataclass(slots=True)
class AppConfig:
    publish_every_poll: bool = False
    unpublish_initial_data: bool = False
    check_for_updates: bool = True
    allow_pre_release_update: bool = False
    update_check_period_s: int = 21600