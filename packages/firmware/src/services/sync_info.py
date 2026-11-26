from lib.api import Api
from lib.singleton import Singleton


class SyncInfo(Singleton):
    def __init__(self) -> None:
        super().__init__()
        self._api = Api()

        self._data: dict = {}

    @property
    def data(self) -> dict:
        return self._data

    async def execute(self) -> bool:
        resp = await self._api.get("/api/devices/info")
        if not resp or not resp["data"]:
            return False

        self._data = resp["data"]
        return True
