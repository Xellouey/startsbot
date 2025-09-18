from aiogram.filters import BaseFilter

class Start(BaseFilter):
    def __init__(self, callback: str):
        self.cb = callback

    async def __call__(self, c):
        return c.data.startswith(self.cb)