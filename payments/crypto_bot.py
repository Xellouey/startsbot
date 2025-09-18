import gc
from datetime import datetime
from typing import Optional, Type, Union, Any, List

import httpx
from pydantic import BaseModel


class CodeErrorFactory(Exception):
    """CryptoPay API Exception"""

    def __init__(self, code: int = None, name: str = None) -> None:
        self.code = int(code) if code else None
        self.name = name
        super().__init__(self.code)

    @classmethod
    def __call__(
        cls, code: Optional[int] = None, name: Optional[int] = None
    ) -> Union["CodeErrorFactory", Type["CodeErrorFactory"]]:
        if name:
            return cls.exception_to_raise(code, str(name))
        return cls.exception_to_handle(code)

    @classmethod
    def exception_to_handle(
        cls, code: Optional[int] = None
    ) -> Type["CodeErrorFactory"]:
        if code is None:
            return cls

        catch_exc_classname = cls.generate_exc_classname(code)

        for obj in gc.get_objects():
            if obj.__class__.__name__ == catch_exc_classname:
                return obj.__class__

        return type(catch_exc_classname, (cls,), {})

    @classmethod
    def exception_to_raise(cls, code: int, name: str) -> "CodeErrorFactory":
        """Returns an error with error code and error_name"""
        exception_type = type(cls.generate_exc_classname(code), (cls,), {})
        return exception_type(code, name)

    @classmethod
    def generate_exc_classname(cls, code: Optional[int]) -> str:
        """Generates unique exception classname based on error code"""
        return f"{cls.__name__}_{code}"

    def __str__(self):
        return f"[{self.code}] {self.name}\n"


CryptoPayAPIError = CodeErrorFactory()


class Invoice(BaseModel):
    invoice_id: int
    status: Union[Any, str]
    hash: str
    asset: Optional[Union[Any, str]] = None
    amount: Union[int, float]
    bot_invoice_url: str
    web_app_invoice_url: str
    mini_app_invoice_url: str
    description: Optional[str] = None
    created_at: datetime
    allow_comments: bool
    allow_anonymous: bool
    expiration_date: Optional[str] = None
    paid_at: Optional[datetime] = None
    paid_anonymously: Optional[bool] = None
    comment: Optional[str] = None
    hidden_message: Optional[str] = None
    payload: Optional[str] = None
    paid_btn_name: Optional[Union[Any, str]] = None
    paid_btn_url: Optional[str] = None
    currency_type: Union[Any, str]
    fiat: Optional[str] = None
    paid_asset: Optional[Union[Any, str]] = None
    paid_amount: Optional[Union[int, float]] = None
    paid_usd_rate: Optional[Union[int, float]] = None
    paid_fiat_rate: Optional[Union[int, float]] = None
    fee_asset: Optional[Union[Any, str]] = None
    fee_amount: Optional[Union[int, float]] = None
    fee_in_usd: Optional[Union[int, float]] = None
    accepted_assets: Optional[Union[List[Union[Any, str]], str]] = None


