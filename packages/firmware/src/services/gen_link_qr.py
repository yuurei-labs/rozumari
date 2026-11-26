import gc

from lib.api import Api
from lib.singleton import Singleton
from lib.uqr import ERROR_CORRECT_L, QRCode


class GenLinkQr(Singleton):
    def __init__(self) -> None:
        super().__init__()

        self._api = Api()
        self._qr = QRCode(error_correction=ERROR_CORRECT_L, border=1)

    async def execute(self) -> list[list[bool]] | None:
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
