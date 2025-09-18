import json
import os

from pydantic import BaseModel, ConfigDict

def _load_env(path: str = '.env'):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue
                k, v = line.split('=', 1)
                v = v.strip().strip('"').strip("'")
                os.environ.setdefault(k.strip(), v)

_load_env()

class Config(BaseModel):
    token: str = ''
    admins: list[int] = []
    ref_percent: float = 10
    fee: float = 5 # комиссия (наценка) %

    mnemonic: list[str] = []
    ton_api_key: str = ''
    hash_fragment: str = ''
    cookies: str = ''

    notify_new_user: bool = True
    notify_new_dep: bool = True
    notify_new_stars_deposit: bool = True

    support_username: str = ''
    channel_username: str = ''
    required_sub: bool = True

    ozon_card: str = "2202 ..."
    ozon_pin: str = '1234'
    ozon_cookies: str = ''

    yoomoney_token: str = ''

    crypto_bot_token: str = ''

    model_config: ConfigDict = ConfigDict(extra='ignore')

    max_stars: int = 100_000
    min_stars: int = 50

    course: dict = {
        0: [[min_stars, 1500], 1.5],
        1: [[1501, 3000], 1.5],
        2: [[3001, 5000], 1.5],
        3: [[5001, 15000], 1.5],
        4: [[15001, max_stars], 1.5],
    }

    def get_course(self, amount = 1):
        for i, data in self.course.items():
            if data[0][0] <= amount <= data[0][1]:
                return data[1]
        return None

    @classmethod
    def load(cls):
        if not os.path.exists('config.json'):
            return cls().save()
        with open('config.json') as file:
            return cls(**json.load(file))

    def save(self):
        with open('config.json', 'w') as file:
            json.dump(self.model_dump(), file, indent=4)
        return self

    def update_data(self):
        self.__dict__.update(self.load().__dict__)

    def toggle(self, param):
        setattr(self, param, not getattr(self, param))
        return self.save()

    def edit_cource(self, new_price_for_star: float, idx: int = None, price: float = None):
        for i, data in self.course.items():
            if idx == i or (price is not None and data[0][0] <= price <= data[0][1]):
                self.course[i][1] = new_price_for_star
                return self.save()

    @property
    def lava_api_key(self) -> str:
        return os.getenv('LAVA_API_KEY', '')

    @property
    def lava_shop_id(self) -> str:
        return os.getenv('LAVA_SHOP_ID', '')

    @property
    def lava_secret(self) -> str:
        return os.getenv('LAVA_SECRET', '')

    @property
    def lava_base_url(self) -> str:
        return os.getenv('LAVA_BASE_URL', 'https://api.lava.ru')

    @property
    def lava_success_url(self) -> str:
        return os.getenv('LAVA_SUCCESS_URL', '')

    @property
    def lava_fail_url(self) -> str:
        return os.getenv('LAVA_FAIL_URL', '')

    @property
    def lava_create_path(self) -> str:
        return os.getenv('LAVA_CREATE_PATH', '/invoices')

    @property
    def lava_status_path(self) -> str:
        return os.getenv('LAVA_STATUS_PATH', '/invoices/{id}')


cfg = Config.load()
cfg.save()
