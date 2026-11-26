import asyncio
import time

from machine import Pin
from micropython import const

from lib.config import Config
from lib.constants import (
    BUZZER,
    SENSOR_CHECK,
    SENSOR_DROP,
    SERVO00,
    SERVO01,
    SERVO10,
    SERVO11,
    STEPPER_DISCARD,
    STEPPER_DRAWER,
)
from lib.i18n import translate as _t
from lib.logger import Logger
from lib.picozero import Servo, Speaker, Stepper
from lib.singleton import Singleton
from modules.button import Button
from services.notify import Notify

try:
    from typing import TypedDict

    class Item(TypedDict):
        slot: str
        medicine: str
        quantity: int
        isRequired: bool
except Exception:
    pass

SERVO_SLOW_SPEED = const(0.56)
DROP_IRQ_TRIGGER = Pin.IRQ_FALLING


class Drop(Singleton):
    def __init__(self) -> None:
        super().__init__()
        if hasattr(self, "_servos"):
            return

        self._logger = Logger("Drop")
        self._config = Config()
        self._notify = Notify()

        self._servos: dict[str, Servo] = {
            "0-0": Servo(SERVO00),
            "0-1": Servo(SERVO01),
            "1-0": Servo(SERVO10),
            "1-1": Servo(SERVO11),
        }

        self._stepper_drawer = Stepper(STEPPER_DRAWER)
        self._stepper_discard = Stepper(STEPPER_DISCARD)

        self._sensor_drop = Pin(SENSOR_DROP, Pin.IN, Pin.PULL_UP)
        self._sensor_check = Pin(SENSOR_CHECK, Pin.IN, Pin.PULL_UP)

        self._buzzer = Speaker(BUZZER)
        self._button = Button()

        self._drop_count = 0
        self._last_drop_ms = 0
        self._check_detected = False
        self._last_check_ms = 0

        self.optional_failures: list[Item] = []
        self.required_failures: list[Item] = []

        self._sensor_drop.irq(trigger=DROP_IRQ_TRIGGER, handler=self._on_pill_drop)

    def _on_pill_drop(self, pin: Pin) -> None:
        now = time.ticks_ms()
        if time.ticks_diff(now, self._last_drop_ms) < 200:
            return
        if pin.value() == 0:
            self._last_drop_ms = now
            self._drop_count += 1

    def _on_pill_check(self, pin: Pin) -> None:
        now = time.ticks_ms()
        if time.ticks_diff(now, self._last_check_ms) < 200:
            return
        if pin.value() == 0:
            self._last_check_ms = now
            self._check_detected = True

    async def execute(
        self, items: "list[Item] | list[dict]", schedule_id: str | None = None
    ) -> bool:
        self.optional_failures.clear()
        self.required_failures.clear()

        drop_timeout = int(self._config.timeout.get("drop", 5))
        open_timeout = int(self._config.timeout.get("open", 10))
        close_timeout = int(self._config.timeout.get("close", 10))

        for item in items:
            slot = str(item.get("slot", ""))
            medicine = str(item.get("medicine", "Unknown"))
            quantity = int(item.get("quantity", 1))
            is_required = bool(item.get("isRequired", True))

            if not await self._dispense_slot(slot, quantity, drop_timeout):
                typed_item: Item = {
                    "slot": slot,
                    "quantity": quantity,
                    "medicine": medicine,
                    "isRequired": is_required,
                }
                if is_required:
                    self.required_failures.append(typed_item)
                    self._logger.error(
                        f"Drop failed for REQUIRED item at slot {slot} (qty: {quantity})!"
                    )
                else:
                    self.optional_failures.append(typed_item)
                    self._logger.warning(
                        f"Drop failed for OPTIONAL item at slot {slot} (qty: {quantity}). Continuing..."
                    )

            await asyncio.sleep_ms(500)

        if self.required_failures:
            msg = _t("notify_required_failures", count=len(self.required_failures))

            self._logger.error(msg)
            await self._notify.send(
                "error",
                _t("notify_schedule_failed" if schedule_id else "notify_drop_failed"),
                msg,
                {
                    "required_failures": self.required_failures,
                    "optional_failures": self.optional_failures,
                },
                schedule_id,
            )
            return False

        if self.optional_failures:
            self._logger.warning(
                f"Dispense finished with {len(self.optional_failures)} optional failure(s), proceeding to open drawer."
            )

        self._logger.info("Opening drawer...")
        self._stepper_drawer.rotate(1 / 6, direction="cw")
        await asyncio.sleep_ms(300)

        self._logger.info(f"Waiting up to {open_timeout}s for user to take medicine...")
        await self._wait_for_user_or_timeout(open_timeout)

        self._logger.info("Closing drawer...")
        self._stepper_drawer.rotate(1 / 6, direction="ccw")
        await asyncio.sleep_ms(300)

        self._logger.info(
            f"Opening discard gate and checking left-over pills for {close_timeout}s..."
        )
        self._check_detected = False
        self._last_check_ms = 0
        self._sensor_check.irq(trigger=DROP_IRQ_TRIGGER, handler=self._on_pill_check)

        try:
            self._stepper_discard.rotate(1 / 16, direction="cw")

            start_check_ms = time.ticks_ms()
            close_timeout_ms = close_timeout * 1000

            while time.ticks_diff(time.ticks_ms(), start_check_ms) < close_timeout_ms:
                if self._check_detected or self._sensor_check.value() == 0:
                    msg = _t("notify_untaken_medicine")
                    self._logger.error(msg)
                    self._stepper_discard.rotate(1 / 16, direction="ccw")
                    await self._notify.send(
                        "error",
                        _t("notify_medicine_not_taken"),
                        msg,
                        {"optional_failures": self.optional_failures},
                        schedule_id,
                    )
                    return False

                await asyncio.sleep_ms(50)

        finally:
            self._sensor_check.irq(handler=None)

        self._logger.info(
            "No left-over pills detected. Closing discard gate (1/16, ccw)..."
        )
        self._stepper_discard.rotate(1 / 16, direction="ccw")

        if self.optional_failures:
            msg = _t(
                "notify_dispense_optional_failures", count=len(self.optional_failures)
            )

            self._logger.warning(msg)
            await self._notify.send(
                "warning",
                _t("notify_schedule_warning" if schedule_id else "notify_drop_warning"),
                msg,
                {"optional_failures": self.optional_failures},
                schedule_id,
            )
        else:
            msg = _t("notify_dispense_success")
            self._logger.info(msg)
            await self._notify.send(
                "info",
                _t(
                    "notify_schedule_completed"
                    if schedule_id
                    else "notify_drop_completed"
                ),
                msg,
                {},
                schedule_id,
            )

        self._logger.info("Medicine schedule cycle completed successfully!")
        return True

    async def _wait_for_user_or_timeout(self, timeout_s: int) -> None:
        self._button.clear_pressed()
        start_ms = time.ticks_ms()
        timeout_ms = timeout_s * 1000
        last_beep_ms = time.ticks_ms() - 1000  # pyright: ignore[reportOperatorIssue]

        while time.ticks_diff(time.ticks_ms(), start_ms) < timeout_ms:
            if self._button.consume_pressed():
                self._logger.info("User pressed button!")
                self._buzzer.play(880, 0.1)
                break

            now = time.ticks_ms()
            if time.ticks_diff(now, last_beep_ms) >= 600:
                last_beep_ms = now
                self._buzzer.play(440, 0.1)

            await asyncio.sleep_ms(50)
        else:
            self._logger.warning(
                f"Open timeout ({timeout_s}s) reached without button press."
            )

    async def _dispense_slot(
        self, slot: str, quantity: int, timeout_s: int = 5
    ) -> bool:
        servo = self._servos.get(slot)
        if not servo:
            self._logger.error(f"Invalid slot: {slot}")
            return False

        if quantity <= 0:
            return True

        self._logger.info(f"Slot {slot}: Dispensing {quantity} pill(s)...")
        self._drop_count = 0
        last_seen_count = 0
        start_ms = time.ticks_ms()
        timeout_ms = timeout_s * 1000

        try:
            servo.value = SERVO_SLOW_SPEED

            while self._drop_count < quantity:
                if self._drop_count > last_seen_count:
                    last_seen_count = self._drop_count
                    start_ms = time.ticks_ms()
                    self._logger.info(
                        f"Slot {slot}: Dropped {self._drop_count}/{quantity}"
                    )
                    if self._drop_count < quantity:
                        servo.off()
                        await asyncio.sleep_ms(150)
                        servo.value = SERVO_SLOW_SPEED

                if time.ticks_diff(time.ticks_ms(), start_ms) > timeout_ms:
                    self._logger.error(
                        f"Slot {slot}: Timeout after {timeout_s}s! "
                        f"Only dropped {self._drop_count}/{quantity}"
                    )
                    return False

                await asyncio.sleep_ms(10)

            self._logger.info(f"Slot {slot}: Completed ({quantity}/{quantity})")
            return True

        finally:
            servo.off()
