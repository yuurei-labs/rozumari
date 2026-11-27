from lib.api import Api
from lib.config import Config
from lib.singleton import Singleton


class SyncInfo(Singleton):
    def __init__(self) -> None:
        """Initialize the API client and device configuration."""
        super().__init__()
        self._api = Api()
        self._config = Config()

    async def execute(self) -> bool:
        """Synchronize device information from the backend.

        Fetches the device information and updates the local configuration
        with the device ID, name, factory model, and position.

        Returns:
            True if device information is retrieved and updated successfully;
            otherwise, False.
        """
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
