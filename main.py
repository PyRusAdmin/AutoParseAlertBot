# -*- coding: utf-8 -*-
import asyncio
import logging
import sys

from loguru import logger

from handlers.entering_keyword import register_entering_keyword_handler
from handlers.handlers import register_greeting_handlers
from system.dispatcher import dp, bot

logger.add("logs/log.log", retention="1 days", enqueue=True)  # Логирование бота


async def main() -> None:
    """
    Функция запуска бота
    :return: None
    """
    register_greeting_handlers()

    register_entering_keyword_handler()  # Регистрация обработчика для ввода и записи в БД ключевых слов

    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
