import random
import string
from datetime import datetime, timedelta
from sqlalchemy import Column as Col, Integer as Int, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from config import cfg
from . import _base as b
from .db_users import User, get_user, get_referrals


def generate_id():
    return "".join(random.choices(string.ascii_letters + string.digits, k=12))

class PayMethods:
    OZON = 1
    YOOMONEY = 2
    CRYPTO_BOT = 3
    TINKOFF = 4
    LAVA = 5

    DESC = {
        OZON: "Перевод",
        YOOMONEY: "ЮMoney",
        CRYPTO_BOT: '🤖 Криптовалюта',
        TINKOFF: '💎 Карта/СБП',
        LAVA: '💳 Lava'
    }

class Status:
    PAID = 1
    PENDING = 0
    ERROR = 3
    CANCELED = 4
    EXPIRED = 5


class Currency:
    RUB = 'RUB'
    USD = 'USD'

class Invoice(b.BaseClass):
    __tablename__ = 'invoices'

    id = Col(Text, nullable=False, default=generate_id, primary_key=True)
    creator_id = Col(Int, ForeignKey('users.user_id'), nullable=True)
    payment_method = Col(Int, nullable=False)
    amount = Col(Float, nullable=False)
    inv_pay_id = Col(Text, nullable=True)
    link = Col(Text, nullable=True)
    commission = Col(Float, default=0.0)
    createdAt = Col(DateTime, default=datetime.now)
    updatedAt = Col(DateTime, default=datetime.now, onupdate=datetime.now)
    status = Col(Int, default=Status.PENDING)
    description = Col(Text, nullable=True)
    payload = Col(Text, nullable=True)
    expiration_hours = Col(Int, nullable=False, default=1)
    expiration_date = Col(DateTime, nullable=False, default=lambda: datetime.now() + timedelta(hours=1))
    currency = Col(Text, nullable=False, default=Currency.RUB)

    user = relationship('User')

    def is_paid(self):
        return self.status == Status.PAID

    @property
    def method_name(self):
        return PayMethods.DESC[self.payment_method]

def add_invoice(invoice: Invoice = None, **kw) -> Invoice:
    invoice = invoice or Invoice(**kw)
    b.sess.add(invoice)
    b.sess.commit()
    b.sess.refresh(invoice)
    return invoice

def get_invoice(invoice_id: str) -> Invoice:
    return b.sess.query(Invoice).filter(Invoice.id == invoice_id).first()

def get_all_invoices(func=None) -> list[Invoice]:
    invoices = b.sess.query(Invoice).all()
    if func:
        return [invoice for invoice in invoices if func(invoice)]
    return invoices

def update_invoice(invoice_id: str, _null_not_update: bool = True, **update_data):
    invoice = b.sess.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        return 0
    for key, value in update_data.items():
        if value is None and _null_not_update:
            continue
        setattr(invoice, key, value)
    invoice.update_date = datetime.now()
    b.sess.commit()
    b.sess.refresh(invoice)
    return 1

def is_invoice_expired(invoice_id: str) -> bool:
    invoice = get_invoice(invoice_id)
    if invoice:
        result = invoice.expiration_date < datetime.now()
        invoice.status = Status.EXPIRED
        b.sess.commit()
        return result
    return False

def get_invoices_by_date(hours: int = 24, invoices=None) -> list[Invoice]:
    return [
        i for i in (invoices or get_all_invoices()) if (i.is_paid() and
        (hours is None or (datetime.now() - i.updatedAt).total_seconds()
            < hours * 60 * 60))
    ]

def get_stat_invoices():
    data = {}
    invoices = get_all_invoices()
    times = [
        ('today', 24),
        ('week', 24 * 7),
        ('month', 24 * 30),
        ('all', None)
    ]
    for period, time in times:
        data[period] = get_invoices_by_date(time, invoices)
    return data

def get_invoices_by_user(user_id: int, invoices=None, **kw) -> list[Invoice]:
    return [
        i for i in (invoices or get_all_invoices()) if i.creator_id == user_id and \
        all(getattr(i, k) == v for k, v in kw.items())
    ]

def get_sum_deps_from_referrals(user_id):
    total = 0
    refs = get_referrals(user_id)
    for ref in refs:
        for invoice in get_invoices_by_user(ref.user_id):
            if invoice.status == Status.PAID:
                total += invoice.amount * (cfg.ref_percent / 100)
    return total