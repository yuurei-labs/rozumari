import json
import os

from lib.singleton import Singleton


class Schedule(Singleton):
    def __init__(self, path: str = "/data/schedule.json") -> None:
        super().__init__()
        if hasattr(self, "_data"):
            return

        self._path = path
        self._data: list = []
        self._ensure_dir()

    def load(self) -> None:
        try:
            with open(self._path, "r") as f:
                loaded = json.load(f)

            if isinstance(loaded, list):
                self._data = loaded
            else:
                self._data = []
        except OSError:
            self._data = []
            self.save()
        except Exception:
            self._data = []

    def save(self) -> bool:
        try:
            with open(self._path, "w") as f:
                json.dump(self._data, f)
            return True
        except Exception:
            return False

    def update(self, schedules: list) -> None:
        if isinstance(schedules, list):
            self._data = schedules
            self.save()

    @property
    def schedules(self) -> list:
        return self._data

    @property
    def pending_schedules(self) -> list:
        return [s for s in self._data if s.get("status") == "pending"]

    def update_status(self, schedule_id: str, new_status: str) -> bool:
        updated = False
        for s in self._data:
            if s.get("id") == schedule_id:
                s["status"] = new_status
                updated = True
                break
        if updated:
            self.save()
        return updated

    def _ensure_dir(self) -> None:
        folder = self._path.rpartition("/")[0]
        if not folder:
            return
        try:
            os.mkdir(folder)
        except OSError:
            pass
