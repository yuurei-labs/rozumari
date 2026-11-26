import json
import os

from lib.singleton import Singleton


class Config(Singleton):
    def __init__(self, path: str = "/data/config.json") -> None:
        super().__init__()
        if hasattr(self, "_data"):
            return

        self._path = path
        self._data: dict = {}
        self._ensure_dir()

    def load(self) -> None:
        try:
            with open(self._path, "r") as f:
                loaded = json.load(f)

            self._data = {}
            for section, defaults in self._DEFAULT.items():
                self._data[section] = defaults.copy()
                if isinstance(loaded.get(section), dict):
                    self._data[section].update(loaded[section])

        except OSError:
            self._data = {k: v.copy() for k, v in self._DEFAULT.items()}
            self.save()
        except Exception:
            self._data = {k: v.copy() for k, v in self._DEFAULT.items()}

    def save(self) -> bool:
        try:
            with open(self._path, "w") as f:
                json.dump(self._data, f)
            return True
        except Exception:
            return False

    def update(self, section: str, values: dict) -> None:
        if section in self._data:
            self._data[section].update(values)

        self.save()

    @property
    def general(self) -> dict:
        return self._data["general"]

    @property
    def wifi(self) -> dict:
        return self._data["wifi"]

    @property
    def api(self) -> dict:
        return self._data["api"]

    @property
    def device(self) -> dict:
        return self._data["device"]

    @property
    def timeout(self) -> dict:
        return self._data["timeout"]

    def _ensure_dir(self) -> None:
        folder = self._path.rpartition("/")[0]
        if not folder:
            return

        try:
            os.mkdir(folder)
        except OSError:
            pass

    _DEFAULT: dict[str, dict] = {  # noqa: RUF012
        "general": {
            "timezone": 7,
            "syncTime": "04:00:00",
            "language": "vi",
        },
        "wifi": {
            "ssid": "",
            "password": "",
        },
        "api": {
            "url": "",
            "token": "",
        },
        "device": {
            "id": "",
            "name": "Rozumari",
            "model": "",
            "position": "",
        },
        "timeout": {
            "drop": 5,
            "open": 10,
            "close": 10,
        },
    }
