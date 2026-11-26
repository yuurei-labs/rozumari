import json

from lib.api import Api
from lib.logger import Logger
from lib.picozero import pico_led
from lib.singleton import Singleton
from services.drop import Drop
from services.sync_info import SyncInfo
from services.sync_schedule import SyncSchedule

try:
    from services.drop import Item
except Exception:
    pass


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

            if action == "sync_info":
                if await SyncInfo().execute():
                    self._logger.info("Info synced!")
                else:
                    self._logger.error("Info sync failed!")

            if action == "sync_schedule":
                if await SyncSchedule().execute():
                    self._logger.info("Schedule synced!")
                else:
                    self._logger.error("Schedule sync failed!")

            if action == "drop":
                raw_items = command.get("payload", [])
                items: list[Item] = [
                    {
                        "slot": str(item.get("slot", "")),
                        "quantity": int(item.get("quantity", 1)),
                        "isRequired": True,
                    }
                    for item in raw_items
                    if isinstance(item, dict) and item.get("slot")
                ]

                if await Drop().execute(items):
                    self._logger.info("Drop success!")
                else:
                    self._logger.info("Drop failed!")

        except Exception as e:
            self._logger.error(f"Error handling message: {e}")
