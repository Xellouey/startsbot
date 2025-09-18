from aiogram import Router
from aiogram.types import Update
import logging

logger = logging.getLogger(f"main.{__name__}")

router = Router()

@router.error()
async def error_handler(ex):
    ex = ex.exception
    logger.error(f"Ошибка при выполнении хендлера тг-бота ({type(ex).__name__}): {str(ex)}")
    logger.debug("TRACEBACK", exc_info=True)