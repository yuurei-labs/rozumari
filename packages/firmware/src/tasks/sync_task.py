import asyncio

from lib.config import Config
from lib.logger import Logger
from lib.singleton import Singleton
from lib.utils import Utils
from services.sync_schedule import SyncSchedule


class SyncTask(Singleton):
    def __init__(self) -> None:
        """Initialize the daily synchronization task and its dependencies."""
        super().__init__()
        self._logger = Logger("SyncTask")
        self._config = Config()
        self._utils = Utils()
        self._sync_schedule = SyncSchedule()

        self._last_sync_date: str = ""

    async def execute(self) -> None:
        """Run the daily schedule synchronization loop.

        Checks the configured synchronization time and executes schedule
        synchronization once per day when the target time is reached.

        Records the date of successful synchronization to prevent duplicate
        execution. Retries failed synchronization during subsequent check
        cycles and logs any unexpected errors.

        Sleeps until the next 30-minute check interval between executions.
        """
        self._logger.info("Daily sync task started.")

        while True:
            try:
                target_time_str = self._config.general.get("syncTime", "04:00:00")[:5]
                t_hour, t_min = map(int, target_time_str.split(":"))
                target_minutes = t_hour * 60 + t_min

                current = self._utils.get_current_time()
                today_str = f"{current[0]:04d}-{current[1]:02d}-{current[2]:02d}"

                curr_hour = current[3]
                curr_min = current[4]
                current_minutes = curr_hour * 60 + curr_min

                if (
                    self._last_sync_date != today_str
                    and current_minutes >= target_minutes
                ):
                    if await self._sync_schedule.execute():
                        self._last_sync_date = today_str
                        self._logger.info("Daily sync completed successfully.")
                    else:
                        self._logger.warning(
                            "Daily sync failed. Will retry in next check cycle."
                        )

            except Exception as e:
                self._logger.error(f"Error in SyncTask loop: {e}")

            current = self._utils.get_current_time()
            now_min = current[4]
            now_sec = current[5]

            remaining_mins = 29 - (now_min % 30)
            sleep_time_seconds = remaining_mins * 60 + (60 - now_sec)

            if sleep_time_seconds < 10:
                sleep_time_seconds = 1800

            await asyncio.sleep(sleep_time_seconds)
