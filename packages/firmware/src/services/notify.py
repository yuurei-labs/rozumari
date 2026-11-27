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
        """Initialize the notification service and API client."""
        super().__init__()
        self._api = Api()

    async def send(
        self,
        *,
        level: "Literal['info' , 'warning' , 'error']",
        title: str,
        body: str,
        payload: dict | None = None,
        schedule_id: str | None = None,
    ):
        """Send a notification to the backend.

        Posts a notification containing its severity level, title, body,
        optional payload, and associated schedule identifier.

        Args:
            level: Notification severity level.
            title: Notification title.
            body: Notification message content.
            payload: Optional additional notification data.
            schedule_id: Optional identifier of the associated schedule.
        """
        await self._api.post(
            "/api/notifications/send",
            body={
                "level": level,
                "title": title,
                "body": body,
                "payload": payload if payload is not None else {},
                "scheduleId": schedule_id,
            },
        )

    async def emit(self, payload: "EmitPayload"):
        """Emit a real-time message through the device API.

        Sends a message event containing the specified notification payload.

        Args:
            payload: Message payload containing its type and content.
        """
        await self._api.post(
            "/api/devices/emit", body={"action": "message", "payload": payload}
        )
