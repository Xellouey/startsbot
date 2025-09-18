import logging
import logging.config
import logging.handlers
import re

from colorama import Fore, Style, Back

LOG_COLORS = {
    logging.DEBUG: Fore.BLACK + Style.BRIGHT,
    logging.INFO: Fore.GREEN,
    logging.WARNING: Fore.YELLOW,
    logging.ERROR: Fore.RED,
    logging.CRITICAL: Fore.RED
}

CLI_LOG_FORMAT = f"{Fore.BLACK + Style.BRIGHT}[%(asctime)s]{Style.RESET_ALL}" \
                 f"{Fore.CYAN}>{Style.RESET_ALL} $RESET%(levelname).1s: %(message)s{Style.RESET_ALL}"
CLI_TIME_FORMAT = "%d-%m %H:%M:%S"

FILE_LOG_FORMAT = "[%(asctime)s]> %(levelname).1s: %(message)s"
FILE_TIME_FORMAT = "%d.%m.%y %H:%M:%S"
CLEAR_RE = re.compile(r"(\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]))|(\n)|(\r)")

colors = {
    "$YELLOW": Fore.YELLOW,
    "$CYAN": Fore.CYAN,
    "$MAGENTA": Fore.MAGENTA,
    "$BLUE": Fore.BLUE,
    "$GREEN": Fore.GREEN,
    "$BLACK": Fore.BLACK,
    "$WHITE": Fore.WHITE,

    "$B_YELLOW": Back.YELLOW,
    "$B_CYAN": Back.CYAN,
    "$B_MAGENTA": Back.MAGENTA,
    "$B_BLUE": Back.BLUE,
    "$B_GREEN": Back.GREEN,
    "$B_BLACK": Back.BLACK,
    "$B_WHITE": Back.WHITE,
}


def add_colors(text: str) -> str:
    for c in colors:
        if c in text:
            text = text.replace(c, colors[c])
    return text


def clear_tags(text: str):
    for c in colors:
        if c in text:
            text = text.replace(c, '')
    return text


class CLILoggerFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg = record.getMessage()
        msg = add_colors(msg)
        msg = msg.replace("$RESET", LOG_COLORS[record.levelno])
        record.msg = msg

        log_format = CLI_LOG_FORMAT.replace("$RESET", Style.RESET_ALL + LOG_COLORS[record.levelno])
        formatter = logging.Formatter(log_format, CLI_TIME_FORMAT)
        return formatter.format(record)


class FileLoggerFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg = record.getMessage()
        msg = CLEAR_RE.sub("", msg)
        msg = clear_tags(msg)
        record.msg = msg

        formatter = logging.Formatter(FILE_LOG_FORMAT, FILE_TIME_FORMAT)
        return formatter.format(record)


class CustomLogger(logging.Logger):
    def traceback(self, message: str = "TRACEBACK", **kwargs):
        self.debug(message, exc_info=True, **kwargs)


logging.setLoggerClass(CustomLogger)


LOGGER_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "cli_formatter": {
            "()": CLILoggerFormatter,
        },
        "file_formatter": {
            "()": FileLoggerFormatter,
        },
    },
    "handlers": {
        "cli_handler": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "cli_formatter",
        },
        "file_handler": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "file_formatter",
            "filename": "logs/log.log",
            "maxBytes": 30 * 1024 * 1024,
            "backupCount": 25,
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "main": {
            "handlers": ["cli_handler", "file_handler"],
            "level": "DEBUG",
        }
    }
}

logging.config.dictConfig(LOGGER_CONFIG)