import json
import os
import re
from datetime import timedelta, datetime

import pytz

TIMEZONE = "Europe/Moscow"

def create_dirs():
    for d in [
        "logs", 'storage'
    ]:
        if not os.path.exists(d):
            os.makedirs(d)

def time_to_str(secs: int):
    td = timedelta(seconds=secs)

    days, seconds = td.days, td.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = secs % 60

    parts = []
    if days > 0:
        parts.append(f"{days} дн.")
    if hours > 0:
        parts.append(f"{hours} ч.")
    if minutes > 0:
        parts.append(f"{minutes} мин.")
    if seconds > 0:
        parts.append(f"{seconds} сек.")

    return " ".join(parts)


class ImagesLoader:
    @classmethod
    def load_banner(cls, path_banner=None, banner_name: str = 'banner2') -> tuple[bytes, str] | None:
        folder = 'storage/media'
        for file in os.listdir(folder):
            if file.startswith(f"{banner_name}."):
                path_banner = folder + f"/{file}"
        if not path_banner:
            return None
        with open(path_banner, 'rb') as file:
            return file.read(), path_banner.split(".")[-1]

def get_date(full: bool = True) -> str:
    format_ = "%d.%m.%Y %H:%M:%S" if full else "%d.%m.%Y"
    return datetime.now(pytz.timezone(TIMEZONE)).strftime(format_)

def is_on(val, true='🟢', false='🔴'):
    return true if val else false


def validate_cookie_string(cookie_string):
    pattern = re.compile(
        r'stel_token=[^;]+;'
        r'stel_dt=[^;]+;'
        r'stel_ssid=[^;]+;'
        r'stel_ton_token=[^;]+'
    )

    if pattern.fullmatch(cookie_string):
        return True
    else:
        return False

def load_cookies(s):
    try:
        _json = json.loads(s)
        return '; '.join([f"{k['name']}={k['value']}" for k in _json])
    except json.JSONDecodeError:
        if not validate_cookie_string(s):
            return -1
        return s