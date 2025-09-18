import time
from config import cfg
from utils.database.db_invoices import Invoice, PayMethods, Status
from utils.tools import time_to_str
from .crypto_bot import CryptoBotAPI
from .ozon import OzonPAY
from .tinkof import generate_payment_link, check_payment_status, logger
from .yoomoney import YoomoneyAPI
from .lava import LavaAPI

ozon_api = OzonPAY(cfg.ozon_pin, cfg.ozon_cookies)
yoomoney_api = YoomoneyAPI(cfg.yoomoney_token)
send = CryptoBotAPI(cfg.crypto_bot_token)
lava_api = LavaAPI(
    cfg.lava_api_key,
    cfg.lava_shop_id,
    cfg.lava_secret,
    cfg.lava_base_url,
    cfg.lava_success_url,
    cfg.lava_fail_url,
    create_path=cfg.lava_create_path,
    status_path=cfg.lava_status_path,
)

class PaymentMethod:
    def __init__(self, min_amount: float, max_amount: float, id: str, name: str):
        self.min_amount = min_amount
        self.max_amount = max_amount
        self.id = id
        self.name = name

    def in_range(self, amount: float):
        return self.min_amount <= amount <= self.max_amount

class PaymentMethods:
    yoomoney = PaymentMethod(15, 30_000, PayMethods.YOOMONEY, PayMethods.DESC[PayMethods.YOOMONEY])
    ozon = PaymentMethod(100, 50_000, PayMethods.OZON, PayMethods.DESC[PayMethods.OZON])
    crypto_bot = PaymentMethod(15, 50_000, PayMethods.CRYPTO_BOT, PayMethods.DESC[PayMethods.CRYPTO_BOT])
    tinkoff = PaymentMethod(10, 50_000, PayMethods.TINKOFF, PayMethods.DESC[PayMethods.TINKOFF])
    lava = PaymentMethod(10, 50_000, PayMethods.LAVA, PayMethods.DESC[PayMethods.LAVA])
    methods = [crypto_bot, lava]  # UI: скрываем Tinkoff, показываем Lava

    @staticmethod
    def get(id=None, name=None):
        if id:
            return next((m.name for m in PaymentMethods.methods if m.id == id), None)
        if name:
            return next((m.name for m in PaymentMethods.methods if m.name == name), None)
        return PaymentMethods.methods

async def generate_inv(inv: Invoice, new_amount=None, link=None, text=None, inv_id=None) -> tuple:
    if inv.payment_method == PayMethods.OZON:
        new_amount = await ozon_api.create_invoice(inv.amount, payload={"user_id": inv.user.id})
        text = (f"💳 <b>Сумма: {new_amount} RUB</b>\n"
                f"Метод оплаты: <b>{inv.method_name}. Ozon Банк</b>\n\n"
                f"Переведите на карту точную сумму:\n"
                f"- <code>{cfg.ozon_card}</code>\n\n"
                f" • У вас есть <b>{time_to_str(inv.expiration_hours * 3600)}</b> для оплаты")
    elif inv.payment_method == PayMethods.YOOMONEY:
        _, link, inv_id = await yoomoney_api.bill(pay_amount=inv.amount)
    elif inv.payment_method == PayMethods.CRYPTO_BOT:
        invoice = send.create_invoice(amount=inv.amount, currency_type="fiat", fiat="RUB", expires_in=inv.expiration_hours * 3600)
        link = invoice.bot_invoice_url
        inv_id = invoice.invoice_id
    elif inv.payment_method == PayMethods.TINKOFF:
        link, inv_id = await generate_payment_link(username=f"user_{inv.creator_id}", stars_count=int(inv.amount))
        text = f"🏦 <b>Сумма: {inv.amount} RUB</b>\nМетод оплаты: <b>Tinkoff</b>\n\n" \
               f" • У вас есть <b>{time_to_str(inv.expiration_hours * 3600)}</b> для оплаты"
    elif inv.payment_method == PayMethods.LAVA:
        link, inv_id = await lava_api.create_invoice(amount=inv.amount, order_id=inv.id,
                                                     description=f"Пополнение баланса {inv.amount} RUB")
        text = f"💳 <b>Сумма: {inv.amount} RUB</b>\nМетод оплаты: <b>{inv.method_name}</b>\n\n" \
               f" • У вас есть <b>{time_to_str(inv.expiration_hours * 3600)}</b> для оплаты"
    else:
        return (-1,) * 4
    return link, inv_id, text, new_amount

async def check_pay(inv: Invoice):
    if inv.payment_method == PayMethods.OZON:
        return ozon_api.check_pay_by_sum(inv.amount)
    if inv.payment_method == PayMethods.CRYPTO_BOT:
        inv = send.get_invoices(invoice_ids=[inv.inv_pay_id])[0]
        if not inv:
            return Status.CANCELED
        status = inv.status
        if status == "paid":
            return Status.PAID
        elif status == "active":
            return Status.PENDING
        elif status == "expired":
            return Status.EXPIRED
    elif inv.payment_method == PayMethods.YOOMONEY:
        status, _ = await yoomoney_api.bill_check(inv.inv_pay_id)
        _results = {0: Status.PAID, 1: Status.EXPIRED, 2: Status.PENDING}
        status = int(status)
        if status in _results:
            return _results[status]
        return Status.ERROR
    elif inv.payment_method == PayMethods.TINKOFF:
        status = await check_payment_status(inv.inv_pay_id)
        if status == -1:
            return Status.ERROR
        result = getattr(Status, status, Status.ERROR)
        logger.info(f'Статус: {status}. Конечный статус: {result}')
        return result
    elif inv.payment_method == PayMethods.LAVA:
        status = await lava_api.check_status(inv.inv_pay_id)
        _map = {"PAID": Status.PAID, "PENDING": Status.PENDING, "CANCELED": Status.CANCELED, "EXPIRED": Status.EXPIRED}
        return _map.get(status, Status.ERROR)
    return Status.ERROR

async def cancel_order(inv: Invoice) -> bool:
    if inv.payment_method == PayMethods.CRYPTO_BOT:
        send.delete_invoice(inv.inv_pay_id)
        return True
    if inv.payment_method == PayMethods.OZON:
        del ozon_api[inv.amount]
        return True
    return False
