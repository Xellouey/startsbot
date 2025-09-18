import aiohttp
from logging import getLogger
from typing import Tuple

logger = getLogger(f"main.{__name__}")


def _join(base: str, path: str) -> str:
    base = (base or "").rstrip("/")
    if not path:
        return base
    return f"{base}/{path.lstrip('/')}"


class LavaAPI:
    def __init__(self, api_key: str, shop_id: str, secret: str,
                 base_url: str = "https://api.lava.ru",
                 success_url: str = None, fail_url: str = None,
                 create_path: str = "/invoices",
                 status_path: str = "/invoices/{id}"):
        self.api_key = api_key
        self.shop_id = shop_id
        self.secret = secret
        self.base_url = (base_url or "https://api.lava.ru").rstrip("/")
        self.success_url = success_url
        self.fail_url = fail_url
        self.create_path = create_path or "/invoices"
        self.status_path = status_path or "/invoices/{id}"
        # Некоторые интеграции Lava используют заголовок X-Api-Key, а не Bearer
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }

    async def create_invoice(self, amount: float, order_id: str, description: str = "") -> Tuple[str, str]:
        payload = {
            "shop_id": self.shop_id,
            "order_id": order_id,
            "amount": amount,
            "currency": "RUB",
            "description": description or f"Пополнение {amount} RUB",
        }
        if self.success_url:
            payload["success_url"] = self.success_url
        if self.fail_url:
            payload["fail_url"] = self.fail_url

        url = _join(self.base_url, self.create_path)
        async with aiohttp.ClientSession(headers=self.headers) as s:
            async with s.post(url, json=payload) as r:
                status = r.status
                try:
                    data = await r.json()
                except Exception:
                    data = {"raw": await r.text()}
        logger.info(f"[LAVA][CREATE] url={url} http={status} resp={data}")
        payment_url = data.get("payment_url") or data.get("url")
        invoice_id = str(data.get("id") or data.get("invoice_id"))
        if not payment_url or not invoice_id:
            raise Exception(f"Lava create_invoice error: {data}")
        return payment_url, invoice_id

    async def check_status(self, invoice_id: str) -> str:
        path = self.status_path.replace("{id}", str(invoice_id))
        url = _join(self.base_url, path)
        async with aiohttp.ClientSession(headers=self.headers) as s:
            async with s.get(url) as r:
                status = r.status
                try:
                    data = await r.json()
                except Exception:
                    data = {"raw": await r.text()}
        logger.info(f"[LAVA][STATUS] url={url} http={status} id={invoice_id} resp={data}")
        status_raw = (data.get("status") or "").lower()
        status_map = {
            "paid": "PAID",
            "pending": "PENDING",
            "canceled": "CANCELED",
            "expired": "EXPIRED",
        }
        return status_map.get(status_raw, "ERROR")
