import asyncio

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

    async def execute(self):
        self._logger.info("Schedule processor task started.")

        while True:
            schedules = self._schedule.pending_schedules
            current_time = self._utils.get_current_time()

            print(schedules)

            now_sec = self._utils.get_current_time()[5]
            sleep_time = 60 - now_sec
            if sleep_time <= 0:
                sleep_time = 60
            await asyncio.sleep(sleep_time)
