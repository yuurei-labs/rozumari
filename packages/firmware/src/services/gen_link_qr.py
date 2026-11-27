import gc

from lib.api import Api
from lib.singleton import Singleton
from lib.uqr import ERROR_CORRECT_L, QRCode


class GenLinkQr(Singleton):
    def __init__(self) -> None:
        """Initialize the API client and QR code generator."""
        super().__init__()
        self._api = Api()
        self._qr = QRCode(error_correction=ERROR_CORRECT_L, border=1)

    async def execute(self) -> list[list[bool]] | None:
        """Generate a QR code matrix for device linking.

        Requests a device linking token from the API and encodes the returned
        data into a QR code matrix. Releases temporary data and performs garbage
        collection to reduce memory usage.

        Returns:
            A two-dimensional boolean matrix representing the QR code, or None
            if the API response is invalid or contains no linking data.
        """
        gc.collect()
        resp = await self._api.get("/api/devices/link/generate")
        if not resp or not isinstance(resp.get("data"), str):
            del resp
            gc.collect()
            return None

        data = resp["data"]
        if not data:
            del data, resp
            gc.collect()
            return None

        self._qr.clear()
        self._qr.add_data(data)
        matrix = self._qr.get_matrix()

        self._qr.clear()
        del data, resp
        gc.collect()

        return matrix  # pyright: ignore[reportReturnType]
