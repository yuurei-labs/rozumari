import json
import os

from lib.singleton import Singleton


class Schedule(Singleton):
    def __init__(self, path: str = "/data/schedule.json") -> None:
        """Initialize the schedule manager.

        Args:
            path: Path to the JSON schedule file.
        """
        super().__init__()
        if hasattr(self, "_data"):
            return

        self._path = path
        self._data: list = []
        self._ensure_dir()

    def load(self) -> None:
        """Load schedules from the JSON file.

        Initializes an empty schedule list if the file does not exist or contains
        invalid data.
        """
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
        """Save the current schedules to the JSON file.

        Returns:
            True if the schedules were saved successfully, otherwise False.
        """
        try:
            with open(self._path, "w") as f:
                json.dump(self._data, f)
            return True
        except Exception:
            return False

    def update(self, schedules: list) -> None:
        """Replace the current schedules and save the changes.

        Args:
            schedules: New list of schedules.
        """
        if isinstance(schedules, list):
            self._data = schedules
            self.save()

    @property
    def schedules(self) -> list:
        """Return all stored schedules."""
        return self._data

    @property
    def pending_schedules(self) -> list:
        """Return schedules with a pending status."""
        return [s for s in self._data if s.get("status") == "pending"]

    def update_status(self, schedule_id: str, new_status: str) -> bool:
        """Update the status of a schedule by its ID.

        Args:
            schedule_id: ID of the schedule to update.
            new_status: New status to assign.

        Returns:
            True if the schedule was found and updated, otherwise False.
        """
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
        """Ensure the parent directory of the schedule file exists."""
        folder = self._path.rpartition("/")[0]
        if not folder:
            return
        try:
            os.mkdir(folder)
        except OSError:
            pass
