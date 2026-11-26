import asyncio
import json

import aioble
from bluetooth import UUID

from lib.config import Config
from lib.logger import Logger
from lib.singleton import Singleton
from services.ble_service import BleService

# Service and Characteristics UUIDs (Sử dụng đối tượng UUID của bluetooth)
_SERVICE_UUID = UUID("20D2C743-9DFC-4FC8-B58F-14686A0A66A5")
_RX_CHAR_UUID = UUID("28363331-A0EA-4954-9E39-3CA259D85EFF")
_TX_CHAR_UUID = UUID("21F3B000-609B-498B-9079-86AE7AE31A28")


class BLE(Singleton):
    """Manages Bluetooth Low Energy (BLE) connections for the IoT system using aioble.

    Implements the Singleton pattern to guarantee that only a single BLE
    driver instance is initialized and controlled throughout the application lifecycle.
    """

    def __init__(self, name: str) -> None:
        """Initializes the GATTS service configuration and background task structures.

        Args:
            name (str): The local name of the device displayed during advertising.

        Returns:
            None
        """
        super().__init__()
        self._name = name
        self._logger = Logger("BLE")
        self._service = BleService(self._send)
        self._ble_service = aioble.Service(_SERVICE_UUID)

        # RX (Write) Characteristic
        self._rx_char = aioble.Characteristic(
            self._ble_service, _RX_CHAR_UUID, write=True, capture=True
        )

        # TX (Read & Notify) Characteristic
        self._tx_char = aioble.Characteristic(
            self._ble_service, _TX_CHAR_UUID, read=True, notify=True
        )

        aioble.register_services(self._ble_service)

        try:
            self._rx_char.write(b"\x00" * 512)
            self._tx_char.write(b"\x00" * 512)
        except Exception as e:
            self._logger.error(f"Failed to pre-allocate buffer size: {e}")

        self._connections: set[aioble.Device] = set()
        self._is_advertising = False

    def get_mac(self):
        try:
            from bluetooth import BLE as _BLE

            _, mac_bytes = _BLE().config("mac")
            return ":".join(f"{byte:02X}" for byte in mac_bytes)
        except Exception:
            return "Unknown"

    def start(self) -> None:
        """Activates BLE and launches the background async tasks.

        Returns:
            None
        """
        if self._is_advertising:
            return

        self._is_advertising = True
        self._logger.info(f"Advertised as {self._name} ({self.get_mac()})")

        loop = asyncio.get_event_loop()
        self._advertising_task = loop.create_task(self._advertising_loop())
        self._rx_task = loop.create_task(self._rx_loop())

    def stop(self) -> None:
        """Stops advertising, cancels tasks, and disconnects all clients.

        Returns:
            None
        """
        self._is_advertising = False

        if hasattr(self, "_advertising_task") and self._advertising_task:
            self._advertising_task.cancel()
            self._advertising_task = None

        if hasattr(self, "_rx_task") and self._rx_task:
            self._rx_task.cancel()
            self._rx_task = None

        for conn in list(self._connections):
            try:
                conn.disconnect()  # pyright: ignore[reportAttributeAccessIssue]
            except Exception:
                pass
        self._connections.clear()
        self._logger.info("Deactivated")

    @property
    def status(self) -> bool:
        """Checks if the BLE module is currently active and running.

        Returns:
            bool: True if advertising is active, False otherwise.
        """
        return self._is_advertising

    async def _advertising_loop(self) -> None:
        """Background task running the advertising loop cleanly.

        Returns:
            None
        """
        config = Config()
        self._name = config.device.get("name", "")

        while self._is_advertising:
            try:
                adv = await aioble.advertise(
                    250_000, name=self._name, services=[_SERVICE_UUID]
                )
                if adv is None or not self._is_advertising:
                    break

                async with adv as connection:
                    self._connections.add(connection)
                    self._logger.info(f"Connected to: {connection.device}")

                    try:
                        await connection.exchange_mtu(256)
                    except Exception:
                        pass

                    await asyncio.sleep(1)

                    if connection.is_connected():
                        payload = json.dumps(
                            {"general": config.general, "timeout": config.timeout},
                        )
                        self._send(payload)

                    await connection.disconnected()
                    self._connections.discard(connection)
                    self._logger.info("Disconnected")

            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._is_advertising:
                    self._logger.error(f"Error in advertising loop: {e}")
                    await asyncio.sleep_ms(500)
                else:
                    break

    async def _rx_loop(self) -> None:
        """Background task that waits and reads incoming BLE writes sequentially.

        Returns:
            None
        """
        while self._is_advertising:
            try:
                _ = await self._rx_char.written()
                data = self._rx_char.read()
                if not data:
                    continue

                try:
                    msg = data.decode("utf-8").strip()
                    self._logger.info(f"Received: {msg}")

                    self._service.execute(msg)
                except UnicodeError:
                    self._logger.info(f"Received non-UTF8 chunk of size: {len(data)}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Error in RX loop: {e}")
                await asyncio.sleep_ms(100)

    def _send(self, msg: str) -> None:
        """Sends a notification payload back to all active connections.

        Args:
            msg (str): The text message to send.
        """
        if not self._is_advertising or not self._connections:
            return

        msg_bytes = msg.encode("utf-8")
        self._tx_char.write(msg_bytes)
        self._logger.info(f"Sent: {msg}")

        for conn in self._connections:
            try:
                self._tx_char.notify(conn)
            except Exception as e:
                self._logger.error(f"Failed to notify client: {e}")
