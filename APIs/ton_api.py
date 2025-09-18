import re
import asyncio
import base64
import logging
import time
from threading import Thread
from typing import Optional, List, Dict, Any, Tuple
from queue import Queue

import aiohttp
import requests
from bs4 import BeautifulSoup
from tonutils.client import TonapiClient
from tonutils.wallet import WalletV5R1

logger = logging.getLogger(f"main.{__name__}")
COURSE_STARS_TO_TON: Optional[float] = None

_lastUpdate: Optional[float] = None
_ton_course = None
_INTERVAL_UDPATE = 30

def ton_to_rub():
    global _ton_course, _lastUpdate
    if _ton_course is None or _lastUpdate is None or (time.time() - _lastUpdate) > _INTERVAL_UDPATE:
        _ton_course = requests.get(
            'https://api.coingecko.com/api/v3/coins/the-open-network'
        ).json()['market_data']['current_price']['rub']
        _lastUpdate = time.time()
    return _ton_course

class FragmentAPIError(Exception): pass
class BadRequest(Exception):
    def __init__(self, response):
        self.response = response
    def __str__(self):
        return self.__class__.__name__
class NotFindedUsername(Exception): pass
class GetProfileError(Exception): pass
class CantGiftUsername(Exception): pass

class InsufficientFundsError(Exception):
    def __init__(self, price: float, balance: float):
        super().__init__(f"Недостаточно TON: нужно {price}, баланс {balance}")
        self.price, self.balance = price, balance

