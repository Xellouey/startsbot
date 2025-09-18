from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton as B, InlineKeyboardMarkup as K

from TgBot.bot import logger
from TgBot.enums import Stickers
from TgBot.keyboards import _gen_back_button

from TgBot.keyboards import payment_methods_kb, success_deposit
from TgBot.tools import notifications
from TgBot.tools.notifications import notify_admins_new_payment
from TgBot.tools.texts import refreal_menu
from TgBot.bot_utils import kb
from payments import check_pay, generate_inv
from TgBot.states import DepositState
from TgBot import CBT
from utils.database import db_users, db_invoices
from utils.database.db_invoices import Status, Invoice
import logging

from utils.tools import time_to_str

log = logging.getLogger(f"main.{__name__}")

router = Router()

@router.callback_query(F.data == CBT.DEPOSIT_BALANCE)
async def top_up_balance(c: CallbackQuery, state: FSMContext):
    await c.message.delete()
    msg = await c.message.answer(text="💵 <b>Введите сумму для пополнения баланса:</b>",
                              reply_markup=_gen_back_button())
    await state.set_state(DepositState.enter_amount)
    await state.set_data({'msg': msg})

@router.message(DepositState.enter_amount)
async def enter_amount(m: Message, state: FSMContext):
    try:
        amount = float(m.text)
    except ValueError:
        return await m.answer("🚫 <b>Пожалуйста, введите корректную сумму.</b>")
    msg = (await state.get_data()).get('msg')
    if msg:
        await msg.delete()
    await m.answer("💳 <b>Выберите метод оплаты:</b>", reply_markup=payment_methods_kb(amount))
    await state.clear()

@router.callback_query(F.data.startswith(f"{CBT.PAYMENT_METHOD}:"))
async def choose_payment_method(c: CallbackQuery, state: FSMContext):
    amount, method = c.data.split(":")[1:]
    amount = float(amount)
    method = int(method)
    if len(db_invoices.get_invoices_by_user(c.from_user.id, status=Status.PENDING)) >= 10:
        return await c.message.edit_text('<b>❌ Вы превысили лимит создаваемых счетов!</b>', reply_markup=_gen_back_button())
    res = await c.message.edit_reply_markup(reply_markup=kb(B(text='🕔 Создание счета...', callback_data=CBT.EMPTY)))
    inv = db_invoices.add_invoice(Invoice(
        creator_id=c.from_user.id, payment_method=method, amount=float(amount)
    ))
    try:
        args = await generate_inv(inv)
        if all(v == -1 for v in args):
            logger.warning(f"Метод оплаты {method} ({type(method).__name__}) не найден")
            await res.delete()
            return await c.message.answer('<b>🤷‍♂️ Метод оплаты не найден!</b>',
                      reply_markup=_gen_back_button())
        link, inv_id, text, new_amount = args
    except Exception as e:
        log.error(f"Ошибка при создании платежа: {str(e)}")
        log.debug("TRACEBACK", exc_info=True)
        db_invoices.update_invoice(inv.id, status=Status.ERROR)
        await res.delete()
        return await c.message.answer(f"❌ <b>Ошибка создания платежного счета</b>")
    await res.delete()
    db_invoices.update_invoice(inv.id, inv_pay_id=inv_id, amount=new_amount, link=link)
    await c.message.answer((text or f"💳 <b>Сумма: {amount} RUB</b>\n"
                           f"Метод оплаты: <b>{inv.method_name}</b>\n\n"
                           f" • У вас есть <b>{time_to_str(inv.expiration_hours * 3600)}</b> для оплаты"),
                              reply_markup=gen_check_payment_menu(link, inv.id))
    await state.clear()

def gen_check_payment_menu(link, order_id):
    kb = []
    if link:
        kb.append([B(text="Перейти к оплате", url=link)])
    kb.append([B(text="✅ Проверить", callback_data=f"{CBT.CHECK_PAYMENT}:{order_id}")])
    return K(inline_keyboard=kb)

@router.callback_query(F.data.startswith(f"{CBT.CHECK_PAYMENT}:"))
async def check_payment(c: CallbackQuery, state: FSMContext):
    inv_id = c.data.split(":")[-1]
    if db_invoices.is_invoice_expired(inv_id):
        db_invoices.update_invoice(inv_id, status=Status.EXPIRED)
        await c.message.delete_reply_markup()
        return await c.message.reply("<b>⏱️ Срок оплаты платежа истёк</b>")
    inv = db_invoices.get_invoice(inv_id)
    result = await check_pay(inv)
    if result == 'not found':
        db_invoices.update_invoice(inv_id, status=Status.CANCELED)
        await c.message.delete()
        await c.message.answer('<b>🗑 Счёт не найден. Возможно, он был отменён</b>')
    if result == 1:
        db_invoices.update_invoice(inv_id, status=Status.PAID)
        db_users.add_balance(inv.creator_id, inv.amount)
        await c.message.delete()
        await c.message.answer_sticker(Stickers.RICH_DUCK)
        await c.message.answer(f"<b>🪙 Счёт успешно оплачен.</b>\n\n"
                                  f"На ваш баланс начислено <code>{inv.amount}</code> {inv.currency}",
                               reply_markup=success_deposit())
        logger.info(f"Пользователь {inv.user.id} пополнил баланс на {inv.amount} {inv.currency}. "
                    f"Пригласил: {inv.user.invited_by or 'Никто'}")
        if inv.user.invited_by:
            invited_by = db_users.get_user(_id=inv.user.invited_by)
            await notifications.notify_user_new_referral(c.bot, invited_by, inv.user, inv.amount, inv.currency)
        await notify_admins_new_payment(c.bot, inv)
    else:
        await c.answer('Счет не был оплачен!')

# ============== реферальная система ============ #


@router.callback_query(F.data == CBT.REFERRAL_SYSTEM)
async def referral_system(c: CallbackQuery):
    user = db_users.get_user(user_id=c.from_user.id)
    await c.message.delete()
    await c.message.answer(refreal_menu(user, (await c.bot.me()).username), reply_markup=_gen_back_button())

