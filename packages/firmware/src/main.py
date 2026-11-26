import asyncio
import gc
import time

from machine import Pin, reset

from lib.config import Config
from lib.constants import MODE_SWITCH
from lib.logger import Logger
from lib.singleton import Singleton
from lib.utils import Utils
from modules.ble import BLE
from modules.st7735 import ST7735
from modules.wifi import WiFi
from services.sync_info import SyncInfo
from tasks.schedule_task import ScheduleTask
from tasks.subcribe_task import SubcribeTask
from tasks.sync_task import SyncTask


class Main(Singleton):
    def __init__(self) -> None:
        super().__init__()
        self._config = Config()
        self._config.load()

        self._logger = Logger("Prog")
        self._wifi = WiFi()
        self._ble = BLE()
        self._utils = Utils()
        self._sync_info = SyncInfo()
        self._lcd = ST7735()

        self._is_config_mode: bool | None = None
        self._mode_changed = True
        self._last_trigger = 0
        self._task: asyncio.Task | None = None

        self._sw = Pin(MODE_SWITCH, Pin.IN, Pin.PULL_UP)
        self._sw.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=self._sw_irq)

        self._schedule_task = ScheduleTask()
        self._subcribe_task = SubcribeTask()
        self._sync_task = SyncTask()

    async def _normal_flow(self) -> None:
        self._draw_header()

        steps = (
            (
                f"Connecting to {self._config.wifi.get('ssid')}...",
                self._wifi.connect(),
                "WiFi connect failed",
            ),
            ("Syncing time...", self._utils.sync_time(), "Time sync failed"),
            ("Syncing info...", self._sync_info.execute(), "Info sync failed"),
        )
        for msg, coro, err in steps:
            self._lcd.fill_rect((0, 72), (160, 24), ST7735.BLACK)
            self._lcd.text((0, 72), msg, ST7735.WHITE, wrap=True, center=True)
            if not await coro:
                raise OSError(err)
            await asyncio.sleep(1)

        self._lcd.fill(ST7735.BLACK)

        bg_tasks = (
            asyncio.create_task(self._schedule_task.execute()),
            asyncio.create_task(self._subcribe_task.execute()),
            asyncio.create_task(self._sync_task.execute()),
        )
        try:
            await asyncio.gather(*bg_tasks)
        finally:
            for t in bg_tasks:
                t.cancel()
            gc.collect()

    async def _config_flow(self) -> None:
        self._draw_header()
        self._lcd.text((0, 80), "Advertise at", ST7735.WHITE, center=True)
        self._lcd.text((0, 96), self._ble.get_mac(), ST7735.WHITE, center=True)

    async def execute(self) -> None:
        self._lcd.init()
        self._lcd.rotation(1)
        while True:
            if self._mode_changed:
                self._mode_changed = False
                await self._sync_mode()
            if self._task and self._task.done():
                await self._task
            await asyncio.sleep_ms(50)

    def cleanup(self) -> None:
        if self._task:
            self._task.cancel()
        self._wifi.disconnect()
        self._ble.stop()
        self._lcd.deinit()
        self._logger.info("Cleanup completed.")

    async def _sync_mode(self) -> None:
        is_cfg = self._sw.value() == 0
        if is_cfg == self._is_config_mode:
            return

        self._is_config_mode = is_cfg
        if self._task:
            self._task.cancel()

        if is_cfg:
            self._logger.info("Switched to CONFIG MODE")
            self._wifi.disconnect()
            self._ble.start()
            self._task = asyncio.create_task(self._config_flow())
        else:
            self._logger.info("Switched to NORMAL MODE")
            self._config.load()
            self._ble.stop()
            self._task = asyncio.create_task(self._normal_flow())

    def _draw_header(self) -> None:
        self._lcd.fill(ST7735.BLACK)
        self._lcd.text((0, 44), "Rozumari", ST7735.WHITE, 2, center=True)
        self._lcd.hline((16, 64), 128, ST7735.BLUE)

    def _sw_irq(self, _: Pin) -> None:
        now = time.ticks_ms()
        if time.ticks_diff(now, self._last_trigger) > 150:
            self._last_trigger = now
            self._mode_changed = True


if __name__ == "__main__":
    main = Main()
    try:
        asyncio.run(main.execute())
    except OSError as e:
        main._logger.error(f"Critical failure: {e}. Rebooting in 3s...")
        main.cleanup()
        time.sleep(3)
        reset()
    except KeyboardInterrupt:
        main._logger.info("KeyboardInterrupt detected")
    finally:
        main.cleanup()
