import asyncio

from lib.config import Config
from lib.schedule import Schedule
from lib.singleton import Singleton
from lib.utils import Utils
from modules.st7735 import ST7735


class DisplayTask(Singleton):
    def __init__(self) -> None:
        super().__init__()

        self._lcd = ST7735()
        self._config = Config().device
        self._utils = Utils()

        self._schedule = Schedule()
        self._last_schedule_snapshot: list = []

    def layout(self) -> None:
        self._lcd.fill(ST7735.BLACK)

        name = self._config.get("name", self._config.get("model"))
        position = self._config.get("position")

        self._lcd.text(
            (4, 4), f"{name}{f' - {position}' if position else ''}", ST7735.WHITE
        )
        self._render_time(force=True)
        self._lcd.hline((4, 28), 152, ST7735.BLUE)

        self._lcd.text((4, 34), "Time  | Items | Status", ST7735.WHITE)
        self._lcd.hline((4, 44), 152, ST7735.WHITE)

        self._last_date_hm = ""
        self._last_date_ss = ""

        self._last_schedule_snapshot = []
        self._render_schedule(force=True)

    async def execute(self) -> None:
        while True:
            self._render_time()
            self._render_schedule()

            await asyncio.sleep(1)

    def _render_time(self, force: bool = False) -> None:
        current = self._utils.get_current_time()
        date_hm = f"{current[2]:02d}-{current[1]:02d}-{current[0]:04d} {current[3]:02d}:{current[4]:02d}"
        date_ss = f"{current[5]:02d}"

        x_static, x_seconds = 4, 106

        if force or date_hm != self._last_date_hm:
            self._last_date_hm = date_hm

            self._lcd.fill_rect((x_static, 16), (128, 8), ST7735.BLACK)
            self._lcd.text((x_static, 16), f"{date_hm}:", ST7735.CYAN)

        if force or date_ss != self._last_sec:
            self._last_sec = date_ss

            self._lcd.fill_rect((x_seconds, 16), (16, 8), ST7735.BLACK)
            self._lcd.text((x_seconds, 16), date_ss, ST7735.CYAN)

    def _render_schedule(self, force: bool = False) -> None:
        schedules = self._schedule.schedules
        current_snapshot = [
            (s.get("time"), len(s.get("items", [])), s.get("status")) for s in schedules
        ]

        if not force and current_snapshot == self._last_schedule_snapshot:
            return

        self._last_schedule_snapshot = current_snapshot
        self._lcd.fill_rect((0, 48), (160, 80), ST7735.BLACK)
        if not schedules:
            self._lcd.text((0, 76), "No schedules", ST7735.WHITE, center=True)
            return

        y = 48
        max_rows = 6

        for s in schedules[:max_rows]:
            raw_time = str(s.get("time", "00:00:00"))
            hh_mm = raw_time[:5]

            items_count = len(s.get("items", []))
            items_str = f"  {items_count}  "

            status = str(s.get("status", "pending")).lower()
            if status == "pending":
                color = ST7735.YELLOW
            elif status == "processing":
                color = ST7735.CYAN
            elif status == "completed":
                color = ST7735.GREEN
            elif status == "failed":
                color = ST7735.RED
            else:
                color = ST7735.WHITE

            info_str = f"{hh_mm:<5} | {items_str:<5} | "
            self._lcd.text((4, y), info_str, ST7735.WHITE)
            self._lcd.text((100, y), status, color)
            y += 12
