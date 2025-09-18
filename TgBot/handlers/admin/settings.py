from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.types import CallbackQuery, Message
from tonutils.wallet.utils import validate_mnemonic

from APIs.ton_api import api, GetProfileError, BadRequest
from TgBot import CBT, keyboards as kbs
from TgBot.bot import logger
from config import cfg
from utils.tools import load_cookies

router = Router()

async def answer_settings(update: Message | CallbackQuery, st: FSMContext):
    msg = (await st.get_data()).get("msg")
    if msg and (not isinstance(update, CallbackQuery) or msg.message_id != update.message.message_id):
        await msg.delete()
    text = f"""⚙️ <b>Настройки бота</b>

∟ Канал: {f"@{cfg.channel_username.strip('@')}" if cfg.channel_username else 'Нет'}
∟ Ник поддержки: {f"@{cfg.support_username.strip('@')}" if cfg.support_username else 'Нет'}

∟ Баланс: <code>{await api.get_balance()}</code> TON
∟ Токен TON API: <code>{api.api_key or 'Нет'}</code>
∟ Сид-фраза: {", ".join(api.mnemonic) if api.mnemonic else '<b>Не установлена</b>'}

∟ Куки: <b>{'Установлены' if api.cookie else 'Не установлены'}</b>
∟ Хеш: <code>{api.hash or 'Нет'}</code>

∟ Тег: @{api.username.strip('@') if api.username else 'Нет'}
∟ Имя: {api.name or 'Нет'}
            """
    if isinstance(update, CallbackQuery):
        await update.message.edit_text(text, reply_markup=kbs.settings_admin_kb())
    else:
        await update.answer(text, reply_markup=kbs.settings_admin_kb())
    await st.clear()

@router.callback_query(F.data == CBT.ADMIN_PANEL_SETTINGS)
async def open_settings_admin(c: CallbackQuery, state: FSMContext):
    await answer_settings(c, state)

@router.callback_query(F.data == CBT.EDIT_CHANNEL)
async def edit_channel(c: CallbackQuery, state: FSMContext):
    msg = await c.message.edit_text("Отправь новый ник канала", reply_markup=kbs.kb(
        kbs.Btn("🔙 Назад", CBT.ADMIN_PANEL_SETTINGS)))
    await state.set_state(State(c.data))
    await state.update_data(msg=msg)

@router.message(State(CBT.EDIT_CHANNEL))
async def edit_channel_handler(m: Message, state: FSMContext):
    try:
        if m.text != '-':
            t = m.text.strip("@")
            channel = await m.bot.get_chat((t.rjust(len(t) + 1, "@") if (not t.isdigit() and not t.startswith("-100")) else int(t)))
            if not (await channel.get_member((await m.bot.me()).id)).can_invite_users:
                raise Exception
            us = channel.username
        else:
            us = ''
    except Exception as e:
        logger.info(f"Нельзя добавить канал @{m.text}: {str(e)}")
        await (await state.get_data()).get("msg").delete()
        await m.answer("Не удалось найти канал",
                       reply_markup=kbs.kb(kbs.Btn("🔙 Назад", CBT.ADMIN_PANEL_SETTINGS)))
        await state.clear()
        return

    cfg.channel_username = us
    cfg.save()
    await answer_settings(m, state)


@router.callback_query(F.data == CBT.EDIT_SUPPORT_CONTACT)
async def edit_channel(c: CallbackQuery, state: FSMContext):
    msg = await c.message.edit_text("Отправь новый ник поддержки", reply_markup=
            kbs.kb(kbs.Btn("🔙 Назад", CBT.ADMIN_PANEL_SETTINGS)))
    await state.set_state(State(c.data))
    await state.update_data(msg=msg)

@router.message(State(CBT.EDIT_SUPPORT_CONTACT))
async def edit_channel_handler(m: Message, state: FSMContext):
    cfg.support_username = m.text if m.text != '-' else ''
    cfg.save()
    await answer_settings(m, state)

@router.callback_query(F.data == CBT.ADMIN_EDIT_REF_PERCENT)
async def edit_ref_percent(c: CallbackQuery, state: FSMContext):
    msg = await c.message.edit_text('Отправь реферальный процент', reply_markup=
    kbs.kb(kbs.Btn("🔙 Назад", CBT.ADMIN_PANEL_SETTINGS)))
    await state.set_state(State(c.data))
    await state.update_data(msg=msg)

@router.message(State(CBT.ADMIN_EDIT_REF_PERCENT))
async def edit_ref_percent_handler(m: Message, state: FSMContext):
    try:
        ref_percent = float(m.text)
        if not (0 <= ref_percent <= 100):
            raise ValueError
    except ValueError:
        await m.answer("Пожалуйста, введите число от 0 до 100.")
        return
    cfg.ref_percent = ref_percent
    cfg.save()
    await answer_settings(m, state)

