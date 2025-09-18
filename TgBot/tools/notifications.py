from aiogram import Bot

from TgBot.tools.admin_tools import send_admins
from TgBot.bot_utils import tag_user
from config import cfg
from utils.database.db_invoices import Invoice
from utils.database.db_stars_orders import StarsOrder
from utils.database.db_users import User

import logging


logger = logging.getLogger(f"main.{__name__}")


async def notify_admins_new_payment(
    bot: Bot,
    invoice: Invoice
):
    if cfg.notify_new_dep:
        await send_admins(
            bot, f"💰 {tag_user(invoice.user.full_name, invoice.user.user_id)} депнул "
                 f"<code>{invoice.amount}</code> <b>{invoice.currency}</b>\n"
                 f"- Метод оплаты: <b>{invoice.method_name}</b>"
        )


async def notify_admins_new_user(bot: Bot, user: User):
    if cfg.notify_new_user:
        await send_admins(
            bot, f"👋 {f'@{user.username} | ' if user.username else ''}"
                 f"{tag_user(user.full_name, user.user_id)}"
        )

async def notify_user_new_referral(
    bot: Bot,
    patnter: User,
    referral: User,
    amount: float,
    curr: str = 'RUB'
):
    await bot.send_message(
        patnter.user_id, f"<b>🫂 Реферал {tag_user(referral.full_name, referral.user_id)} депнул <code>{amount}</code> {patnter.currency.upper()}</b>\n"
                         f" - Зачислено: <code>{amount * cfg.ref_percent}</code> {curr}"
    )


async def notify_success_stars_deposit(
    bot: Bot,
    order: StarsOrder
):
    if cfg.notify_new_stars_deposit:
        await send_admins(
            bot, f"⭐️ <b> Успешно куплено <code>{order.stars_amount}</code> Stars!</b>\n"
                 f" ∟ В рублях: <code>{order.total}</code> RUB\n"
                 f" ∟ Сумма: <code>{order.amount_ton} TON</code>\n"
                 f" ∟ Транзакция: <a href='https://tonviewer.com/transaction/{order.tx_hash}'>{order.tx_hash}</a>")