from aiogram import Router, F
from aiogram.types import CallbackQuery
from TgBot import CBT, keyboards as kbs
from TgBot.filters.callback import Start
from config import cfg

router = Router()

@router.callback_query(Start(CBT.TOGGLE_NOTIF))
async def open_notifications(c: CallbackQuery):
    split = c.data.split(":")
    if len(split) == 2:
        param = split[-1]
        cfg.toggle(param)
    await c.message.edit_text("<b>Настройки уведомлений</b>", reply_markup=kbs.notify_kb())