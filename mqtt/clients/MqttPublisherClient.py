

class MqttPublisherClient():

    @staticmethod
    def strip_mac(mac: str) -> str:
        return mac.replace(":", "").replace("-","").lower()

    def build_application_discovery_payload(self, state_topic: str, application_topic: str, application_payload: dict[str, object], clear: bool) -> list[tuple[str, dict[str, object]]]:
        return []

    def build_network_discovery_payload(self, state_topic: str, network_topic: str, network_payload: dict[str, object], clear: bool) -> list[tuple[str, dict[str, object]]]:
        return []

    def build_device_discovery_payload(self, state_topic: str, device_topic: str, device_payload: dict[str, object], network_names: dict[int, str], clear: bool) -> list[tuple[str, dict[str, object]]]:
        return []

    def build_ssid_discovery_payload(self, state_topic: str, ssid_topic: str, ssid_payload: dict[str, object], devices: dict[str, str], clear: bool) -> list[tuple[str, dict[str, object]]]:
        return []

    def application_published(self) -> None:
        pass

    def networks_published(self, network_topic: str) -> None:
        pass

    def devices_published(self, device_topic: str) -> None:
        pass

    def ssids_published(self, ssid_topic: str) -> None:
        pass

    def reset_networks(self, network_topic: str | None = None) -> None:
        pass

    def reset_devices(self, device_topic: str | None = None) -> None:
        pass

    def reset_ssids(self, ssid_topic: str | None = None) -> None:
        pass
