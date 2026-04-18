from typing import Any

from gwn.api.GwnRequestor import GwnRequestor
from gwn.authentication import GwnConfig


class GwnClient:
    def __init__(self, config: GwnConfig) -> None:
        self._config = config
        self._requestor = GwnRequestor(config)

    @property
    def refresh_period(self) -> int:
        return self._config.refresh_period_s

    async def authenticate(self) -> bool:
        return await self._requestor.authenticate()

    async def get_all_networks(self) -> list[dict[str, Any]] | None:
        return await self._requestor.get_all_networks()

    async def get_all_ssids(self, network_id: str) -> list[dict[str, Any]] | None:
        return await self._requestor.get_all_ssids(network_id)

    async def get_all_devices(self, network_id: str) -> dict[str, Any] | None:
        device_response = await self._requestor.get_all_devices(network_id)
        macs: list[str] = []
        if device_response is not None:
            for result in device_response:
                mac = result.get("mac")
                if mac:
                    macs.append(mac)
        return await self._requestor.get_device_list_info(macs)
