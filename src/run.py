import asyncio

from icpc_mexico_scoreboard.app import start


if __name__ == "__main__":
    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        pass
