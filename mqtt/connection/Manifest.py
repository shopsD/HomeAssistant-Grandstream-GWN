import logging
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from gwn.constants import Constants
from mqtt.config import MqttConfig

_LOGGER = logging.getLogger(Constants.LOG)

@dataclass(slots=True)
class ManifestConstants:
    TOPIC: ClassVar[str] = "topic"
    VERSION: ClassVar[str] = "version"

class Manifest:

    def __init__(self, config: MqttConfig) -> None:
        self._config: MqttConfig = config
        self._published_topics: set[str] = set()
        self._manifest_path: Path | None = self._initialise_manifest_path()
        self._has_changes: bool = False

    def _initialise_manifest_path(self) -> Path | None:
        manifest_path: Path | None = None
        if self._config.topic_manifest_path is None:
            _LOGGER.info("No Manifest Path Specified")
            return None
        manifest_path = Path(self._config.topic_manifest_path).resolve()
        if manifest_path.is_dir():
            manifest_path = manifest_path / "manifest.yml"
        _LOGGER.info(f"Manifest file set to {manifest_path}")
        return manifest_path

    @property
    def published_topics(self) -> set[str]:
        return self._published_topics

    def read_manifest(self) -> None:
        self._published_topics = set()
        if self._manifest_path is not None:
            if not self._manifest_path.exists():
                return _LOGGER.info(f"No Manifest found at: {self._manifest_path}")
            _LOGGER.info(f"Reading Manifest from: {self._manifest_path}")
            with self._manifest_path.open("r", encoding="utf-8") as file_handle:
                raw = yaml.safe_load(file_handle) or {}
            version = raw.get(ManifestConstants.VERSION, None)
            if not isinstance(version, str):
                return _LOGGER.error("Invalid version found in the Manifest. Version must be text")
            if version != Constants.APP_VERSION:
                _LOGGER.warn(f"Manifest was created with a different application version. Manifest Version: '{version}' - Application Version: '{Constants.APP_VERSION}'")
            topic_section = raw.get(ManifestConstants.TOPIC, None)
            if not isinstance(topic_section, list):
                return _LOGGER.error("Invalid topic section found in the Manifest. Topic must be a list")
            for topic in topic_section:
                if not isinstance(topic, str):
                    return _LOGGER.error(f"Each topic child must be a single value. Found: {topic}")
                self._published_topics.add(topic)
        _LOGGER.info(f"Read {len(self.published_topics)} Topics from the Manifest")

    def write_manifest(self) -> None:
        if self._manifest_path is not None and self._has_changes:
            try:
                if not self._manifest_path.exists():
                    _LOGGER.info(f"Creating manifest file at {self._manifest_path}")
                    Path.mkdir(self._manifest_path.parent, parents=True, exist_ok=True)
                _LOGGER.info(f"Writing {len(self.published_topics)} topics to the manifest")
                manifest_data: dict[str, list[str] | str] = {}
                manifest_data[ManifestConstants.VERSION] = Constants.APP_VERSION
                manifest_data[ManifestConstants.TOPIC] = list(self.published_topics)
                with self._manifest_path.open("w", encoding="utf-8") as file_handle:
                    yaml.dump(manifest_data, file_handle, default_flow_style=False)
                self._has_changes = False
                _LOGGER.info(f"Wrote {len(self.published_topics)} topics to the manifest")
            except Exception as e:
                _LOGGER.error(f"Failed to write {len(self.published_topics)} topics to the manifest: {e}")

    def add_topic(self, topic: str) -> None:
        if topic not in self.published_topics:
            self._has_changes = True
            self.published_topics.add(topic)

    def remove_topic(self, topic: str) -> None:
        if topic in self.published_topics:
            self._has_changes = True
            self.published_topics.remove(topic)
