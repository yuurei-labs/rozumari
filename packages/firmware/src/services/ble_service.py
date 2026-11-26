try:
    from collections.abc import Callable
except:
    pass

import json
import time

import network

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
                _, ssid, password = msg.split(".")
                if self._test_wifi(ssid, password):
                    self._config.update("wifi", {"ssid": ssid, "password": password})
                    self._send_notify("success", "WiFi connected and saved!")
                else:
                    self._send_notify("error", f"Could not connect to WiFi '{ssid}'!")

            elif msg.startswith("general"):
                _, timezone, sync_time, language = msg.split(".")

                self._config.update(
                    "general",
                    {
                        "timezone": int(timezone),
                        "syncTime": sync_time,
                        "language": language,
                    },
                )
                self._send_notify("success", "General config saved!")

            elif msg.startswith("timeout"):
                _, drop, open, close = msg.split(".")
                self._config.update(
                    "timeout",
                    {"drop": int(drop), "open": int(open), "close": int(close)},
                )
                self._send_notify("success", "Timeout config saved!")

        except Exception as e:
            self._handle_send(f"Config error: {e}")

    def _send_notify(self, msg_type: str, content: str) -> None:
        payload = json.dumps({"type": msg_type, "content": content})
        self._handle_send(payload)

    def _test_wifi(self, ssid: str, password: str, timeout_s: int = 10) -> bool:
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)

        if wlan.isconnected():
            wlan.disconnect()
            time.sleep_ms(200)

        wlan.connect(ssid, password)

        start_ms = time.ticks_ms()
        timeout_ms = timeout_s * 1000

        while time.ticks_diff(time.ticks_ms(), start_ms) < timeout_ms:
            if wlan.isconnected():
                return True

            status = wlan.status()
            if status < 0:
                break

            time.sleep_ms(250)

        wlan.disconnect()
        return False