class CryptoBotAPI:
    def __init__(
        self, token: str
    ) -> None:
        super().__init__()
        """
        Init CryptoPay API client
            :param token: Your API token from @CryptoBot
            :param network: Network address https://help.crypt.bot/crypto-pay-api#HYA3
        """
        self.__token = token
        self.network = "https://pay.crypt.bot"
        self.__headers = {'Content-Type': 'application/json', 'Crypto-Pay-API-Token': self.__token}
        self._handlers = []

    @staticmethod
    def _validate_response(response: dict) -> dict:
        """Validate response"""
        if not response.get("ok"):
            name = response["error"]["name"]
            code = response["error"]["code"]
            raise CryptoPayAPIError(code, name)
        return response

    def _make_request(self, method: str, url: str, **kwargs) -> dict:
        """
        Make a request.
            :param method: HTTP Method
            :param url: endpoint link
            :param kwargs: data, params, json and other...
            :return: status and result or exception
        """
        client = httpx.Client()
        response = client.request(method, url, **kwargs)
        response.raise_for_status()
        response_json = response.json()
        return self._validate_response(response_json)

    def create_invoice(
        self,
        amount: Union[int, float],
        asset: Optional[Union[Any, str]] = None,
        description: Optional[str] = None,
        hidden_message: Optional[str] = None,
        paid_btn_name: Optional[Union[Any, str]] = None,
        paid_btn_url: Optional[str] = None,
        payload: Optional[str] = None,
        allow_comments: Optional[bool] = None,
        allow_anonymous: Optional[bool] = None,
        expires_in: Optional[int] = None,
        fiat: Optional[str] = None,
        currency_type: Optional[Union[Any, str]] = None,
        accepted_assets: Optional[Union[List[Union[Any, str]], str]] = None,
    ) -> Invoice:
        """
        Use this method to create a new invoice.
        https://help.crypt.bot/crypto-pay-api#createInvoice

        Args:
            asset (Optional[Union[Assets, str]]): Currency code if the field currency_type has crypto as a value. Supported assets: “USDT”, “TON”, “BTC”, “ETH”, “LTC”, “BNB”, “TRX” and “USDC”.
            amount (Union[int, float]): Amount of the invoice in float or int. For example: 125.50
            description (Optional[str], optional): Description for the invoice. User will see this description when they pay the invoice. Up to 1024 characters.
            hidden_message (Optional[str], optional): Text of the message that will be shown to a user after the invoice is paid. Up to 2o48 characters.
            paid_btn_name (Optional[Union[PaidButtons, str]], optional): Name of the button that will be shown to a user after the invoice is paid.
            paid_btn_url (Optional[str], optional): Required if paid_btn_name is used.URL to be opened when the button is pressed. You can set any success link (for example, a link to your bot). Starts with https or http.
            payload (Optional[str], optional): Any data you want to attach to the invoice (for example, user ID, payment ID, ect). Up to 4kb.
            allow_comments (Optional[bool], optional): Allow a user to add a comment to the payment. Default is true.
            allow_anonymous (Optional[bool], optional): Allow a user to pay the invoice anonymously. Default is true.
            expires_in (Optional[int], optional): You can set a payment time limit for the invoice in seconds. Values between 1-2678400 are accepted.
            fiat (Optional[str], optional): Fiat currency code if the field currency_type has fiat as a value. Supported fiat currencies: All fiats in CryptoBot
            currency_type (Optional[Union[CurrencyType, str]], optional): Type of the price, can be “crypto” or “fiat”. Default is crypto.
            accepted_assets (Optional[Union[List[Union[Assets, str]], str]], optional): Assets which can be used to pay the invoice if the field fiat has a value. Supported assets: “USDT”, “TON”, “BTC” (and “JET” for testnet). Defaults to all currencies.

        Returns:
            Invoice: Invoice object
        """
        method = "GET"
        url = f"{self.network}/api/createInvoice"

        if accepted_assets and type(accepted_assets) == list:
            accepted_assets = ",".join(map(str, accepted_assets))

        params = {
            "asset": asset,
            "amount": amount,
            "description": description,
            "hidden_message": hidden_message,
            "paid_btn_name": paid_btn_name,
            "paid_btn_url": paid_btn_url,
            "payload": payload,
            "allow_comments": allow_comments,
            "allow_anonymous": allow_anonymous,
            "expires_in": expires_in,
            "fiat": fiat,
            "currency_type": currency_type,
            "accepted_assets": accepted_assets,
        }

        for key, value in params.copy().items():
            if isinstance(value, bool):
                params[key] = str(value).lower()
            if value is None:
                del params[key]

        response = self._make_request(
            method=method, url=url, params=params, headers=self.__headers
        )
        return Invoice(**response["result"])

    def get_invoices(
        self,
        asset: Optional[Union[Any, str]] = None,
        invoice_ids: Optional[Union[List[int], int]] = None,
        status: Optional[Union[Any, str]] = None,
        offset: Optional[int] = None,
        count: Optional[int] = None,
    ) -> Optional[Union[Invoice, List[Invoice]]]:
        """
        Use this method to get invoices of your app.
        https://help.crypt.bot/crypto-pay-api#getInvoices

        Args:
            asset (Optional[Union[Assets, str]], optional): Cryptocurrency alphabetic code. Supported assets: “USDT”, “TON”, “BTC”, “ETH”, “LTC”, “BNB”, “TRX” and “USDC” (and “JET” for testnet). Defaults to all currencies.
            invoice_ids (Optional[Union[List[int], int]], optional): Invoice IDs separated by comma (list in python).
            status (Optional[Union[InvoiceStatus, str]], optional): Status of invoices to be returned. Available statuses: “active” and “paid”. Defaults to all statuses.
            offset (Optional[int], optional): Offset needed to return a specific subset of invoices. Default is 0.
            count (Optional[int], optional): Number of invoices to be returned. Values between 1-1000 are accepted. Default is 100.

        Returns:
            Optional[Union[Invoice, List[Invoice]]]: Invoice object or list of Invoices
        """
        method = "GET"
        url = f"{self.network}/api/getInvoices"

        if invoice_ids and type(invoice_ids) == list:
            invoice_ids = ",".join(map(str, invoice_ids))

        params = {
            "asset": asset,
            "invoice_ids": invoice_ids,
            "status": status,
            "offset": offset,
            "count": count,
        }

        for key, value in params.copy().items():
            if value is None:
                del params[key]

        response = self._make_request(
            method=method, url=url, params=params, headers=self.__headers
        )
        if len(response["result"]["items"]) > 0:
            if invoice_ids and isinstance(invoice_ids, int):
                return Invoice(**response["result"]["items"][0])
            return [Invoice(**invoice) for invoice in response["result"]["items"]]

    def delete_invoice(self, invoice_id: int) -> bool:
        """
        Use this method to delete invoices created by your app.
        http://help.crypt.bot/crypto-pay-api#34Hd

        Args:
            invoice_id (int): Invoice ID to be deleted.

        Returns:
            bool: Returns True on success.
        """
        return self._make_request(
            method="GET",
            url=f"{self.network}/api/deleteInvoice",
            params={"invoice_id": invoice_id},
            headers=self.__headers
        )["result"]