class FragmentAPI:
    def __init__(self, ton_api_key: str, mnemonic: List[str], hash: str, cookie: str, testnet: bool = False):
        self._api_key = ton_api_key
        self._mnemonic = mnemonic
        self.hash = hash
        self.cookie = cookie
        self._is_testnet = testnet
        self._balance = -1
        self.inited = False
        self.name = self.username = None
        self.client: Optional[TonapiClient] = None
        self.wallet: Optional[WalletV5R1] = None
        self._headers = {
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://fragment.com',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/133.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        }
        self.session = aiohttp.ClientSession()
        self._lastTime = None
        self.init()
        self.to_transfer = Queue()
        self._res = {}
        self.start_transfer_worker()

    @property
    def cookie_dict(self) -> Dict[str, str]:
        return dict(list(map(str.strip, item.split('='))) for item in self.cookie.split(';') if item)

    def init(self):
        if not (self._api_key and self._mnemonic): return
        try:
            self.client = TonapiClient(api_key=self._api_key, is_testnet=self._is_testnet)
            self.wallet, _, _, _ = WalletV5R1.from_mnemonic(self.client, self._mnemonic)
            self.inited = True
            logger.info(f"Инициализирован FragmentAPI. Сид: {' '.join(self._mnemonic)}")
        except Exception as e:
            logger.error(f"Ошибка инициализации TON: {e}")

    @property
    def headers(self):
        self._headers.update({'cookie': self.cookie})
        return self._headers

    async def init_profile(self):
        if not self.cookie: return
        try:
            self.name, self.username = self.get_profile(self.cookie)
            return True
        except GetProfileError as e:
            logger.error(f"Ошибка профиля: {e}")
            return False

    async def _request(self, method: str, data: Dict[str, Any]) -> aiohttp.ClientResponse:
        url = f"https://fragment.com/api?hash={self.hash}"
        data.update({'method': method})
        async with self.session.post(url, headers=self.headers, data=data, cookies=self.cookie_dict) as response:
            if 'Bad request' in await response.text():
                raise BadRequest(response)
            if response.status != 200:
                raise FragmentAPIError(f"Ошибка API: {await response.text()[:500]}")
            return response

    async def get_balance(self) -> float:
        if not (self.wallet and self.client): return -1
        try:
            self._balance = await self.wallet.balance()
            if self._balance > 1e5:
                self._balance /= 1e9
            return self._balance
        except Exception as e:
            logger.error(f"Ошибка получения баланса: {e}")
            return -1

    async def search_stars_recipient(self, username: str, via_st: bool = False) -> Tuple[str, str]:
        if not via_st:
            return await self._search_stars_recipient(username)
        return await self._split_tg_recipient(username)

    async def _search_stars_recipient(self, username: str) -> Tuple[str, str]:
        data = {"query": username, "quantity": "", "method": "searchStarsRecipient"}
        result = await (await self._request("searchStarsRecipient", data)).json()
        if result.get('error') == "No Telegram users found.":
            raise NotFindedUsername(f'[{self.name}] Не найден ник @{username}')
        if "found" not in result:
            raise FragmentAPIError(f"[{self.name}] Получатель не найден", result)
        return result["found"]["recipient"], result["found"]["name"]

    async def _split_tg_recipient(self, username: str) -> Tuple[str, str]:
        async with self.session.post('https://api.split.tg/recipients/stars', json={"username": username}) as resp:
            if resp.status == 400:
                raise NotFindedUsername(f'[split.tg] Не найден ник @{username}')
            result = await resp.json()
            if result.get('error') == "No Telegram users found.":
                raise NotFindedUsername(f'[{self.name}] Не найден ник @{username}')
            if "gift Telegram Stars to this account at this moment" in result.get('error', ''):
                raise CantGiftUsername(f'[{self.name}] Нельзя дарить на юзернейм @{username}')
            if not result.get("ok", False) or not result.get("message"):
                raise FragmentAPIError(f"Ошибка split.tg ({result.get('code')}): {result.get('error_message')}")
            return result['message']['recipient'], result['message']['name']

    async def update_stars_prices(self, stars_count: int):
        data = {"method": "updateStarsPrices", "stars": stars_count, "quantity": stars_count}
        return await (await self._request("updateStarsPrices", data)).json()

    async def init_buy_stars_request(self, recipient: str, stars_count: int) -> str:
        data = {"method": "initBuyStarsRequest", "recipient": recipient, "quantity": stars_count, "stars": stars_count}
        result = await (await self._request("initBuyStarsRequest", data)).json()
        req_id = result.get("req_id")
        if not req_id:
            raise FragmentAPIError(f"ID запроса не найден: {str(result)[:500]}")
        return req_id

    async def get_buy_stars_link(self, req_id: str, show_me: bool = False) -> Dict[str, Any]:
        data = {
            "method": "getBuyStarsLink",
            "account": '{"address":"","chain":"-239","":""}',
            "device": '{"platform":"windows","appName":"Tonkeeper","appVersion":"3.27.1","maxProtocolVersion":2,"features":'
                      '["SendTransaction",{"name":"SendTransaction","maxMessages":10}]}',
            "transaction": 1,
            "id": req_id,
            "show_sender": int(show_me)
        }
        return await (await self._request("getBuyStarsLink", data)).json()

    def _handle_delay(self, d: int = 5):
        if self._lastTime:
            time.sleep(max(d - time.time() + self._lastTime, 0))
        self._lastTime = time.time()

    def start_transfer_worker(self, delay: int = 5):
        def run():
            while True:
                if self.to_transfer.empty():
                    time.sleep(1)
                    continue
                tag, address, amount, payload = self.to_transfer.get()
                tag = f"@{tag.strip('@')}"
                e = None
                for _ in range(3):
                    try:
                        res = asyncio.run(self.wallet.transfer(destination=address, amount=amount, body=payload))
                        logger.info(f'[{tag}] Отправил {amount} TON на {address}. Комментарий: {payload}. Хеш: {res}')
                        break
                    except Exception as e:
                        logger.debug(f"Ошибка отправки: {e}")
                        time.sleep(1)
                else:
                    res = Exception(f"Не удалось отправить звезды: {e}")
                self._res[payload] = res
                time.sleep(delay)
        Thread(target=run, daemon=True).start()

    async def _send_ton(self, username, address, amount, payload):
        self.to_transfer.put((username, address, amount, payload))
        while payload not in self._res:
            await asyncio.sleep(0.5)
        res = self._res.pop(payload)
        if isinstance(res, BaseException):
            raise res
        return res

    async def send_stars_async(self, username: str, stars_count: int, recipient: str = None) -> Tuple[float, str, int, str, str, str]:
        global COURSE_STARS_TO_TON
        req_id = None
        for attempt in range(5):
            try:
                st = time.time()
                if not recipient:
                    recipient, _ = await self.search_stars_recipient(username)
                await self.update_stars_prices(stars_count)
                if not req_id:
                    req_id = await self.init_buy_stars_request(recipient, stars_count)
                result = await self.get_buy_stars_link(req_id)
                msg = result["transaction"]["messages"][0]
                address, amount = msg["address"], float(msg["amount"]) / 1e9
                payload = await self._decode_payload(msg["payload"])
                if payload in self._res:
                    logger.info(f"Транзакция с payload {payload} уже отправлена")
                    continue
                balance = await self.get_balance()
                if balance == -1: balance = self._balance
                if balance < amount: raise InsufficientFundsError(amount, balance)
                self._handle_delay()
                tx_hash = await self._send_ton(username, address, amount, payload)
                if await self._verify_transaction(tx_hash) == -1:
                    logger.info(f"Транзакция {tx_hash} не подтверждена, повтор...")
                    continue
                self._balance -= amount
                COURSE_STARS_TO_TON = amount / stars_count
                logger.info(f"Отправил {stars_count} звезд на @{username}. ID: {recipient}. За {round(time.time() - st, 2)} сек.")
                return amount, tx_hash, stars_count, username, payload.split("\n")[-1], recipient
            except Exception as e:
                logger.error(f"Попытка {attempt + 1} не удалась: {e}")
                if attempt == 4: raise e
                await asyncio.sleep(2)
        raise FragmentAPIError("Не удалось отправить звезды после 5 попыток")

    def send_stars(self, username: str, stars_count: int, recipient: str = None) -> Tuple[float, str, int, str, str, str]:
        return asyncio.run(self.send_stars_async(username, stars_count, recipient))

    async def _decode_payload(self, payload: str) -> Optional[str]:
        try:
            if len(payload) % 4: payload += '=' * (4 - len(payload) % 4)
            decoded = base64.b64decode(payload).decode('utf-8', errors='ignore')
            match = re.search(r'([0-9]+)\s+Telegram Stars\s+Ref#[A-Za-z0-9]{9}', decoded, re.DOTALL)
            return match.group(0) if match else decoded
        except Exception as e:
            logger.error(f"Ошибка декодирования payload: {e}")
            return None

    async def _verify_transaction(self, tx_hash: str) -> int:
        not_trans = 0
        for _ in range(100):
            res = await self.is_transaction_confirmed(tx_hash)
            if res == -1:
                not_trans += 1
                if not_trans < 6:
                    await asyncio.sleep(4)
                    continue
                return -1
            if res: return 1
            await asyncio.sleep(1)
        return 0

    async def is_transaction_confirmed(self, tx_hash: str) -> int:
        try:
            async with self.session.get(f"https://tonviewer.com/transaction/{tx_hash}") as response:
                text = (await response.text()).lower()
                exists = "stars" in text and "fragment" in text
                conf = 'confirmed transaction' in text
                return 1 if conf else (-1 if not exists else 0)
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка проверки транзакции: {e}")
            return 0

    @staticmethod
    def get_profile(cookie: str) -> Tuple[str, str]:
        with requests.get("https://fragment.com/my/profile", headers={
            'accept': 'text/html,application/xhtml+xml,*/*;q=0.8',
            'cookie': cookie,
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/132.0.0.0 Safari/537.36',
        }) as response:
            if response.status_code != 200:
                raise GetProfileError(response)
            soup = BeautifulSoup(response.text, "html.parser")
            try:
                return (soup.find('div', class_="tm-settings-item-head").text,
                        soup.find('div', class_="tm-settings-item-desc").text)
            except AttributeError:
                raise GetProfileError(response, "Ошибка разбора профиля")

    async def star_price(self, q: float = 100.0) -> float:
        response = await self._request('updateStarsPrices', {'stars': q, 'quantity': q})
        html_price = (await response.json()).get('cur_price')
        soup = BeautifulSoup(html_price, 'html.parser')
        ton_value = soup.select_one('.tm-value').get_text(strip=True).replace('<span class="mini-frac">', '').replace('</span>', '')
        return float(ton_value) / q

    @property
    def mnemonic(self):
        return self._mnemonic

    @mnemonic.setter
    def mnemonic(self, value):
        self._mnemonic = value

    @property
    def api_key(self):
        return self._api_key

    @api_key.setter
    def api_key(self, val):
        self._api_key = val


api = FragmentAPI('', [], '', '')