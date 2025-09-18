import datetime
import logging
import time
from threading import Thread

import requests

from .cookies import load_cookies, save_cookies
from .states import load_states, save_states

from .models import ClientOperations

api_url = "https://finance.ozon.ru/api/v2/"

logger = logging.getLogger(f"Utils.{__name__}")


class OzonPAY(requests.Session):
    def __init__(self, pincode: str, cookie_string: str = None, card: str = None):
        super().__init__()
        self.__pin = pincode
        self.__cookie_string = cookie_string or load_cookies(return_str=True)
        self.__card = card

        self.cookies_dict = self._cookies_to_json(self.__cookie_string)

        self.states = load_states()

        self._start_loop()

    def _start_loop(self):
        def _run():
            while True:
                try:
                    self.auth_check()
                except Exception as e:
                    logger.error(f"Ошибка проверки авторизации: {str(e)}")
                time.sleep(60)

        Thread(target=_run, daemon=True).start()


    def get_invoice(self, sum: int):
        """
        Получает инвойс из состояния
        """
        return self.states.get(sum)

    def __call__(self, *args, **kwargs):
        return self._request(*args, **kwargs)

    def __delitem__(self, key):
        if key in self.states:
            del self.states[key]
            save_states(self.states)

    def __setitem__(self, item, value):
        self.states[float(item)] = value
        save_states(self.states)

    def _str_time(self, _time: datetime.datetime):
        return _time.strftime("%d.%m.%Y %H:%M:%S")

    def from_str(self, _time: str):
        return datetime.datetime.strptime(_time, "%d.%m.%Y %H:%M:%S")

    def _request(self, method, json=None, params=None, _method="post") -> dict:
        response = getattr(self, _method)(
            api_url + method, json=json, params=params, headers=self._pre_headers(),
            cookies=self.cookies_dict
        )

        self.cookies.update(response.cookies)
        self.cookies_dict.update(self.cookies.get_dict())
        save_cookies(self.cookies_dict)

        if response.status_code == 401:
            logger.error("Reauthorization Ozon Bank...")
            self._login()
            return self._request(method, json, params, _method)
        if response.status_code == 200:
            return response.json()
        raise Exception(f"request failed\n{response.text}")

    @staticmethod
    def _cookies_to_json(string):
        result = {}
        for cookie in string.split(";"):
            cookie = cookie.strip()
            split = cookie.split("=")
            if len(split) > 1:
                result[split[0]] = split[1]
        return result

    @staticmethod
    def _base_headers():
        return {
            "accept": "application/json",
            "accept-language": "ru-RU,ru;q=0.7",
            "ob-client-version": "4e088df2",
            "origin": "https://finance.ozon.ru",
        }

    def _pre_headers(self):
        headers = self._base_headers()
        headers['cookie'] = self.__cookie_string

    def _login(self) -> bool:
        """
        :return: Успешный ли запрос
        """
        result = tuple(self("auth_login", {"pincode": self.__pin}).values())
        ok = result[0]
        if ok: self.__signToken = result[-1]
        return ok

    def get_credits(self, effect="EFFECT_CREDIT") -> ClientOperations:
        """
        Получает входящие платежи
        """
        return ClientOperations.de_json(self("clientOperations",
                                             {"filter": {"categories": [], "effect": effect},
                                              "cursors": {"next": None, "prev": None}, "perPage": 100}
                                             ))

    def auth_check(self):
        return self("auth_check")

    def check_pay_by_sum(self, sum: int, _raise: bool = True, _del_is_payed: bool = True) -> bool | models.Item:
        """
        Проверяет оплату на заказ
        :param sum: сумма в рублях
        :param _raise: Если True, то бросает исключение при ошибке
        :param _del_is_payed: Если True, то удаляет заказ из состояния, если заказ был оплачен
        :return: bool | models.Item
        """
        try:
            items = self.get_credits().items
            inv = self.get_invoice(sum)
            if not inv:
                return None
            for item in items:
                created_at_ozon, created_at = item.time.replace(tzinfo=datetime.timezone.utc), inv['created_at']
                created_at = self.from_str(created_at).replace(tzinfo=datetime.timezone.utc)
                if item.accountAmount / 100 == sum and created_at_ozon > created_at:
                    if _del_is_payed:
                        del self[sum]
                    print(created_at_ozon, created_at)
                    return item
            return False
        except Exception as e:
            logger.error(f"Ошибка при проверке платежа - {e}")
            logger.debug("TRACEBACK", exc_info=True)
            if _raise: raise e
            return -1


    def gen_inv(self, sum: int, step: int = 0.01, payload={}) -> int:
        """
        Генерирует инвойс, если сумма уже есть в состояниях, то повышает {sum} на {step} пока сумма не будет свободна
        """
        while True:
            if not self.get_invoice(sum):
                break
            sum += step
            sum = round(sum, 2)
        data = {"created_at": self._str_time(datetime.datetime.now(tz=datetime.timezone.utc)), "data": payload}
        self[sum] = data
        return sum

    async def create_invoice(self, *args, **kwargs):
        return self.gen_inv(*args, **kwargs)
