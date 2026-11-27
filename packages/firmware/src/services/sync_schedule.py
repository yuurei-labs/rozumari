from lib.api import Api
from lib.schedule import Schedule
from lib.singleton import Singleton
from lib.utils import Utils


class SyncSchedule(Singleton):
    def __init__(self) -> None:
        """Initialize the API client, time utility, and schedule storage."""
        super().__init__()
        self._api = Api()
        self._utils = Utils()
        self._schedule = Schedule()

    async def execute(self) -> bool:
        """Synchronize today's schedules from the backend.

        Retrieves the current date, requests the schedules for that date,
        and updates the local schedule storage with the returned data.

        Returns:
            True if the response contains a valid schedule list and the local
            schedules are updated successfully; otherwise, False.
        """
        today = self._utils.get_current_time()
        today_str = f"{today[0]:04d}-{today[1]:02d}-{today[2]:02d}"

        resp = await self._api.get("/api/schedules/today", query={"date": today_str})
        data = resp.get("data")
        if not resp or not isinstance(data, list):
            return False

        self._schedule.update(data)

        return True
