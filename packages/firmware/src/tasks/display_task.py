import asyncio
import gc
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
        """Initialize the display task and its dependencies."""
        super().__init__()

        self._lcd = ST7735()
        self._config = Config().device
        self._utils = Utils()

        self._schedule = Schedule()
        self._last_schedule_snapshot: list = []

        self._button = Button()
        self._gen_link_qr = GenLinkQr()

    def layout(self) -> None:
        """Initialize the LCD layout and render the initial screen.

        Resets cached display state and renders the current time and schedule.
        """
        self._lcd.fill(ST7735.BLACK)

        name = self._config.get("name", self._config.get("model"))
        position = self._config.get("position")

        self._lcd.text(
            pos=(4, 4),
            text=f"{name}{f' - {position}' if position else ''}",
            color=ST7735.WHITE,
        )
        self._render_time(force=True)
        self._lcd.hline(pos=(4, 28), length=152, color=ST7735.BLUE)

        self._lcd.text(
            pos=(4, 34), text=_t("lcd_time_items_status"), color=ST7735.WHITE
        )
        self._lcd.hline(pos=(4, 44), length=152, color=ST7735.WHITE)

        self._last_date_hm = ""
        self._last_date_ss = ""

        self._last_schedule_snapshot = []
        self._render_schedule(force=True)

    async def execute(self) -> None:
        """Run the main display loop.

        Periodically updates the displayed time and schedules, checks for
        long button presses, and performs garbage collection every 60 seconds.
        """
        last_gc_ms = time.ticks_ms()

        while True:
            self._render_time()
            self._render_schedule()

            if self._button.check_long_press(5000):
                await self._on_long_press_5s()

            if time.ticks_diff(time.ticks_ms(), last_gc_ms) >= 60_000:
                gc.collect()
                last_gc_ms = time.ticks_ms()

            await asyncio.sleep(1)

    async def _on_long_press_5s(self) -> None:
        """Handle a button long press by displaying a pairing QR code.

        Generates and displays a QR code, then waits for a button press or
        a 60-second timeout before restoring the default display layout.
        """
        self._lcd.fill(ST7735.BLACK)
        self._lcd.text(
            pos=(0, 60), text=_t("lcd_generating_qr"), color=ST7735.CYAN, center=True
        )

        matrix = await self._gen_link_qr.execute()
        if not matrix:
            self._lcd.fill(ST7735.BLACK)
            self._lcd.text(
                pos=(0, 60), text=_t("lcd_qr_failed"), color=ST7735.RED, center=True
            )
            await asyncio.sleep(2)
            self.layout()
            gc.collect()
            return

        self._draw_qr_matrix(matrix)
        del matrix
        gc.collect()

        self._button.clear_pressed()
        start_ms = time.ticks_ms()
        duration_ms = 60 * 1000

        while time.ticks_diff(time.ticks_ms(), start_ms) < duration_ms:
            if not self._button.is_active and self._button.consume_pressed():
                break
            await asyncio.sleep_ms(200)

        self.layout()

    def _render_time(self, force: bool = False) -> None:
        """Render the current date and time on the LCD.

        Updates only the portions of the display that have changed unless
        a forced refresh is requested.

        Args:
            force: Whether to force a complete time display refresh.
        """
        current = self._utils.get_current_time()
        date_hm = f"{current[2]:02d}-{current[1]:02d}-{current[0]:04d} {current[3]:02d}:{current[4]:02d}"
        date_ss = f"{current[5]:02d}"

        x_static, x_seconds = 4, 106

        if force or date_hm != self._last_date_hm:
            self._last_date_hm = date_hm

            self._lcd.fill_rect(pos=(x_static, 16), size=(128, 8), color=ST7735.BLACK)
            self._lcd.text(pos=(x_static, 16), text=f"{date_hm}:", color=ST7735.CYAN)

        if force or date_ss != self._last_sec:
            self._last_sec = date_ss

            self._lcd.fill_rect(pos=(x_seconds, 16), size=(16, 8), color=ST7735.BLACK)
            self._lcd.text(pos=(x_seconds, 16), text=date_ss, color=ST7735.CYAN)

    def _render_schedule(self, force: bool = False) -> None:
        """Render the current schedule list on the LCD.

        Displays schedule times, item counts, and status indicators. Skips
        rendering if the schedule data has not changed unless forced.

        Args:
            force: Whether to force a schedule display refresh.
        """
        schedules = self._schedule.schedules
        current_snapshot = [
            (s.get("time"), len(s.get("items", [])), s.get("status")) for s in schedules
        ]

        if not force and current_snapshot == self._last_schedule_snapshot:
            return

        self._last_schedule_snapshot = current_snapshot
        self._lcd.fill_rect(pos=(0, 48), size=(160, 80), color=ST7735.BLACK)
        if not schedules:
            self._lcd.text(
                pos=(0, 76),
                text=_t("lcd_no_schedules"),
                color=ST7735.WHITE,
                center=True,
            )
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
            self._lcd.text(pos=(4, y), text=info_str, color=ST7735.WHITE)
            self._lcd.text(pos=(100, y), text=_t(f"status_{status}"), color=color)
            y += 12

    def _draw_qr_matrix(self, matrix: list[list[bool]]) -> None:
        """Render a QR code matrix on the LCD.

        Scales and centers the QR code within the display boundaries and
        draws its modules using RGB565 pixel data.

        Args:
            matrix: Two-dimensional boolean matrix representing the QR code.
        """
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
        self._lcd.fill_rect(pos=(bg_x, bg_y), size=(bg_w, bg_h), color=ST7735.WHITE)

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
            self._lcd.blit(x=offset_x, y=y, w=qr_pixel_size, h=scale, data=row_buf)
