from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from TgBot.bot import logger
from TgBot.bot_utils import answer_with_banner, edit_msg, check_sub_channel
from TgBot.states import StarsState
from TgBot import CBT
from TgBot.keyboards import buy_stars, stars_dep_confirm_kb, _gen_back_button, go_deposit, dodep_stars, waiting, req_sub

from APIs.ton_api import (api, NotFindedUsername, CantGiftUsername, InsufficientFundsError, FragmentAPIError,
                          BadRequest,
                          ton_to_rub)
from TgBot.tools.notifications import notify_success_stars_deposit
from config import cfg
from utils.database import db_stars_orders, db_users

router = Router()

@router.callback_query(F.data.startswith(CBT.OPEN_MENU))
async def open_stars_deposit_menu(c: CallbackQuery, state: FSMContext):
    if not await check_sub_channel(c.bot, c.from_user.id):
        await c.message.answer(
            f"""👋 <b>Привет, {c.from_user.full_name}!</b>

Чтобы использовать бот, необходимо подписаться на наш канал с новостями и обновлениями:""",
            reply_markup=req_sub()
        )
        return
    try:
        star_price = await api.star_price()
        if cfg.fee:
            msg = f'🪙 <b>1 Telegram Stars = {round((star_price * (1 + (cfg.fee / 100))) * ton_to_rub(), 2)} RUB</b>'
        else:
            msg = "\n".join([f"• До <b>{rng[0][1]}</b> звёзд <b>{rng[1]}</b> RUB" for rng in list(cfg.course.values())])
        text = f"""⭐️ <b>Актуальные цены:</b>

{msg}"""
        if c.data.split(":")[-1] == '1':
            await c.message.delete_reply_markup()
        else:
            await c.message.delete()
        await answer_with_banner(c.message, text, reply_kb=buy_stars())
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при открытии меню: {e}")
        logger.debug('TRACEBACK', exc_info=True)
        await c.message.answer("❌ <b>Ошибка при загрузке цен. Попробуйте позже.</b>")
        await state.clear()

