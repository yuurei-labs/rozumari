import asyncio
import time

import ntptime

from lib.config import Config
from lib.logger import Logger
from lib.singleton import Singleton


class Utils(Singleton):
    def __init__(self) -> None:
        super().__init__()
        self._config = Config()

    def get_current_time(self) -> tuple[int, ...]:
        timezone = int(self._config.general.get("timezone", "7"))
        return time.localtime(time.time() + timezone * 3600)

    def clamp(self, value: int, _min: int, _max: int) -> int:
        return max(_min, min(_max, value))

    def rgb(self, r: int, g: int, b: int, invert: bool = False) -> int:
        if invert:
            val = ((b & 0xF8) << 8) | ((g & 0xFC) << 3) | (r >> 3)
        else:
            val = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

        return val

    async def sync_time(self, retries: int = 5) -> bool:
        logger = Logger("NTP")
        logger.info("Syncing time...")

        ntp_hosts = [
            "time.google.com",
            "time.cloudflare.com",
            "time.windows.com",
            "pool.ntp.org",
        ]
        ntptime.timeout = 5

        for attempt in range(1, retries + 1):
            host = ntp_hosts[(attempt - 1) % len(ntp_hosts)]
            ntptime.host = host
            try:
                logger.info(f"Connecting to NTP server: {host}")
                ntptime.settime()
                logger.info("Time synced!")
                return True
            except Exception as e:
                logger.error(f"Sync failed ({retries - attempt} time(s) left): {e}")
                await asyncio.sleep(2)

        return False
