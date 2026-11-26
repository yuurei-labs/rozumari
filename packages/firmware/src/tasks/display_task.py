import asyncio
import time

from lib.config import Config
from lib.i18n import translate as _t
from lib.schedule import Schedule
from lib.singleton import Singleton
from lib.utils import Utils
from modules.button import Button
from modules.st7735 import ST7735
from services.gen_link_qr import GenLinkQr


class DisplayTask(Singleton):
    def __init__(self) -> None:
        super().__init__()

        self._lcd = ST7735()
        self._config = Config().device
        self._utils = Utils()

        self._schedule = Schedule()
        self._last_schedule_snapshot: list = []

        self._button = Button()
        self._gen_link_qr = GenLinkQr()

    def layout(self) -> None:
        self._lcd.fill(ST7735.BLACK)

        name = self._config.get("name", self._config.get("model"))
        position = self._config.get("position")

        self._lcd.text(
            (4, 4), f"{name}{f' - {position}' if position else ''}", ST7735.WHITE
        )
        self._render_time(force=True)
        self._lcd.hline((4, 28), 152, ST7735.BLUE)

        self._lcd.text((4, 34), _t("lcd_time_items_status"), ST7735.WHITE)
        self._lcd.hline((4, 44), 152, ST7735.WHITE)

        self._last_date_hm = ""
        self._last_date_ss = ""

        self._last_schedule_snapshot = []
        self._render_schedule(force=True)

    async def execute(self) -> None:
        while True:
            self._render_time()
            self._render_schedule()

            if self._button.check_long_press(5000):
                await self._on_long_press_5s()

            await asyncio.sleep(1)

    async def _on_long_press_5s(self) -> None:
        self._lcd.fill(ST7735.BLACK)
        self._lcd.text((0, 60), _t("lcd_generating_qr"), ST7735.CYAN, center=True)

        matrix = await self._gen_link_qr.execute()
        if not matrix:
            self._lcd.fill(ST7735.BLACK)
            self._lcd.text((0, 60), _t("lcd_qr_failed"), ST7735.RED, center=True)
            await asyncio.sleep(2)
            self.layout()
            return

        self._draw_qr_matrix(matrix)

        self._button.clear_pressed()
        start_ms = time.ticks_ms()
        duration_ms = 60 * 1000

        while time.ticks_diff(time.ticks_ms(), start_ms) < duration_ms:
            if not self._button.is_active and self._button.consume_pressed():
                break
            await asyncio.sleep_ms(200)

        self.layout()

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
            self._lcd.text((0, 76), _t("lcd_no_schedules"), ST7735.WHITE, center=True)
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
            self._lcd.text((100, y), _t(f"status_{status}"), color)
            y += 12

    def _draw_qr_matrix(self, matrix: list[list[bool]]) -> None:
        self._lcd.fill(ST7735.BLACK)
        size = len(matrix)

        scale = 128 // size
        scale = max(scale, 1)

        qr_pixel_size = size * scale
        offset_x = (160 - qr_pixel_size) // 2
        offset_y = (128 - qr_pixel_size) // 2

        pad = 3
        bg_x = max(0, offset_x - pad)
        bg_y = max(0, offset_y - pad)
        bg_w = min(160 - bg_x, qr_pixel_size + pad * 2)
        bg_h = min(128 - bg_y, qr_pixel_size + pad * 2)
        self._lcd.fill_rect((bg_x, bg_y), (bg_w, bg_h), ST7735.WHITE)

        black_hi = (ST7735.BLACK >> 8) & 0xFF
        black_lo = ST7735.BLACK & 0xFF
        white_hi = (ST7735.WHITE >> 8) & 0xFF
        white_lo = ST7735.WHITE & 0xFF

        row_buf = bytearray(qr_pixel_size * scale * 2)

        for r, row in enumerate(matrix):
            idx = 0
            for cell in row:
                ch = black_hi if cell else white_hi
                cl = black_lo if cell else white_lo
                for _ in range(scale):
                    row_buf[idx] = ch
                    row_buf[idx + 1] = cl
                    idx += 2

            line_bytes = qr_pixel_size * 2
            for s in range(1, scale):
                start = s * line_bytes
                row_buf[start : start + line_bytes] = row_buf[0:line_bytes]

            y = offset_y + r * scale
            self._lcd.blit(offset_x, y, qr_pixel_size, scale, row_buf)
