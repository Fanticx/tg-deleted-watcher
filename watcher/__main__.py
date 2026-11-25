import asyncio
import logging

from .app import Watcher
from .config import Config


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("telethon").setLevel(logging.WARNING)
    try:
        asyncio.run(Watcher(Config.from_env()).run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
