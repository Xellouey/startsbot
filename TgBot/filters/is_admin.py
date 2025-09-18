from aiogram.filters import BaseFilter
from aiogram.types import Message

from config import cfg


class IsAdmin(BaseFilter):
    def __init__(self, is_admin: bool = True) -> None:
        self.is_admin = is_admin

    async def __call__(self, message: Message) -> bool:
        return self.is_admin is (message.from_user.id in cfg.admins)