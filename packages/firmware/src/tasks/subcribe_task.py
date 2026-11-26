import json

from lib.api import Api
from lib.logger import Logger
from lib.picozero import pico_led
from lib.singleton import Singleton
from services.sync_schedule import SyncSchedule


class SubcribeTask(Singleton):
    def __init__(self) -> None:
        super().__init__()

        self._api = Api()
        self._logger = Logger("Subcribe")

    async def execute(self):
        await self._api.subcribe("/api/devices/subscribe", self._on_message, timeout=15)

    async def _on_message(self, msg: str) -> None:
        try:
            command: dict = json.loads(msg)
            self._logger.info(f"Received: {msg}")

            action = command.get("action")

            if action == "led":
                payload = command.get("payload", "0")
                value = int(payload)
                pico_led.value = value
                self._logger.info(f"Led: {'ON' if value else 'OFF'}")

            if action == "sync_schedule":
                if await SyncSchedule().execute():
                    self._logger.info("Schedule synced!")
                else:
                    self._logger.error("Schedule sync failed!")

        except Exception as e:
            self._logger.error(f"Error handling message: {e}")
