import json

from lib.api import Api
from lib.logger import Logger
from lib.picozero import pico_led
from lib.singleton import Singleton


class SubcribeTask(Singleton):
    def __init__(self) -> None:
        super().__init__()

        self._api = Api()
        self._logger = Logger("Subcribe")

    async def execute(self):
        await self._api.subcribe("/api/devices/subscribe", self._on_message, timeout=15)

    async def _on_message(self, msg: str) -> None:
        try:
            payload: dict = json.loads(msg)
            self._logger.info(f"Received: {msg}")

            if payload.get("action") == "led":
                value = int(payload.get("payload", "0"))
                pico_led.value = value

        except Exception as e:
            self._logger.error(f"Error handling message: {e}")
