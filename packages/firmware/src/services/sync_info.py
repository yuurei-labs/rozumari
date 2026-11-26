from lib.api import Api
from lib.config import Config
from lib.singleton import Singleton


class SyncInfo(Singleton):
    def __init__(self) -> None:
        super().__init__()

        self._api = Api()
        self._config = Config()

    async def execute(self) -> bool:
        resp = await self._api.get("/api/devices/info")
        if not resp or not resp["data"]:
            return False

        data: dict = resp["data"]
        self._config.update(
            "device",
            {
                "id": data.get("id", ""),
                "name": data.get("name", "Rozumari"),
                "model": data.get("factoryModel", ""),
                "position": data.get("position", ""),
            },
        )

        return True
