import yaml
import os
from threading import RLock
from typing import Any

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "configs")
class ConfigService:
    """Hot-reloadable config store. Emits change events to subscribers."""
    def __init__(self):
        self._lock = RLock()
        self._data: dict[str, Any] = {}
        self._version = 0
        self._subscribers = []
        self.load_all()

    def load_all(self):
        for name in ["sla_policies", "calendar", "skills", "mandatory_fields"]:
            path = os.path.join(CONFIG_DIR, f"{name}.yaml")
            if os.path.exists(path):
                with open(path) as f:
                    self._data[name] = yaml.safe_load(f)

    def get(self, key: str) -> Any:
        with self._lock:
            return self._data.get(key)

    def reload(self, key: str | None = None):
        """Runtime change hook: reload one or all configs, bump version."""
        with self._lock:
            if key:
                path = os.path.join(CONFIG_DIR, f"{key}.yaml")
                with open(path) as f:
                    self._data[key] = yaml.safe_load(f)
            else:
                self.load_all()
            self._version += 1
            version = self._version
        for cb in self._subscribers:
            cb(key, version)

    def subscribe(self, callback):
        self._subscribers.append(callback)

    @property
    def version(self):
        return self._version

config = ConfigService()