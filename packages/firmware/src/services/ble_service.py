try:
    from collections.abc import Callable
except:
    pass

import json
import time

import network

from lib.config import Config
from lib.i18n import translate as _t
from lib.singleton import Singleton


class BleService(Singleton):
    def __init__(self, handle_send: "Callable[[str], None]") -> None:
        """Initialize the BLE service.

        Args:
            handle_send: Callback used to send messages to the BLE client.
        """
        super().__init__()
        self._handle_send = handle_send

        self._config = Config()

    def execute(self, msg: str) -> None:
        """Execute a command received from a BLE client.

        Processes commands for Wi-Fi credentials, general settings, and timeout
        configuration. Sends the corresponding response or error message.

        Args:
            msg: Command string received from the BLE client.
        """
        try:
            if msg == "ping":
                self._handle_send("pong")

            if msg.startswith("wifi"):
                _, ssid, password = msg.split(".")
                if self._test_wifi(ssid, password):
                    self._config.update("wifi", {"ssid": ssid, "password": password})
                    self._send_notify("success", _t("ble_wifi_success"))
                else:
                    self._send_notify("error", _t("ble_wifi_failed", ssid=ssid))

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
                self._send_notify("success", _t("ble_general_saved"))

            elif msg.startswith("timeout"):
                _, drop, open, close = msg.split(".")
                self._config.update(
                    "timeout",
                    {"drop": int(drop), "open": int(open), "close": int(close)},
                )
                self._send_notify("success", _t("ble_timeout_saved"))

        except Exception as e:
            self._handle_send(_t("ble_config_error", error=str(e)))

    def _send_notify(self, msg_type: str, content: str) -> None:
        """Send a structured notification to the BLE client.

        Args:
            msg_type: Notification type, such as success or error.
            content: Notification message content.
        """
        payload = json.dumps({"type": msg_type, "content": content})
        self._handle_send(payload)

    def _test_wifi(self, ssid: str, password: str, timeout_s: int = 10) -> bool:
        """Test connectivity to a Wi-Fi network.

        Attempts to connect using the provided credentials within the specified
        timeout. Disconnects if the connection cannot be established.

        Args:
            ssid: Wi-Fi network name.
            password: Wi-Fi network password.
            timeout_s: Maximum connection time in seconds.

        Returns:
            True if the connection succeeds, otherwise False.
        """
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
