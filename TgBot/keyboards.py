from TgBot.bot_utils import kb, Btn
from config import cfg
from payments import PaymentMethods
from aiogram.types import InlineKeyboardButton as B, InlineKeyboardMarkup as K
from TgBot import CBT
from utils.tools import is_on


def start_kb():
    lst = [
        [B(text="⭐️ Купить звёзды Telegram", callback_data=CBT.OPEN_MENU)],
        [B(text="👤 Мой профиль ", callback_data=CBT.PROFILE_TELEGRAM)],
        ]
    contacts = []
    if cfg.channel_username:
        contacts.append(B(text='📢 Канал', url=f'https://t.me/{cfg.channel_username.strip("@")}'))
    if cfg.support_username:
        contacts.append(B(text='🎈 Поддержка', url=f'https://t.me/{cfg.support_username.strip("@")}'))
    if contacts:
        lst.append(contacts)
    return K(inline_keyboard=lst)

def req_sub():
    return kb(
        Btn("Перейти на канал", url=f"https://t.me/{cfg.channel_username.strip('@')}"),
        Btn("✅ Я подписался", CBT.CHECK_SUB_CHANNEL),
        row_width=1
    )

def _gen_back_button(callback_data: str = CBT.PROFILE_TELEGRAM):
    return K(inline_keyboard=[[B(text="🔙 Назад", callback_data=callback_data)]])

def clear_state_kb():
    return kb(Btn("❌ Отменить", CBT.CLEAR_STATE))

# ========== пополнение баланса ========== #

def payment_methods_kb(amount: float):
    return K(inline_keyboard=[
        *[[B(text=method.name, callback_data=f"{CBT.PAYMENT_METHOD}:{amount}:{method.id}")] for
         method in PaymentMethods.methods if method.in_range(amount)],
        [B(text="🔙 Назад", callback_data=CBT.PROFILE_TELEGRAM)],
        [B(text="🏘 Назад в главное меню", callback_data=CBT.MAIN_MENU)]
    ])


def go_deposit():
    return kb(Btn("💰 Пополнить баланс", CBT.DEPOSIT_BALANCE))

def success_deposit():
    return kb(Btn("👤 Открыть профиль", F"{CBT.PROFILE_TELEGRAM}:1"))

# ================================ #

def ref_system_kb():
    return _gen_back_button()  # TODO

def waiting(msg = 'Загрузка...'):
    return kb(Btn(f"🕖 {msg}", CBT.EMPTY))


def profile_telegram_menu():
    return K(inline_keyboard=[
        [B(text="💰 Пополнить баланс", callback_data=CBT.DEPOSIT_BALANCE)],
        [B(text="👥 Реферальная система", callback_data=CBT.REFERRAL_SYSTEM)],
        [B(text='🔙 Назад', callback_data=CBT.MAIN_MENU)]
    ])



# ============= стим пополнение ============ #

def buy_stars():
    return kb(
        Btn("⭐️ Купить звёзды", CBT.BUY),
        Btn('🔙 Назад', CBT.MAIN_MENU),
        row_width=1
    )

def stars_dep_confirm_kb(amount, username, to_pay):
    return K(inline_keyboard=[
        [B(text="✅ Подтвердить", callback_data=f"{CBT.CONFIRM_BUY}:{to_pay}:{amount}:{username}")],
        [B(text="❌ Отменить", callback_data=CBT.OPEN_MENU)]
    ])

def dodep_stars():
    return kb(Btn("⭐️ Купить звёзды", f"{CBT.OPEN_MENU}:1"))


# ========================== админ-панель ======================= #

def admin_panel_kb():
    return kb(
        Btn("⚙️ Настройки", CBT.ADMIN_PANEL_SETTINGS),
        Btn("🔔 Уведомления", CBT.TOGGLE_NOTIF),
        row_width=1
    )

def notify_kb():
    return kb(
        *[Btn(f"{is_on(getattr(cfg, arg), true='🔔', false='🔕')} {desc}",
              f"{CBT.TOGGLE_NOTIF}:{arg}") for arg, desc in (
            ('notify_new_user', 'Новый пользователь'),
            ('notify_new_stars_deposit', 'Пополнение Stars'),
            ('notify_new_dep', 'Пополнение баланса')
        )],
        Btn("🔙 Назад", CBT.OPEN_ADMIN_PANEL),
        row_width=1
    )

def settings_admin_kb():
    return kb(
        Btn(f"Реферальный процент: {cfg.ref_percent}%", CBT.ADMIN_EDIT_REF_PERCENT),
        Btn(f"Наценка Stars: {cfg.fee}%", CBT.ADMIN_EDIT_FEE_STEAM),
        Btn("Изменить канал", CBT.EDIT_CHANNEL),
        Btn("Изменить саппорта", CBT.EDIT_SUPPORT_CONTACT),
        Btn('🍪 Изменить куки', CBT.EDIT_COOKIES),
        Btn('🔐 Изменить сид-фразу', CBT.EDIT_MNEMONIC),
        Btn('🔑 Токен TON API', CBT.EDIT_TON_API),
        Btn('👨🏼‍💻 Изменить хеш', CBT.EDIT_HASH),
        Btn("🔙 Назад", CBT.OPEN_ADMIN_PANEL),
        row_width=1
    )