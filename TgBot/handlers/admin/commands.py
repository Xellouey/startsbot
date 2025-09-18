import io
from datetime import datetime

import psutil
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, BufferedInputFile, CallbackQuery

from TgBot import CBT
from TgBot.filters.is_admin import IsAdmin
from TgBot.keyboards import admin_panel_kb
from TgBot.states import AdminStates
from TgBot.tools.texts import stat
from config import cfg

from utils.database import db_invoices, db_users


router = Router()

@router.message(Command('stat'), IsAdmin())
async def get_stat(m: Message):
    await m.answer(
        stat(
            db_users.get_stat_users(),
            db_invoices.get_stat_invoices()
        )
    )

@router.message(Command('logs'), IsAdmin())
async def get_logs(m: Message):
    with open("logs/log.log", 'rb') as f:
        await m.answer_document(BufferedInputFile(f.read(), 'log.log'),
                                caption=f'📁 <b>#LOGS {datetime.now().strftime("%H:%M:%S %d.%m.%Y")}</b>')


@router.message(Command('admin'), IsAdmin())
async def send_admin(m: Message):
    await m.answer(f"""⚙️ <b>Настройки бота</b>

∟ Канал: {f"@{cfg.channel_username.strip('@')}" if cfg.channel_username else 'Нет'}
∟ Ник поддержки: {f"@{cfg.support_username.strip('@')}" if cfg.support_username else 'Нет'}
            """, reply_markup=admin_panel_kb())

@router.callback_query(F.data == CBT.OPEN_ADMIN_PANEL, IsAdmin())
async def open_adm(c: CallbackQuery, state: FSMContext):
    await c.message.edit_text(f"""⚙️ <b>Настройки бота</b>

∟ Канал: {f"@{cfg.channel_username.strip('@')}" if cfg.channel_username else 'Нет'}
∟ Ник поддержки: {f"@{cfg.support_username.strip('@')}" if cfg.support_username else 'Нет'}
            """, reply_markup=admin_panel_kb())
    await state.clear()

@router.message(Command('sys'), IsAdmin())
async def get_sys_info(m: Message):
    ram = psutil.virtual_memory()
    cpu_usage = "\n".join(
        f"    CPU {i}:  <code>{l}%</code>" for i, l in enumerate(psutil.cpu_percent(percpu=True)))
    text = """<b><u>Сводка данных</u></b>

    <b>ЦП:</b>
    {}
        Используется <i>FPC</i>: <code>{}%</code>

    <b>ОЗУ:</b>
        Всего:  <code>{} MB</code>
        Использовано:  <code>{} MB</code>
        Свободно:  <code>{} MB</code>
        Используется ботом:  <code>{} MB</code>"""
    await m.answer(text.format(cpu_usage, psutil.Process().cpu_percent(),
                                            str(ram.total // 1048576), str(ram.used // 1048576),
                                            str(ram.free // 1048576),
                                            str(psutil.Process().memory_info().rss // 1048576)))