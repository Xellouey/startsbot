from utils.database import db_users
import logging
from colorama import Style, Fore

logger = logging.getLogger(f"main.{__name__}")

async def display_bot_statistics():
    users = db_users.get_all_users()
    total_users = len(users)
    active_users = sum(1 for user in users if user.is_active)
    total_balance = sum(user.balance for user in users)

    table_rows = [
        f"{Style.RESET_ALL}| {Fore.CYAN}Всего пользователей{Style.RESET_ALL} -> {Fore.YELLOW}{total_users}{Style.RESET_ALL}",
        f"| {Fore.CYAN}Активные{Style.RESET_ALL} -> {Fore.YELLOW}{active_users}{Style.RESET_ALL}",
        f"| {Fore.CYAN}Суммарный баланс{Style.RESET_ALL} -> {Fore.YELLOW}{total_balance}{Style.RESET_ALL}"
    ]

    table = "\n".join(table_rows)

    logger.info("\n" + table)