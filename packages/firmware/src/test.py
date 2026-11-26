import time

from lib.constants import BUTTON, BUZZER, STEPPER_DRAWER
from lib.picozero import Button, Speaker, Stepper

button = Button(BUTTON)
buzzer = Speaker(BUZZER)
stepper = Stepper(STEPPER_DRAWER)


def pressed():
    buzzer.play(440, 0.1)


button.when_activated = pressed

stepper.rotate(1 / 16, direction="cw")
# 1 / 3 -> drawer
# 1 / 16 -> discard

while True:
    time.sleep(1)
