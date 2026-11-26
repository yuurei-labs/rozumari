import asyncio
from time import sleep_ms, ticks_diff, ticks_ms

from network import WLAN, hostname

from lib.config import Config
from lib.logger import Logger
from lib.singleton import Singleton


class WiFi(Singleton):
    def __init__(self, name: str, mode: int = WLAN.IF_STA) -> None:
        hostname(name)

        self._wlan = WLAN(mode)
        self._config = Config().wifi
        self._logger = Logger("WiFi")

    def is_connected(self) -> bool:
        return self._wlan.isconnected()

    async def connect(
        self,
        ssid: str,
        password: str,
        timeout: int = 20,
        retries: int = 5,
    ) -> bool:
        while retries > 0 and not self._wlan.isconnected():
            self.disconnect()
            self._wlan.active(True)
            self._wlan.connect(ssid, password)
            self._logger.info(f"Connecting to {ssid}...")

            start = ticks_ms()
            while not self._wlan.isconnected():
                if ticks_diff(ticks_ms(), start) >= timeout * 1000:
                    break
                await asyncio.sleep_ms(100)

            if self._wlan.isconnected():
                self._logger.info(f"Connected: {self._wlan.ifconfig()[0]}")
                return True
            else:
                retries -= 1
                self._logger.error(f"Connection failed ({retries} time(s) left)")
                await asyncio.sleep(2)

        return False

    def disconnect(self) -> None:
        if self._wlan.isconnected():
            self._wlan.disconnect()
            sleep_ms(500)
        if self._wlan.active():
            self._wlan.active(False)
            sleep_ms(500)
