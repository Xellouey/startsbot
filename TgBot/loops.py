import asyncio

from TgBot.bot_utils import autobackup_admin
from payments import cancel_order
from utils.database import db_invoices
from aiogram import Bot
import logging

from utils.database.db_invoices import Status

logger = logging.getLogger(f"main.{__name__}")


def start_expired_orders_loop(bot: Bot, delay: int = 50):
    async def run():
        while True:
            try:
                for inv in db_invoices.get_all_invoices(func=lambda i: i.status == Status.PENDING):
                    exprd = db_invoices.is_invoice_expired(inv.id)
                    if exprd is not None:
                        if exprd:
                            logger.info(f"Срок оплаты заказа {inv.id} пользователя {inv.creator_id} истёк")
                            await cancel_order(inv)
                            try:
                                await bot.send_message(inv.creator_id, f"⌛️ <b>Срок оплаты заказа</b> #{inv.id} <b>истёк!</b>")
                            except Exception as e:
                                logger.error(f"Ошибка при отправке сообщения {inv.creator_id} об истечение заказа {inv.id} - {e}")
                                logger.debug("TRACEBACK", exc_info=True)
            except Exception as e:
                logger.error(f"Ошибка при работе цикла с заказами - {e}")
                logger.debug("TRACEBACK", exc_info=True)
                await asyncio.sleep(100)
            await asyncio.sleep(delay)

    asyncio.create_task(run())


def start_autobackup_admin(bot: Bot):
    async def run():
        while True:
            await autobackup_admin(bot)
            await asyncio.sleep(60 * 60 * 24)

    asyncio.create_task(run())