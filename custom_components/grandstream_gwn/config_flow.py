import re
import voluptuous as vol
from typing import Any

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult

from .const import DOMAIN
from gwn.authentication import GwnConfig

MAC_MATCHER=re.compile('^([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}(,([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2})*$')

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def _check_numeric_list(self, list_string: str | None) -> bool:
        return list_string is not None and (list_string == "" or list_string.replace(",","").isnumeric())
    
    def _check_mac_list(self, list_string: str | None) -> bool:
        return list_string is not None and (list_string == "" or bool(MAC_MATCHER.match(list_string)))

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            data: dict[str, Any] = {
                "app_id": str(user_input["app_id"]),
                "secret_key": str(user_input["secret_key"])
            }
            page_size = user_input.get("page_size")
            if page_size is not None:
                if int(page_size) < 1:
                    errors["page_size"] = "required_ge_1"
                else:
                    data["page_size"] = int(page_size)

            max_pages = user_input.get("max_pages")
            if max_pages is not None:
                if int(max_pages) < 0:
                    errors["max_pages"] = "required_ge_0"
                else:
                    data["max_pages"] = int(max_pages)
            refresh_period_s = user_input.get("refresh_period_s")
            if refresh_period_s is not None:
                if int(refresh_period_s) < 0:
                    errors["refresh_period_s"] = "required_ge_0"
                else:
                    data["refresh_period_s"] = int(refresh_period_s)

            username = user_input.get("username")
            password = user_input.get("password")

            has_username = username not in (None, "")
            has_password = password not in (None, "")
            if has_username and not has_password:
                errors["password"] = "required_with_username"
            elif has_password and not has_username:
                errors["username"] = "required_with_password"
            elif has_password and has_username:
                data["username"] = str(username)
                data["password"] = str(password)

            restricted_api = user_input.get("restricted_api")
            if restricted_api is not None and bool(restricted_api):
                if not has_username or not has_password:
                    errors["restricted_api"] = "requires_passord_username"
                else:
                    data["restricted_api"] = bool(restricted_api)

            exclude_passphrase = user_input.get("exclude_passphrase")
            if self._check_numeric_list(exclude_passphrase):
                data["exclude_passphrase"] = str(exclude_passphrase)
            else:
                errors["exclude_passphrase"] = "not_list_of_ints"
            
            exclude_ssid = user_input.get("exclude_ssid")
            if not self._check_numeric_list(exclude_ssid):
                data["exclude_ssid"] = str(exclude_ssid)
            else:
                errors["exclude_ssid"] = "not_list_of_ints"

            exclude_device = user_input.get("exclude_device")
            if not self._check_mac_list(exclude_device):
                data["exclude_device"] = str(exclude_device)
            else:
                errors["exclude_device"] = "not_list_of_macs"

            exclude_network = user_input.get("exclude_network")
            if not self._check_numeric_list(exclude_network):
                data["exclude_network"] = str(exclude_network)
            else:
                errors["exclude_network"] = "not_list_of_ints"

            base_url = user_input.get("base_url")
            if base_url is not None:
                data[base_url] = str(base_url)

            ignore_failed_fetch_before_update = user_input.get("ignore_failed_fetch_before_update")
            if ignore_failed_fetch_before_update is not None:
                data[ignore_failed_fetch_before_update] = bool(ignore_failed_fetch_before_update)

            ssid_name_to_device_binding = user_input.get("ssid_name_to_device_binding")
            if ssid_name_to_device_binding is not None:
                data[ssid_name_to_device_binding] = bool(ssid_name_to_device_binding)

            no_publish = user_input.get("no_publish")
            if no_publish is not None:
                data[no_publish] = bool(no_publish)


            if len(errors) == 0:
                return self.async_create_entry(
                    title=user_input["base_url"],
                    data=data
                )
        defaults: GwnConfig = GwnConfig("dummy", "dummy") # dummy to initialise the defaults
        schema = vol.Schema(
            {
                vol.Required("app_id"): str,
                vol.Required("secret_key"): str,
                vol.Optional("restricted_api", default=defaults.restricted_api): bool,
                vol.Optional("username", default=defaults.username): str,
                vol.Optional("password", default=defaults.password): str,
                vol.Optional("base_url", default=defaults.base_url): str,
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
