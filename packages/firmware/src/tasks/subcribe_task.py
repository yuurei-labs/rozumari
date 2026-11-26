import asyncio
import gc
import json

from lib.api import Api
from lib.i18n import translate as _t
from lib.logger import Logger
from lib.picozero import pico_led
from lib.singleton import Singleton
from services.drop import Drop
from services.notify import Notify
from services.sync_info import SyncInfo
from services.sync_schedule import SyncSchedule
from tasks.display_task import DisplayTask

try:
    from services.drop import Item
except Exception:
    pass


class SubcribeTask(Singleton):
    def __init__(self) -> None:
        super().__init__()

        self._api = Api()
        self._notify = Notify()
        self._logger = Logger("Subcribe")

    async def execute(self):
        await self._api.subcribe("/api/devices/subscribe", self._on_message, timeout=15)

    async def _on_message(self, msg: str) -> None:
        command: dict | None = None

        try:
            gc.collect()
            command = json.loads(msg)
            if command is None:
                return

            action = command.get("action")
            self._logger.info(f"Received action: {action}")

            if action == "led":
                payload = command.get("payload", "0")
                value = int(payload)
                pico_led.value = value
                self._logger.info(f"Led: {'ON' if value else 'OFF'}")

            if action == "sync_info":
                await self._notify.emit(
                    {"type": "info", "content": _t("emit_sync_info_received")}
                )

                await asyncio.sleep_ms(500)
                if await SyncInfo().execute():
                    self._logger.info("Info synced!")
                    await self._notify.emit(
                        {"type": "success", "content": _t("emit_sync_info_success")}
                    )

                    DisplayTask().layout()
                else:
                    self._logger.error("Info sync failed!")
                    await self._notify.emit(
                        {"type": "error", "content": _t("emit_sync_info_failed")}
                    )

            if action == "sync_schedule":
                await self._notify.emit(
                    {"type": "info", "content": _t("emit_sync_schedule_received")}
                )

                await asyncio.sleep_ms(500)
                if await SyncSchedule().execute():
                    self._logger.info("Schedule synced!")
                    await self._notify.emit(
                        {"type": "success", "content": _t("emit_sync_schedule_success")}
                    )
                else:
                    self._logger.error("Schedule sync failed!")
                    await self._notify.emit(
                        {"type": "error", "content": _t("emit_sync_schedule_failed")}
                    )

            if action == "drop":
                await self._notify.emit(
                    {"type": "info", "content": _t("emit_drop_received")}
                )

                raw_items = command.get("payload", [])
                if not isinstance(raw_items, list):
                    raise ValueError("Drop payload must be a list")

                items: list[Item] = (  # pyright: ignore[reportAssignmentType]
                    item
                    for item in raw_items
                    if isinstance(item, dict) and item.get("slot")
                )

                await asyncio.sleep_ms(500)
                if await Drop().execute(items):
                    self._logger.info("Drop success!")
                    await self._notify.emit(
                        {"type": "success", "content": _t("emit_drop_success")}
                    )
                else:
                    self._logger.error("Drop failed!")
                    await self._notify.emit(
                        {"type": "error", "content": _t("emit_drop_failed")}
                    )

        except Exception:
            gc.collect()

        finally:
            if command is not None:
                del command
            gc.collect()
