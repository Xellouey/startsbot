import random
import string
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column as Col, Integer as Int, Text, Float, DateTime, Boolean as Bool, ForeignKey
from sqlalchemy.orm import relationship

from config import cfg
from . import _base as b

def generate_id():
    return "".join(random.choices(string.ascii_letters + string.digits, k=12))

class Currency:
    RUB = 'RUB'
    USD = 'USD'

class Roles:
    user = 'user'
    admin = 'admin'

class User(b.BaseClass):
    __tablename__ = 'users'

    id = Col(Text, nullable=False, default=generate_id, primary_key=True)
    full_name = Col(Text, nullable=False)
    username = Col(Text, nullable=True)
    user_id = Col(Int, nullable=False, unique=True)
    joinedAt = Col(DateTime, default=datetime.now)
    updatedAt = Col(DateTime, default=datetime.now, onupdate=datetime.now)
    invited_by = Col(Int, ForeignKey('users.user_id'), nullable=True)
    balance = Col(Float, default=0.0)
    currency = Col(Text, default=Currency.RUB)
    lang = Col(Text, default='ru')
    is_active = Col(Bool, default=True)
    role = Col(Text, nullable=False, default=Roles.user)

    invited_by_user = relationship("User", remote_side=[user_id])

def add_user(user: User = None, **kw):
    user = user or User(**kw)
    b.sess.add(user)
    b.sess.commit()
    b.sess.refresh(user)
    return user

def get_user(user_id: int = None, _id: str = None) -> Optional[User]:
    if user_id:
        return b.sess.query(User).filter(User.user_id == user_id).first()
    elif _id:
        return b.sess.query(User).filter(User.id == _id).first()
    return None

def get_all_users() -> List[User]:
    return b.sess.query(User).all()

def update_user(user_id, **update_data):
    user = b.sess.query(User).filter(User.user_id == user_id).first()
    if not user:
        return 0
    for key, value in update_data.items():
        setattr(user, key, value)
    b.sess.commit()
    b.sess.refresh(user)
    return 1

def add_balance(user_id: int, amount: float, ref_percent: float = cfg.ref_percent):
    user = get_user(user_id=user_id)
    if not user:
        raise ValueError("User not found")

    update_data = {"balance": user.balance + amount}

    if amount > 0.0 and user.invited_by and 0.0 <= ref_percent <= 100.0:
        referral_user = get_user(_id=user.invited_by)
        if referral_user:
            referral_amount = int(amount * (ref_percent / 100))
            update_user(referral_user.user_id, balance=referral_user.balance + referral_amount)

    update_user(user_id, **update_data)

def get_admins() -> list[User]:
    return [u for u in get_all_users() if u.role == Roles.admin]

def get_users_by_date(hours: int = 24) -> list[User]:
    return [
        user for user in get_all_users() if (hours is None or (datetime.now() - user.joinedAt).total_seconds()
            < hours * 60 * 60)
    ]

def get_stat_users():
    data = {}
    users = get_all_users()
    times = [
        ('today', 24),
        ('week', 24 * 7),
        ('month', 24 * 30),
        ('all', None)
    ]
    for period, time in times:
        data[period] = len(get_users_by_date(time))
    data['active'] = len(list(filter(lambda u: u.is_active, users)))
    data['non_active'] = len([u for u in users if not u.is_active])
    return data

def get_referrals(user_id: int) -> list[User]:
    return b.sess.query(User).filter(User.invited_by == user_id).all()