@router.callback_query(F.data == CBT.ADMIN_EDIT_FEE_STEAM)
async def edit_fee_stars(c: CallbackQuery, state: FSMContext):
    msg = await c.message.edit_text('Отправь процент комиссии Stars', reply_markup=
            kbs.kb(kbs.Btn("🔙 Назад", CBT.ADMIN_PANEL_SETTINGS)))
    await state.set_state(State(c.data))
    await state.update_data(msg=msg)

@router.message(State(CBT.ADMIN_EDIT_FEE_STEAM))
async def edit_fee_stars_handler(m: Message, state: FSMContext):
    try:
        fee_stars = float(m.text)
        if not (0 <= fee_stars <= 100):
            raise ValueError
    except ValueError:
        await m.answer("Пожалуйста, введите число от 0 до 100.")
        return
    cfg.fee = fee_stars
    cfg.save()
    await answer_settings(m, state)

@router.callback_query(F.data == CBT.EDIT_COOKIES)
async def edit_cookies(c: CallbackQuery, state: FSMContext):
    msg = await c.message.edit_text('🍪 Отправь новые куки', reply_markup=
            kbs.kb(kbs.Btn("🔙 Назад", CBT.ADMIN_PANEL_SETTINGS)))
    await state.set_state(State(c.data))
    await state.update_data(msg=msg)

@router.message(State(CBT.EDIT_COOKIES))
async def edit_cookies_handler(m: Message, state: FSMContext):
    r = load_cookies(m.text)
    if r == -1:
        return await m.answer(f"❌ <b>Неверный формат куки</b>")
    api.cookie = r
    try:
        name, username = api.get_profile(api.cookie)
        api.name, api.username = name, username
        await api.init_profile()
    except Exception as e:
        logger.error(f"Ошибка при парсинге профиля: {str(e)}")
        logger.debug("TRACEBACK", exc_info=True)
        await m.delete()
        await state.clear()
        return await m.answer(f"❌ <b>При авторизации произошла ошибка. Скорее всего, куки не подходят</b>")
    cfg.cookies = r
    cfg.save()
    await answer_settings(m, state)

@router.callback_query(F.data == CBT.EDIT_MNEMONIC)
async def edit_seed_mneminoc(c: CallbackQuery, state: FSMContext):
    msg = await c.message.edit_text('🔐 Отправь новую сид-фразу', reply_markup=
            kbs.kb(kbs.Btn("🔙 Назад", CBT.ADMIN_PANEL_SETTINGS)))
    await state.set_state(State(c.data))
    await state.update_data(msg=msg)

@router.message(State(CBT.EDIT_MNEMONIC))
async def edit_seed_mnemonic_handler(m: Message, state: FSMContext):
    _words = list(map(str.strip, (m.text.split(',') if "," in m.text else m.text.split())))
    await state.clear()
    if len(_words) not in (12, 16, 24):
        return await m.answer(f"❌ <b>Сид-фраза должна состоять из 12, 16 или 24 англ. слов</b>")
    api.mnemonic = _words
    cfg.mnemonic = _words
    cfg.save()
    api.init()
    await answer_settings(m, state)

@router.callback_query(F.data == CBT.EDIT_HASH)
async def edit_hash(c: CallbackQuery, state: FSMContext):
    msg = await c.message.edit_text('👨🏼‍💻 Отправь новый хеш', reply_markup=
            kbs.kb(kbs.Btn("🔙 Назад", CBT.ADMIN_PANEL_SETTINGS)))
    await state.set_state(State(c.data))
    await state.update_data(msg=msg)

@router.message(State(CBT.EDIT_HASH))
async def edit_hash_handler(m: Message, state: FSMContext):
    await state.clear()
    old_hash = api.hash
    try:
        api.hash = m.text
        await api.search_stars_recipient('soxbz')
    except BadRequest as e:
        api.hash = old_hash
        return m.answer(f"🔩 <b>Неверный хеш</b>\n\n"
                        f"<code>{str(await e.response.text())}</code>")
    cfg.hash_fragment = api.hash
    api.init()
    cfg.save()
    await answer_settings(m, state)

@router.callback_query(F.data == CBT.EDIT_TON_API)
async def edit_ton_api(c: CallbackQuery, state: FSMContext):
    msg = await c.message.edit_text('🔑 Отправь новый TON API-ключ', reply_markup=
            kbs.kb(kbs.Btn("🔙 Назад", CBT.ADMIN_PANEL_SETTINGS)))
    await state.set_state(State(c.data))
    await state.update_data(msg=msg)

@router.message(State(CBT.EDIT_TON_API))
async def edit_ton_api_handler(m: Message, state: FSMContext):
    api.api_key = m.text
    cfg.ton_api_key = m.text
    cfg.save()
    api.init()
    await answer_settings(m, state)