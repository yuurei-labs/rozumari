from lib.singleton import Singleton


class SyncTask(Singleton):
    def __init__(self) -> None:
        super().__init__()

    async def execute(self):
        pass
