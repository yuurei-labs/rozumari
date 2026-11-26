import asyncio

from lib.config import Config
from services.drop import Drop

drop = Drop()


async def main():
    Config().load()

    while True:
        await drop.execute([{"slot": "0-0", "quantity": 1}])
        await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        for servo in drop._servos.values():
            servo.off()
