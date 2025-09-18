import os
import zipfile
from io import BytesIO
from typing import ContextManager

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, BufferedInputFile, FSInputFile
from aiogram import Bot

from config import cfg
from utils.database import db_users
from utils.database.db_users import get_admins
from utils.tools import ImagesLoader, get_date


class Btn:
    def __init__(
        self,
        text: str,
        callback: str = None,
        url: str = None
    ):
        self.text, self.callback_data, self.url = text, callback, url

def kb(*btns: InlineKeyboardButton | Btn, lst: list[Btn] = [], row_width: int = 3) -> InlineKeyboardMarkup:
    kbs = []
    row = []
    for btn in (lst or btns):
        if isinstance(btn, Btn):
            btn = InlineKeyboardButton(**btn.__dict__)
        row.append(btn)
        if len(row) == row_width:
            kbs.append(row)
            row = []
    if row:
        kbs.append(row)
    return InlineKeyboardMarkup(inline_keyboard=kbs)


async def check_sub_channel(
    bot: Bot,
    user_id: int
) -> bool:
    if not cfg.channel_username or not cfg.required_sub:
        return True
    try:
        user = await bot.get_chat_member(f"@{cfg.channel_username.strip('@')}", user_id)
        return user is not None and user.status not in ("left",)
    except:
        return False


def generate_referral_link(user_id: int, bot_name: str) -> str:
    return f"https://t.me/{bot_name}?start=r_{user_id}"

def tag_user(name: str, user_id: int, add_id: bool = True):
    text = f"<a href='tg://user?id={user_id}'>{name}</a>"
    if add_id:
        text += f' (<code>{user_id}</code>)'
    return text

async def answer_with_banner(
    msg: Message,
    text: str,
    reply_kb: InlineKeyboardMarkup = None,
    banner_name: str = 'banner',
    **kw
):
    result = ImagesLoader.load_banner(banner_name=banner_name)
    _objs = {
        'gif': 'animation',
        'mp4': 'animation',
        'jpg': 'photo',
        'png': 'photo',
        'jpeg': 'photo'
    }
    if not result:
        return await msg.answer(text, reply_markup=reply_kb, **kw)
    else:
        banner, ext = result
        await getattr(msg, f"answer_{_objs[ext]}")(
            BufferedInputFile(banner, f'banner.{ext}'), caption=text, reply_markup=reply_kb, **kw
        )

def get_backup() -> ContextManager[BytesIO]:
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for root, _, files in os.walk('storage'):
            for file in files:
                file_path = os.path.join(root, file)
                zip_file.write(file_path, os.path.relpath(file_path, 'storage'))
    zip_buffer.seek(0)
    return zip_buffer

async def autobackup_admin(bot: Bot):
    for admin in get_admins():
        try:
            await bot.send_document(
                admin,
                FSInputFile("../storage/base.db"),
                caption=f"<b>📦 #BACKUP | <code>{get_date(full=False)}</code></b>",
                disable_notification=True,
            )
        except:
            ...


async def edit_msg(
    m: Message,
    text: str = None,
    reply_markup: InlineKeyboardMarkup = None,
    **kw
):
    func = getattr(
        m, f"edit_{('text' if m.text else 'caption') if text else 'reply_markup'}"
    )
    if text:
        kw['text'] = text
    if reply_markup:
        kw['reply_markup'] = reply_markup
    return await func(**kw)