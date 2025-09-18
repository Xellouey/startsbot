import asyncio
import time
import hashlib
import aiohttp
from logging import getLogger
from fastapi import FastAPI
from pydantic import BaseModel

TERMINAL_KEY = "1733840121286"
SECRET_KEY = "5gqjyhq6s3ckhv0b"

logger = getLogger(f"main.{__name__}")
pending_orders = {}
app = FastAPI()

def generate_token(data: dict, password: str) -> str:
    token_fields = {k: v for k, v in data.items() if isinstance(v, (str, int, float)) and k != "Token"}
    token_fields["Password"] = password
    sorted_items = sorted(token_fields.items())
    token_string = ''.join(str(value) for _, value in sorted_items)
    logger.info(f"[TOKEN STRING]: {token_string}")
    return hashlib.sha256(token_string.encode('utf-8')).hexdigest()

async def generate_payment_link(username: str, stars_count: int, phone: str = "", email: str = ""):
    order_id = f"{username}_{stars_count}_{int(time.time())}"
    amount = stars_count * 100
    description = f"Пополнение баланса {stars_count} рублей"
    phone = phone or "+79999999999"
    email = email or 'example@gmail.com'

    token_fields = {
        "TerminalKey": TERMINAL_KEY,
        "Amount": amount,
        "OrderId": order_id,
        "Description": description,
        "Language": "ru",
        "PayType": "O",
        "Recurrent": "N",
        "SuccessURL": f"http://t.me/EsqStarsBot",
        "FailURL": f"http://t.me/EsqStarsBot"
    }

    token = generate_token(token_fields, SECRET_KEY)

    data = {
        **token_fields,
        "Token": token,
        "DATA": {
            "Phone": phone,
            "Email": email,
        },
        "Receipt": {
            "Phone": phone,
            "Email": email,
            "Taxation": "usn_income",
            "Items": [{
                "Name": "Telegram Stars",
                "Quantity": "1",
                "Amount": amount,
                "Tax": "none",
                "Price": amount
            }]
        }
    }

    logger.info(f"👉 Инициализация платежа OrderId: {order_id} Сумма: {amount}")
    async with aiohttp.ClientSession() as session:
        response = await session.post("https://securepay.tinkoff.ru/v2/Init", json=data)
        result = await response.json()

    logger.info(f"🔁 Ответ Init: {result}")
    if result.get("Success"):
        payment_id = result.get("PaymentId")
        pending_orders[order_id] = (username, stars_count, payment_id)
        return result["PaymentURL"], payment_id
    raise Exception(f"Ошибка инициализации: {result.get('Message')} | {result.get('Details')}")

async def check_payment_status(payment_id: str) -> str | int:
    token_string = f"{SECRET_KEY}{payment_id}{TERMINAL_KEY}"
    token = hashlib.sha256(token_string.encode('utf-8')).hexdigest()

    data = {
        "TerminalKey": TERMINAL_KEY,
        "PaymentId": payment_id,
        "Token": token
    }

    status_map = {
        "NEW": "PENDING",
        "FORM_SHOWED": "PENDING",
        "AUTHORIZING": "PENDING",
        "CHECKING": "PENDING",
        "AUTHORIZED": "PENDING",
        "CONFIRMING": "PENDING",
        "CONFIRMED": "PAID",
        "REVERSED": "CANCELED",
        "REFUNDED": "CANCELED",
        "REJECTED": "CANCELED",
        "CANCELED": "CANCELED",
        "DEADLINE_EXPIRED": "EXPIRED"
    }

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
        for attempt in range(3):
            try:
                logger.info(f"👉 Попытка {attempt + 1} проверки платежа {payment_id}")
                async with session.post("https://securepay.tinkoff.ru/v2/GetState", json=data) as response:
                    response.raise_for_status()
                    result = await response.json()
                    logger.info(f"📦 Ответ от Tinkoff: {result}")
                    if result.get("ErrorCode") != '0':
                        return -1
                    status = result.get("Status", "UNKNOWN")
                    return status_map.get(status, "ERROR")
            except aiohttp.ClientError as e:
                logger.error(f"Ошибка проверки платежа {payment_id}: {e}")
                if attempt == 2:
                    return "ERROR"
                await asyncio.sleep(1)
    return "ERROR"

class TinkoffCallback(BaseModel):
    OrderId: str
    Success: bool
    Status: str
    PaymentId: str
    DATA: dict = {}

@app.post("/webhook")
async def tinkoff_webhook(data: TinkoffCallback):
    logger.info(f"📨 Вебхук: OrderId={data.OrderId}, Success={data.Success}, Status={data.Status}")
    if data.Success and data.Status == "CONFIRMED":
        order_id = data.OrderId
        username, stars_count, _ = pending_orders.pop(order_id, (None, None, None))
        if username:
            logger.info(f"✅ Оплата подтверждена: @{username} получил {stars_count} звёзд.")
        else:
            logger.info(f"⚠️ Заказ не найден в pending_orders.")
    return {"ok": True}

@app.get("/check_order/{order_id}")
async def check_order(order_id: str):
    if order_id not in pending_orders:
        return {"ok": False, "message": "Заказ не найден"}

    username, stars_count, payment_id = pending_orders[order_id]
    status = await check_payment_status(payment_id)
    logger.info(f"📊 Статус платежа: {status}")

    if status == "PAID":
        pending_orders.pop(order_id, None)
        logger.info(f"✅ Подтверждено: @{username} получил {stars_count} звёзд.")
        return {"ok": True, "message": f"Платёж подтверждён. @{username} получил {stars_count} звёзд."}

    if status in ["CANCELED", "EXPIRED"]:
        pending_orders.pop(order_id, None)
        logger.info(f"❌ Платёж отклонён или истёк срок. Статус: {status}")
        return {"ok": False, "message": f"Платёж не прошёл. Статус: {status}"}

    logger.info(f"⏳ Платёж в процессе. Статус: {status}")
    return {"ok": False, "message": f"Платёж ещё не завершён. Текущий статус: {status}"}