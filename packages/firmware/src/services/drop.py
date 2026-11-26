import asyncio
import time

from machine import Pin
from micropython import const

from lib.config import Config
from lib.constants import (
    SENSOR_CHECK,
    SENSOR_DROP,
    SERVO00,
    SERVO01,
    SERVO10,
    SERVO11,
    STEPPER_DISCARD,
    STEPPER_DRAWER,
)
from lib.logger import Logger
from lib.picozero import Servo, Stepper
from lib.singleton import Singleton

try:
    from typing import TypedDict

    class Item(TypedDict):
        slot: str
        quantity: int
        isRequired: bool
except:
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

        self._servos: dict[str, Servo] = {
            "0-0": Servo(SERVO00),
            "0-1": Servo(SERVO01),
            "1-0": Servo(SERVO10),
            "1-1": Servo(SERVO11),
        }
        self._stepper_drawer = Stepper(STEPPER_DRAWER, step_sequence="half")
        self._stepper_discard = Stepper(STEPPER_DISCARD, step_sequence="half")

        self._sensor_drop = Pin(SENSOR_DROP, Pin.IN, Pin.PULL_UP)
        self._sensor_check = Pin(SENSOR_CHECK, Pin.IN, Pin.PULL_UP)

        self._drop_count = 0
        self._last_drop_ms = 0

        self._sensor_drop.irq(trigger=DROP_IRQ_TRIGGER, handler=self._on_pill_drop)

    async def execute(self, items: "list[Item]") -> bool:
        drop_timeout = int(self._config.timeout.get("drop", 5))
        for item in items:
            slot = item.get("slot", "")
            quantity = int(item.get("quantity", 1))

            success = await self._dispense_slot(slot, quantity, drop_timeout)
            if not success:
                return False

            await asyncio.sleep_ms(500)

        return True

    def _on_pill_drop(self, pin: Pin) -> None:
        now = time.ticks_ms()
        if time.ticks_diff(now, self._last_drop_ms) < 200:
            return

        if pin.value() == 0:
            self._last_drop_ms = now
            self._drop_count += 1

    async def _dispense_slot(
        self, slot: str, quantity: int, timeout_s: int = 3
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
