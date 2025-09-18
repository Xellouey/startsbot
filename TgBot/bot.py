from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeChat, BufferedInputFile

from TgBot.bot_utils import autobackup_admin
from TgBot.loops import start_expired_orders_loop, start_autobackup_admin
from config import cfg

from TgBot.middlewares.trottling import ThrottlingMiddleware

import logging

from utils.database import db_users

logger = logging.getLogger(f"main.{__name__}")


class States(StatesGroup):
    login = State()
    conf = State()

class Telegram:
    def __init__(self, TOKEN):
        self.bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        self.dp = Dispatcher(storage=MemoryStorage())

        self.commands = [
            BotCommand(command='start', description="Начать"),
            # BotCommand(command='buy', description="Купить"),
            # BotCommand(command='profile', description="Мой профиль"),
        ]
        self.admin_commands = self.commands.copy()
        self.admin_commands.extend([
            BotCommand(command='logs', description="📁 Лог-файл"),
            BotCommand(command='stat', description="📊 Статистика"),
            BotCommand(command='sys', description="🖥 Нагрузка на систему"),
            # BotCommand(command='newsletter', description='Настройки рассылки'),
            BotCommand(command='admin', description="👨🏼‍💻 Админ-панель"),
            # BotCommand(command='restart', description="Перезапустить бота"),
        ])

        self.admins = cfg.admins

    async def init(self):
        from TgBot.handlers import payment, start, error, admin, buy_stars

        await self.set_commands()

        start_expired_orders_loop(self.bot)
        start_autobackup_admin(self.bot)

        self.dp.include_routers(
            admin.get_admin_router(),
            buy_stars.router,
            start.router,
            payment.router,
            error.router,
        )

        self.dp.message.middleware(ThrottlingMiddleware())

        logger.info(f"Бот @{(await self.bot.me()).username} инициализирован.")

    async def set_commands(self):
        await self.bot.set_my_commands(self.commands)
        for user in self.admins:
            await self.bot.set_my_commands(self.admin_commands, BotCommandScopeChat(chat_id=user))

    async def run(self):
        while True:
            try:
                await self.dp.start_polling(self.bot)
            except (SystemExit, KeyboardInterrupt) as e:
                raise e
            except Exception as e:
                print(f"Error occurred: {e}")