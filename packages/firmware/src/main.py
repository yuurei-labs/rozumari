import asyncio
import gc
import time

from machine import Pin, reset

from lib.config import Config
from lib.constants import MODE_SWITCH
from lib.i18n import translate as _t
from lib.logger import Logger
from lib.singleton import Singleton
from lib.utils import Utils
from modules.ble import BLE
from modules.st7735 import ST7735
from modules.wifi import WiFi
from services.sync_info import SyncInfo
from tasks.display_task import DisplayTask
from tasks.schedule_task import ScheduleTask
from tasks.subcribe_task import SubcribeTask
from tasks.sync_task import SyncTask


class Main(Singleton):
    def __init__(self) -> None:
        """Initialize the main application and its hardware components.

        Load the device configuration, initialize services and peripherals,
        register the mode-switch interrupt, and create background task handlers.
        """
        super().__init__()
        self._config = Config()
        self._config.load()

        self._logger = Logger("Prog")
        self._wifi = WiFi(self._config.device.get("name", ""))
        self._ble = BLE(self._config.device.get("name", ""))
        self._utils = Utils()
        self._lcd = ST7735()

        self._is_config_mode: bool | None = None
        self._mode_changed = True
        self._last_trigger = 0
        self._task: asyncio.Task | None = None

        self._sw = Pin(MODE_SWITCH, Pin.IN, Pin.PULL_UP)
        self._sw.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=self._sw_irq)

        self._display_task = DisplayTask()
        self._schedule_task = ScheduleTask()
        self._subcribe_task = SubcribeTask()
        self._sync_task = SyncTask()

    async def _normal_flow(self) -> None:
        """Run the application in normal operating mode.

        Collect garbage, initialize the display, connect to Wi-Fi, synchronize
        the system time and device information, then start the background tasks.

        Raises:
            OSError: If Wi-Fi connection, time synchronization, or information
                synchronization fails.
        """
        gc.collect()
        self._draw_header()

        ssid = self._config.wifi.get("ssid", "")
        password = self._config.wifi.get("password", "")

        steps = (
            (
                _t("lcd_connecting_wifi", ssid=ssid),
                self._wifi.connect(ssid=ssid, password=password),
                "WiFi connect failed",
            ),
            (_t("lcd_syncing_time"), self._utils.sync_time(), "Time sync failed"),
            (_t("lcd_syncing_info"), SyncInfo().execute(), "Info sync failed"),
        )
        for msg, coro, err in steps:
            self._lcd.fill_rect(pos=(0, 72), size=(160, 24), color=ST7735.BLACK)
            self._lcd.text(
                pos=(0, 72), text=msg, color=ST7735.WHITE, wrap=True, center=True
            )
            if not await coro:
                raise OSError(err)
            await asyncio.sleep(1)

        self._display_task.layout()
        bg_tasks = (
            asyncio.create_task(self._display_task.execute()),
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
        """Run the application in configuration mode.

        Display the configuration-mode instructions and the device BLE MAC
        address on the LCD.
        """
        self._draw_header()
        self._lcd.text(
            pos=(0, 80), text=_t("lcd_advertise_at"), color=ST7735.WHITE, center=True
        )
        self._lcd.text(
            pos=(0, 96), text=self._ble.get_mac(), color=ST7735.WHITE, center=True
        )

    async def execute(self) -> None:
        """Initialize the display and run the main application loop.

        Synchronize the operating mode whenever the mode-switch state changes
        and monitor the active mode task for completion.
        """
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
        """Release application resources and stop active services.

        Cancel the active mode task, disconnect Wi-Fi, stop BLE advertising,
        deinitialize the LCD, and log the cleanup completion.
        """
        if self._task:
            self._task.cancel()
        self._wifi.disconnect()
        self._ble.stop()
        self._lcd.deinit()
        self._logger.info("Cleanup completed.")

    async def _sync_mode(self) -> None:
        """Synchronize the application mode with the physical mode switch.

        Cancel the previous mode task, collect garbage, and start the
        corresponding configuration or normal operating flow.
        """
        is_cfg = self._sw.value() == 0
        if is_cfg == self._is_config_mode:
            return

        self._is_config_mode = is_cfg
        if self._task:
            self._task.cancel()
            await asyncio.sleep_ms(0)
        gc.collect()

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
        """Draw the application header on the LCD.

        Clear the display and render the application name and a horizontal
        separator line.
        """
        self._lcd.fill(ST7735.BLACK)
        self._lcd.text(
            pos=(0, 44), text="Rozumari", color=ST7735.WHITE, size=2, center=True
        )
        self._lcd.hline(pos=(16, 64), length=128, color=ST7735.BLUE)

    def _sw_irq(self, _: Pin) -> None:
        """Handle mode-switch state changes through a GPIO interrupt.

        Apply a 150 ms debounce interval before marking the application mode
        as changed.

        Args:
            _: The GPIO pin that triggered the interrupt.
        """
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
