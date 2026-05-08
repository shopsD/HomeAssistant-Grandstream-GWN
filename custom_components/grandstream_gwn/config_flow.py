import voluptuous as vol
from typing import Any

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult

from .const import DOMAIN
from gwn.authentication import GwnConfig


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        defaults: GwnConfig = GwnConfig("dummy", "dummy") # dummy to initialise the defaults
        if user_input is not None:
            return self.async_create_entry(
                title=user_input["url"],
                data={
                    "app_id": user_input["app_id"],
                    "secret_key": user_input["secret_key"],
                    "restricted_api": user_input.get("restricted_api"),
                    "username": user_input.get("username"),
                    "password": user_input.get("password"),
                    "hashed_password": user_input.get("hashed_password"),
                    "url": user_input.get("url"),
                    "page_size": user_input.get("page_size"),
                    "max_pages": user_input.get("max_pages"),
                    "refresh_period_s": user_input.get("refresh_period_s"),
                    "exclude_passphrase": user_input.get("exclude_passphrase"),
                    "exclude_ssid": user_input.get("exclude_ssid"),
                    "exclude_device": user_input.get("exclude_device"),
                    "exclude_network": user_input.get("exclude_network"),
                    "ignore_failed_fetch_before_update": user_input.get("ignore_failed_fetch_before_update"),
                    "ssid_name_to_device_binding": user_input.get("ssid_name_to_device_binding"),
                    "no_publish": user_input.get("no_publish")
                }
            )

        schema = vol.Schema(
            {
                vol.Required("app_id"): str,
                vol.Required("secret_key"): str,
                vol.Optional("restricted_api", default=defaults.restricted_api): bool,
                vol.Optional("username", default=defaults.username): str,
                vol.Optional("password", default=defaults.password): str,
                vol.Optional("hashed_password"): str,
                vol.Optional("url", default=defaults.base_url): str,
                vol.Optional("page_size", default=defaults.page_size): int,
                vol.Optional("max_pages", default=defaults.max_pages): int,
                vol.Optional("refresh_period_s", default=defaults.refresh_period_s): int,
                vol.Optional("exclude_passphrase", default=",".join(str(id) for id in defaults.exclude_passphrase)): str,
                vol.Optional("exclude_ssid", default=",".join(str(id) for id in defaults.exclude_ssid)): str,
                vol.Optional("exclude_device", default=",".join(defaults.exclude_device)): str,
                vol.Optional("exclude_network", default=",".join(str(id) for id in defaults.exclude_network)): str,
                vol.Optional("ignore_failed_fetch_before_update", default=defaults.ignore_failed_fetch_before_update): bool,
                vol.Optional("ssid_name_to_device_binding", default=defaults.ssid_name_to_device_binding): bool,
                vol.Optional("no_publish", default=defaults.no_publish): bool
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
