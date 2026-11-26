import asyncio
import gc

from lib.logger import Logger
from lib.schedule import Schedule
from lib.singleton import Singleton
from lib.utils import Utils
from services.drop import Drop


class ScheduleTask(Singleton):
    def __init__(self) -> None:
        super().__init__()
        self._logger = Logger("ScheduleTask")
        self._drop = Drop()
        self._utils = Utils()
        self._schedule = Schedule()
        self._schedule.load()

    async def execute(self) -> None:
        self._logger.info("Schedule processor task started.")

        while True:
            try:
                current = self._utils.get_current_time()
                current_date = f"{current[0]:04d}-{current[1]:02d}-{current[2]:02d}"
                current_time = f"{current[3]:02d}:{current[4]:02d}"

                pending_schedules = self._schedule.pending_schedules

                for s in pending_schedules:
                    s_date = s.get("date")
                    s_time = s.get("time", "00:00:00")[:5]
                    s_id = s.get("id")

                    if s_date == current_date and s_time == current_time:
                        self._logger.info(
                            f"Triggering schedule [{s_id}] at {current_date} {current_time}"
                        )

                        items = s.get("items", [])

                        self._schedule.update_status(s_id, "processing")
                        if await self._drop.execute(items):
                            self._schedule.update_status(s_id, "completed")
                            if self._drop.optional_failures:
                                self._logger.warning(
                                    f"Schedule [{s_id}] completed with optional failures: "
                                    f"{[i.get('slot') for i in self._drop.optional_failures]}"
                                )
                            else:
                                self._logger.info(
                                    f"Schedule [{s_id}] completed successfully!"
                                )
                        else:
                            self._schedule.update_status(s_id, "failed")
                            self._logger.error(
                                f"Schedule [{s_id}] failed! Required items failed: "
                                f"{[i.get('slot') for i in self._drop.required_failures]}"
                            )

            except Exception as e:
                self._logger.error(f"Error in ScheduleTask loop: {e}")
            finally:
                gc.collect()

            now_sec = self._utils.get_current_time()[5]
            sleep_time = 60 - now_sec
            if sleep_time <= 0:
                sleep_time = 60

            await asyncio.sleep(sleep_time)
