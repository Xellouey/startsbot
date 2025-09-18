from typing import Union
import aiohttp
import random
import string

class YoomoneyAPI:
    def __init__(self, token: str = None):
        self.token = token
        self.client_id = "20E7D579DBAB90D4468FAB31D10940E2A5D69AB9994497CA0D4EF8444673F051"
        self.base_url = 'https://yoomoney.ru/api/'
        self.account = None
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        self.session = aiohttp.ClientSession()

    # Проверка кошелька
    async def check(self) -> str:
        status, response = await self._request("account-info")

        if status:
            if len(response) >= 1:
                text_identified = "Имеется" if response['identified'] else "Отсутствует"

                text_status = {
                    "identified": "Идентифицированный аккаунт",
                    "anonymous": "Анонимный аккаунт",
                    "named": "Именованный аккаунт"
                }.get(response['account_status'], response['account_status'])

                text_type = {
                    "personal": "Личный аккаунт",
                    "professional": "Профессиональный аккаунт"
                }.get(response['account_type'], response['account_type'])

                return f"""
                    Кошелек YooMoney полностью функционален.
                    Кошелек: {response['account']}
                    Идентификация: {text_identified}
                    Статус аккаунта: {text_status}
                    Тип аккаунта: {text_type}
                """
            else:
                return "Не удалось проверить кошелек YooMoney."
        else:
            return "Не удалось проверить кошелек YooMoney."

    async def authorization_get(self) -> str:
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        url = f"https://yoomoney.ru/oauth/authorize?client_id={self.client_id}B&response_type=code&redirect_uri=https://yoomoney.ru&scope=account-info%20operation-history%20operation-details"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers) as response:
                return str(response.url)

    # Принятие кода авторизации и получение токена
    async def authorization_enter(self, get_code: str) -> tuple[bool, str, str]:
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        url = f"https://yoomoney.ru/oauth/token?code={get_code}&client_id={self.client_id}B&grant_type=authorization_code&redirect_uri=https://yoomoney.ru"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers) as response:
                response_data = await response.json()

                if "error" in response_data:
                    error = response_data['error']
                    if error == "invalid_request":
                        return False, "", "<b>❌ Требуемые параметры запроса отсутствуют или имеют неправильные или недопустимые значения</b>"
                    elif error == "unauthorized_client":
                        return False, "", f"""
                            <b>❌ Недопустимое значение параметра 'client_id' или 'client_secret', или приложение
                            не имеет права запрашивать авторизацию (например, ЮMoney заблокировал его 'client_id')</b>
                        """
                    elif error == "invalid_grant":
                        return False, "", f"""
                            <b>❌ В выпуске 'access_token' отказано. ЮMoney не выпускал временный токен,
                            срок действия токена истек, или этот временный токен уже выдан
                            'access_token' (повторный запрос токена авторизации с тем же временным токеном)</b>
                        """

                if response_data['access_token'] == "":
                    return False, "", "<b>❌ Не удалось получить токен. Попробуйте снова.</b>"

                return True, response_data['access_token'], "<b>🔮 ЮMoney кошелек был успешно изменен ✅</b>"

    # Получение баланса
    async def balance(self) -> str:
        status, response = await self._request("account-info")

        if status:
            wallet_balance = response['balance']
            wallet_number = await self.account_info()

            return f"""
                Баланс кошелька YooMoney
                Кошелек: {wallet_number}
                Баланс: {wallet_balance} RUB
            """
        else:
            return "Не удалось получить баланс кошелька YooMoney."

    # Информация об аккаунте
    async def account_info(self):
        status, response = await self._request("account-info")

        self.account = response['account']

        return response['account']

    # Создание платежа
    async def bill(self, pay_amount: Union[float, int]) -> tuple[str, str, str]:
        """
        :return:
        (сообщение, ссылка, айди)
        """
        bill_receipt = self.gen_id()

        get_wallet = self.account or await self.account_info()
        url = "https://yoomoney.ru/quickpay/confirm.xml?"

        pay_amount_bill = pay_amount + (pay_amount * 0.031)

        if float(pay_amount_bill) < 2:
            pay_amount_bill = 2.04

        payload = {
            'receiver': get_wallet,
            'quickpay_form': "button",
            'targets': 'Пожертвование',
            'paymentType': 'SB',
            'sum': pay_amount_bill,
            'label': bill_receipt,
        }

        for value in payload:
            url += str(value).replace("_", "-") + "=" + str(payload[value])
            url += "&"

        async with aiohttp.ClientSession() as session:
            async with session.post(url[:-1].replace(" ", "%20")) as response:
                bill_link = str(response.url)

        bill_message = f"""
            Платеж
            Для пополнения баланса нажмите на кнопку ниже и оплатите выставленный счет
            Сумма платежа: {pay_amount} RUB
            После оплаты нажмите 'Проверить платеж'
        """

        return bill_message, bill_link, bill_receipt

    # Проверка платежа
    async def bill_check(self, bill_receipt: Union[str, int] = None, records: int = 1) -> tuple[int, str]:
        data = {
            'type': 'deposition',
            'details': 'true',
        }

        if bill_receipt is not None:
            data['label'] = bill_receipt
        if records is not None:
            data['records'] = records

        status, response = await self._request("operation-history", data)

        operations = response['operations']
        if not operations:
            return 2, "Заказ не оплачен"
        if any(op['amount_currency'] == "RUB" for op in operations):
            return 0, "pass"
        elif len(operations) >= 1:
            return 4, "Другая валюта"
        return 1, "Счет истек"

    # Запрос
    async def _request(self, method: str, data: dict = None) -> tuple[bool, any]:
        url = self.base_url + method

        async with self.session.post(url, headers=self.headers, data=data) as response:
            try:
                response_data = await response.json()
                if response.status == 200:
                    return True, response_data
                else:
                    return False, response_data
            except Exception as ex:
                return False, str(ex)

    # Генерация ID
    def gen_id(self):
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
