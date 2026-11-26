try:
    from collections.abc import Callable
except:
    pass

from lib.config import Config
from lib.singleton import Singleton


class BleService(Singleton):
    def __init__(self, handle_send: "Callable[[str], None]") -> None:
        super().__init__()
        self._handle_send = handle_send

        self._config = Config()

    def execute(self, msg: str) -> None:
        try:
            if msg == "ping":
                self._handle_send("pong")

            if msg.startswith("wifi"):
                _, ssid, password = msg.split(":")
                self._config.update("wifi", {"ssid": ssid, "password": password})
                self._handle_send("WiFi config saved!")

            elif msg.startswith("general"):
                _, timezone, sync_time, language = msg.split(":")
                self._config.update(
                    "general",
                    {
                        "timezone": int(timezone),
                        "syncTime": sync_time,
                        "language": language,
                    },
                )
                self._handle_send("General config saved!")

            elif msg.startswith("timeout"):
                _, drop, open, close = msg.split(":")
                self._config.update(
                    "timeout",
                    {"drop": int(drop), "open": int(open), "close": int(close)},
                )
                self._handle_send("Timeout config saved!")

        except Exception as e:
            self._handle_send(f"Config error: {e}")
