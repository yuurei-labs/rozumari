import time

from lib.constants import BUTTON
from lib.picozero import Button as _Button
from lib.singleton import Singleton


class Button(Singleton):
    def __init__(self) -> None:
        """Initialize the button handler and register press event callbacks."""
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
        """Handle the button press event.

        Sets the pressed flag, records the press start time, and resets the
        long-press detection state.
        """
        self._pressed_flag = True
        self._press_start_ms = time.ticks_ms()  # pyright: ignore[reportAttributeAccessIssue]
        self._long_press_triggered = False

    def _on_up(self) -> None:
        """Handle the button release event.

        Resets the press start time and long-press detection state.
        """
        self._press_start_ms = None
        self._long_press_triggered = False

    @property
    def is_active(self) -> bool:
        """Return whether the button is currently being held down."""
        return bool(self._btn.is_active)

    def clear_pressed(self) -> None:
        """Clear the stored button press flag."""
        self._pressed_flag = False

    def consume_pressed(self) -> bool:
        """Check and consume a button press event.

        Returns:
            True if a press event is detected, otherwise False.
        """
        if self._pressed_flag or self._btn.is_active:
            self._pressed_flag = False
            return True
        return False

    def check_long_press(self, duration_ms: int = 5000) -> bool:
        """Check whether the button has been held for the specified duration.

        Args:
            duration_ms: Minimum hold duration in milliseconds.

        Returns:
            True once when the hold duration is reached, otherwise False.
        """
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
