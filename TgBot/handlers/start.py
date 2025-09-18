from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from TgBot.bot import logger
from TgBot.keyboards import start_kb, profile_telegram_menu, req_sub
from TgBot.tools import notifications
from TgBot.bot_utils import answer_with_banner, check_sub_channel, edit_msg
from config import cfg
from utils.database import db_users, db_invoices, db_stars_orders

from TgBot.tools.texts import start_message, text_profile
from TgBot import CBT
from utils.database.db_invoices import Status

router = Router()

@router.message(Command("start"))
async def start_cmd(m: Message, state: FSMContext):
    user = db_users.get_user(user_id=m.from_user.id)
    if not user:
        invited_by = None
        postfix = m.text.split()[-1]
        if "r_" in postfix:
            invited_by = postfix[2:]
        role = 'admin' if m.from_user.id in cfg.admins else 'user'
        user = db_users.add_user(user_id=m.from_user.id,
                          full_name=m.from_user.full_name,
                          username=m.from_user.username,
                          invited_by=invited_by,
                          role=role)
        logger.info(f"Новый пользователь: {user.user_id}")
        await notifications.notify_admins_new_user(m.bot, user)
    await state.clear()
    if not await check_sub_channel(m.bot, m.from_user.id):
        return await m.answer(
            f"""👋 <b>Привет, {m.from_user.full_name}!</b>

Чтобы использовать бот, необходимо подписаться на наш канал с новостями и обновлениями:""",
            reply_markup=req_sub()
        )
    await answer_with_banner(m, start_message(m.from_user.full_name), reply_kb=start_kb())

@router.callback_query(F.data == CBT.MAIN_MENU)
async def main_menu_handler(c: CallbackQuery):
    if not await check_sub_channel(c.bot, c.from_user.id):
        return await c.message.answer(
            f"""👋 <b>Привет, {c.from_user.full_name}!</b>

    Чтобы использовать бот, необходимо подписаться на наш канал с новостями и обновлениями:""",
            reply_markup=req_sub()
        )
    await c.message.delete()
    await answer_with_banner(c.message, start_message(c.from_user.full_name), reply_kb=start_kb())

@router.callback_query(F.data == CBT.CHECK_SUB_CHANNEL)
async def check_sub(c: CallbackQuery):
    if not await check_sub_channel(c.bot, c.from_user.id):
        return await c.answer('Вы не подписались на канал!')
    await c.message.delete()
    await answer_with_banner(c.message, start_message(c.from_user.full_name), reply_kb=start_kb())

@router.message(Command("profile"))
async def profile_cmd(m: Message):
    user = db_users.get_user(user_id=m.from_user.id)
    invs = db_invoices.get_invoices_by_user(m.from_user.id, status=Status.PAID)
    stars_invs = db_stars_orders.get_user_orders(m.from_user.id)
    await answer_with_banner(m, text_profile(user, invs, stars_invs), reply_kb=profile_telegram_menu())

@router.callback_query(F.data.startswith(CBT.PROFILE_TELEGRAM))
async def profile_telegram_handler(c: CallbackQuery, state: FSMContext):
    if not await check_sub_channel(c.bot, c.from_user.id):
        return await c.message.answer(
            f"""👋 <b>Привет, {c.from_user.full_name}!</b>

    Чтобы использовать бот, необходимо подписаться на наш канал с новостями и обновлениями:""",
            reply_markup=req_sub()
        )
    user = db_users.get_user(user_id=c.from_user.id)
    invs = db_invoices.get_invoices_by_user(c.from_user.id, status=Status.PAID)
    stars_invs = db_stars_orders.get_user_orders(c.from_user.id)
    if c.data.split(":")[-1] != '1':
        await c.message.delete()
    else:
        await c.message.delete_reply_markup()
    await answer_with_banner(c.message, text_profile(user, invs, stars_invs), reply_kb=profile_telegram_menu())
    await state.clear()

@router.callback_query(F.data == CBT.EMPTY)
async def empty_handler(c: CallbackQuery):
    await c.answer()

@router.callback_query(F.data == CBT.CLEAR_STATE)
async def clear_state_handler(c: CallbackQuery, state: FSMContext):
    await c.message.delete_reply_markup()
    await state.clear()
    await edit_msg(c.message, start_message(c.from_user.full_name), reply_kb=start_kb())
