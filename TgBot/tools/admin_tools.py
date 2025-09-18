from aiogram import Bot

from utils.database import db_users
import logging

logger = logging.getLogger(f"main.{__name__}")

async def send_admins(
    bot: Bot,
    text: str,
    reply_markup=None,
    **kw
):
    for user in db_users.get_admins():
        try:
            await bot.send_message(
                user.user_id, text, reply_markup=reply_markup, disable_web_page_preview=True, **kw
            )
        except Exception as e:
            logger.error(f'Ошибка при отправке сообщения админу {user.user_id}: {str(e)}')
            logger.debug('TRACEBACK', exc_info=True)

