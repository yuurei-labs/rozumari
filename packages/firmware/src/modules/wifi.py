import asyncio
from time import sleep_ms, ticks_diff, ticks_ms

from network import WLAN, hostname

from lib.config import Config
from lib.logger import Logger
from lib.singleton import Singleton


class WiFi(Singleton):
    def __init__(self, name: str, mode: int = WLAN.IF_STA) -> None:
        """Initialize the Wi-Fi manager.

        Args:
            name: Device hostname.
            mode: WLAN operating mode. Defaults to station mode.
        """
        hostname(name)

        self._wlan = WLAN(mode)
        self._config = Config().wifi
        self._logger = Logger("WiFi")

    async def connect(
        self,
        *,
        ssid: str,
        password: str,
        timeout: int = 20,
        retries: int = 5,
    ) -> bool:
        """Connect to a Wi-Fi network with timeout and retry handling.

        Attempts to establish a connection until successful or the retry limit
        is reached.

        Args:
            ssid: Wi-Fi network name.
            password: Wi-Fi network password.
            timeout: Maximum connection time per attempt in seconds.
            retries: Maximum number of connection attempts.

        Returns:
            True if the connection succeeds, otherwise False.
        """
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
        """Disconnect from the current Wi-Fi network and deactivate the interface."""
        if self._wlan.isconnected():
            self._wlan.disconnect()
            sleep_ms(500)
        if self._wlan.active():
            self._wlan.active(False)
            sleep_ms(500)

    @property
    def is_connected(self) -> bool:
        """Check whether the Wi-Fi interface is connected.

        Returns:
            True if connected to a Wi-Fi network, otherwise False.
        """
        return self._wlan.isconnected()
