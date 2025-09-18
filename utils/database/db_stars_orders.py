import random
import string
from datetime import datetime
from sqlalchemy import Column as Col, Integer as Int, Text, Float, DateTime
from . import _base as b

def generate_id():
    return "".join(random.choices(string.ascii_lowercase, k=12))

class StarsOrder(b.BaseClass):
    __tablename__ = 'stars_orders'

    id = Col(Text, nullable=False, default=generate_id, primary_key=True)
    status = Col(Text, nullable=False, default=1)
    stars_amount = Col(Int, nullable=False) #
    total = Col(Float, nullable=False)
    username = Col(Text, nullable=False)
    user_id = Col(Int, nullable=False)
    date = Col(DateTime, default=datetime.now)
    tx_hash = Col(Text, nullable=False)
    amount_ton = Col(Float, nullable=False)

def add_order(order: StarsOrder = None, **kw) -> StarsOrder:
    order = order or StarsOrder(**kw)
    b.sess.add(order)
    b.sess.commit()
    b.sess.refresh(order)
    return order

def get_order(custom_id: str = None, _id: str = None):
    if custom_id:
        return b.sess.query(StarsOrder).filter(StarsOrder.custom_id == custom_id).first()
    elif _id:
        return b.sess.query(StarsOrder).filter(StarsOrder.id == _id).first()
    return None

def get_all_orders():
    return b.sess.query(StarsOrder).all()

def update_order(_id: str, **update_data) -> int:
    order = b.sess.query(StarsOrder).filter(StarsOrder.id == _id).first()
    if not order:
        return 0
    for key, value in update_data.items():
        setattr(order, key, value)
    b.sess.commit()
    b.sess.refresh(order)
    return 1

def get_user_orders(user_id: int) -> list[StarsOrder]:
    return b.sess.query(StarsOrder).filter(StarsOrder.user_id == user_id).all()