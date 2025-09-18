import asyncio

async def main():
    from utils.database import _base
    _base.create_session()

    from TgBot.bot import Telegram
    from utils.prints import display_bot_statistics

    from utils.tools import create_dirs
    create_dirs()

    from utils import logger
    from config import cfg
    from APIs.ton_api import api

    api.init()
    api.cookie, api.hash, api.api_key, api.mnemonic = cfg.cookies, cfg.hash_fragment, cfg.ton_api_key, cfg.mnemonic
    api.init()
    await api.init_profile()


    await display_bot_statistics()
    telegram = Telegram(cfg.token)
    await telegram.init()
    await telegram.run()

if __name__ == "__main__":
    asyncio.run(main())
