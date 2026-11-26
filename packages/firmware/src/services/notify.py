from lib.api import Api
from lib.singleton import Singleton

try:
    from typing import Literal, TypedDict

    class EmitPayload(TypedDict):
        type: Literal["info", "success", "error"]
        content: str
except:
    pass


class Notify(Singleton):
    def __init__(self) -> None:
        super().__init__()

        self._api = Api()

    async def send(
        self,
        level: "Literal['info' , 'warning' , 'error']",
        title: str,
        body: str,
        payload: dict | None = None,
        schedule_id: str | None = None,
    ):
        await self._api.post(
            "/api/notifications/send",
            {
                "level": level,
                "title": title,
                "body": body,
                "payload": payload,
                "scheduleId": schedule_id,
            },
        )

    async def emit(self, payload: "EmitPayload"):
        await self._api.post(
            "/api/devices/emit", {"action": "message", "payload": payload}
        )
