import time

from lib.constants import BUTTON
from lib.picozero import Button as _Button
from lib.singleton import Singleton


class Button(Singleton):
    def __init__(self) -> None:
        super().__init__()
        if hasattr(self, "_btn"):
            return

        self._btn = _Button(BUTTON)
        self._pressed_flag = False
        self._press_start_ms: int | None = None
        self._long_press_triggered = False

        self._btn.when_activated = self._on_down
        self._btn.when_deactivated = self._on_up

    def _on_down(self) -> None:
        self._pressed_flag = True
        self._press_start_ms = time.ticks_ms()  # pyright: ignore[reportAttributeAccessIssue]
        self._long_press_triggered = False

    def _on_up(self) -> None:
        self._press_start_ms = None
        self._long_press_triggered = False

    @property
    def is_active(self) -> bool:
        return bool(self._btn.is_active)

    def clear_pressed(self) -> None:
        self._pressed_flag = False

    def consume_pressed(self) -> bool:
        if self._pressed_flag or self._btn.is_active:
            self._pressed_flag = False
            return True
        return False

    def check_long_press(self, duration_ms: int = 5000) -> bool:
        if self._btn.is_active:
            if self._press_start_ms is None:
                self._press_start_ms = time.ticks_ms()  # pyright: ignore[reportAttributeAccessIssue]
                self._long_press_triggered = False
            elif not self._long_press_triggered and (
                time.ticks_diff(time.ticks_ms(), self._press_start_ms) >= duration_ms
            ):
                self._long_press_triggered = True
                return True
        else:
            self._press_start_ms = None
            self._long_press_triggered = False

        return False