@router.callback_query(F.data.startswith(CBT.BUY))
async def pick_currency(c: CallbackQuery, state: FSMContext):
    if not api.inited:
        await c.answer("В данный момент идут тех. работы!")
        return
    try:
        balance = await api.get_balance()
        star_price = await api.star_price()
        if balance <= 50 * star_price:
            logger.warning("Недостаточно средств для покупки звезд")
            await c.answer("В данный момент идут тех. работы!")
            return
        _min = 50
        _max = int(balance // star_price)
        await state.set_state(StarsState.wait_amount)
        await state.update_data()
        await c.message.delete()
        msg = await c.message.answer(
            f"⭐️ Введи кол-во Telegram Stars:\n\n- От <b>{_min}</b> до <b>{_max}</b>",
            reply_markup=_gen_back_button(CBT.OPEN_MENU)
        )
        await state.update_data(max=_max, min=_min, msg=msg)
    except Exception as e:
        logger.error(f"Ошибка при выборе валюты: {e}")
        await c.answer("❌ <b>Ошибка при загрузке баланса. Попробуйте позже.</b>")
        await state.clear()

@router.message(StarsState.wait_amount)
async def send_amount(m: Message, state: FSMContext):
    try:
        amount = int(m.text)
    except ValueError:
        await m.answer("❌ <b>Введите корректную сумму</b>")
        return
    st = await state.get_data()
    _max, _min = st['max'], st['min']
    if amount < _min or amount > _max:
        await m.answer(f"❌ <b>Сумма должна быть от <code>{_min}</code> до <code>{_max}</code></b>")
        return
    await state.update_data(amount=amount)
    msg = st.get('msg')
    if msg:
        await msg.delete()
    await m.answer(
        f"👤 Отправь @username. Сумма: <b>{amount} Stars</b>",
        reply_markup=_gen_back_button(CBT.OPEN_MENU)
    )
    await state.set_state(StarsState.wait_login)

@router.message(StarsState.wait_login)
async def send_login(m: Message, state: FSMContext):
    st = await state.get_data()
    login, amount = m.text.strip("@"), st['amount']
    if login.startswith("https://t.me/"):
        login = login.replace("https://t.me/", "")
    try:
        await api.search_stars_recipient(login)
    except NotFindedUsername:
        await m.answer(f"❌ Пользователь <b>@{login}</b> не найден")
        return
    except CantGiftUsername:
        await m.answer(f"❌ <b>Нельзя отправить звезды на @{login}</b>")
        return
    except Exception as e:
        logger.error(f"Ошибка при проверке username: {e}")
        await m.answer("❌ <b>Ошибка при поиске пользователя. Попробуйте позже.</b>")
        await state.clear()
        return
    try:
        if cfg.fee:
            to_pay = round(((await api.star_price() * (1 + (cfg.fee / 100))) * amount) * ton_to_rub(), 2)
        else:
            to_pay = round(amount * cfg.get_course(amount), 2)
        await state.clear()
        await m.answer(
            f"🔎 <b>Пожалуйста, проверьте данные</b>\n\n"
            f"∟ Ваш юзернейм (тег): «<b>{login}</b>»\n"
            f"∟ Сумма: <b>{amount}</b> Telegram Stars\n\n"
            f"💳 К оплате: <b>{to_pay} RUB</b>\n\n"
            f"Если всё верно, нажмите «<b>Подтвердить</b>»",
            reply_markup=stars_dep_confirm_kb(amount, login, to_pay=to_pay)
        )
    except Exception as e:
        logger.error(f"Ошибка при формировании подтверждения: {e}")
        await m.answer("❌ <b>Ошибка при расчете стоимости. Попробуйте позже.</b>")
        await state.clear()

@router.callback_query(F.data.startswith(CBT.CONFIRM_BUY))
async def confirm_buy(c: CallbackQuery, state: FSMContext):
    to_pay, amount, login = c.data.split(":")[1:]
    to_pay, amount = float(to_pay), int(amount)
    user = db_users.get_user(c.from_user.id)
    await state.clear()
    if user.balance < to_pay:
        await edit_msg(c.message, '<b>😓 Не хватает средств для оплаты!</b>', reply_markup=go_deposit())
        return
    await c.message.delete()
    res = await c.message.answer(f"⭐️ <b>Отправляем Telegram звёзды...</b>", reply_markup=waiting())
    try:
        result = await api.send_stars_async(login, amount)
    except NotFindedUsername:
        await res.delete()
        await c.message.answer(f'<b>❌ Пользователя >@{login} не существует!</b>', reply_markup=dodep_stars())
        return
    except CantGiftUsername:
        await res.delete()
        await c.message.answer(f'<b>❌ Нельзя отправить звезды на @{login}!</b>', reply_markup=dodep_stars())
        return
    except InsufficientFundsError as e:
        await res.delete()
        logger.warning(f"Недостаточно TON: нужно {e.price}, баланс {e.balance}")
        await c.message.answer(f'<b>❌ Ошибка при отправке звезд. Попробуйте позже.</b>', reply_markup=dodep_stars())
        return
    except BadRequest:
        await res.delete()
        logger.error("Неверный hash или куки в API")
        await c.message.answer(f'<b>❌ Ошибка конфигурации бота. Обратитесь в поддержку.</b>', reply_markup=dodep_stars())
        return
    except FragmentAPIError as e:
        await res.delete()
        logger.error(f"Ошибка API Fragment: {e}")
        await c.message.answer(f'<b>❌ Ошибка при отправке звезд. Попробуйте позже.</b>', reply_markup=dodep_stars())
        return
    except Exception as e:
        await res.delete()
        logger.error(f"Неизвестная ошибка при пополнении stars: {e}")
        logger.debug("TRACEBACK", exc_info=True)
        await c.message.answer(f'<b>❌ Произошла ошибка. Попробуйте позже.</b>', reply_markup=dodep_stars())
        return
    amount_ton, tx_hash, amount_stars, username = result[:4]
    order = db_stars_orders.add_order(db_stars_orders.StarsOrder(
        stars_amount=amount_stars,
        total=to_pay,
        username=username,
        user_id=c.from_user.id,
        tx_hash=tx_hash,
        amount_ton=amount_ton
    ))
    logger.info(f"{c.from_user.id} купил {amount_stars} звезд на юзернейм @{login}. Транза: {tx_hash}. Сумма: {amount_ton}")
    db_users.add_balance(c.from_user.id, -to_pay)
    await res.delete()
    await answer_with_banner(
        c.message,
        f"💫 <b>Звёзды успешно отправлены!</b>\n\n"
        f"∟ Сумма: <b>{order.stars_amount} Stars</b>\n"
        f"∟ Получатель: <b>@{order.username}</b>\n\n"
        f"Обязательно приходите еще! ❤️",
        reply_kb=dodep_stars()
    )
    await notify_success_stars_deposit(c.bot, order)