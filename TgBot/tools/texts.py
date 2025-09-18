from TgBot.bot_utils import generate_referral_link
from config import cfg
from utils.database import db_users
from utils.database.db_invoices import Invoice, get_sum_deps_from_referrals
from utils.database.db_stars_orders import StarsOrder
from utils.database.db_users import User

from typing import List


def text_profile(user: User, invoices: List[Invoice], buyed_stars: List[StarsOrder]):
    return f"""<b>👔 Мой профиль ⌵</b>

┏ Ваш ID: <code>{user.user_id}</code>
┣ Баланс: <code>{round(user.balance, 2)}</code> <b>{user.currency.upper()}</b>
┗ Имя: <b>{user.full_name}</b>

<b>💰 Статистика ⌵</b>

┏ Всего пополнений: <code>{round(sum([i.amount for i in invoices]), 2)}</code> <b>{user.currency.upper()}</b>
┗ Куплено звёзд: <code>{round(sum([i.stars_amount for i in buyed_stars]))}</code>

Дата регистрации: <b>{user.joinedAt.strftime('%H:%M:%S %d.%m.%Y')}</b>"""


def start_message(name=None):
    return f"""✨ <b>Добро пожаловать{f', {name}' if name else ''}!</b>
    
Бот поможет быстро, дёшево и максимально удобно купить <b>Telegram звёзды</b> на ваш аккаунт"""

def refreal_menu(user: User, bot_name):
    referral_link = generate_referral_link(user.id, bot_name)
    return (f"👥 <b>Реферальная система:</b>\n\n"
            f"Приглашайте друзей и пожизненно получайте <b>{cfg.ref_percent}%</b> с их пополнений!"
            f"\n\nВаша реферальная ссылка:\n{referral_link}\n\n"
            f"▫️ Всего рефералов: <code>{len(db_users.get_referrals(user.id))}</code>\n"
            f"▫️ Заработано: <code>{get_sum_deps_from_referrals(user.id)}</code> <b>{user.currency.upper()}</b>")


# ===================== Admin ======================== #

def stat(
    data_users: dict[str, int],
    data_deposits: dict[str, list[Invoice]]
) -> str:
    return f"""
<b>👤 Статистика пользователей</b>

За день: <code>{data_users['today']}</code>
За неделю: <code>{data_users['week']}</code>
За месяц: <code>{data_users['month']}</code>
За всё время: <code>{data_users['all']}</code>

<b>💰 Статистика платежей</b>

За день: <code>{len(data_deposits['today'])} ({sum([i.amount for i in data_deposits['today']])} ₽)</code>
За неделю: <code>{len(data_deposits['week'])} ({sum([i.amount for i in data_deposits['week']])} ₽)</code>
За месяц: <code>{len(data_deposits['month'])} ({sum([i.amount for i in data_deposits['month']])} ₽)</code>
За всё время: <code>{len(data_deposits['all'])} ({sum([i.amount for i in data_deposits['all']])} ₽)</code>
"""