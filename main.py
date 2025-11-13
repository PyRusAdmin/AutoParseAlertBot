# -*- coding: utf-8 -*-
import asyncio
import logging
import sys

from loguru import logger

from ai.ai import get_groq_response
from handlers.connect_group import register_entering_group_handler
from handlers.entering_keyword import register_entering_keyword_handler
from handlers.get_dada import register_data_export_handlers
from handlers.handlers import register_greeting_handlers
from handlers.stop_tracking import register_stop_tracking_handler
from system.dispatcher import dp, bot

logger.add("logs/log.log", retention="1 days", enqueue=True)  # Логирование бота


async def main() -> None:
    """
    Функция запуска бота
    :return: None
    """
    user_input = "Привет"
    await get_groq_response(user_input)

    register_greeting_handlers()
    register_entering_keyword_handler()  # Регистрация обработчика для ввода и записи в БД ключевых слов
    register_entering_group_handler()  # Регистрация обработчика для ввода и записи в БД групп (техническая группа)
    register_data_export_handlers()  # Выдача пользователю введенных им данных

    register_stop_tracking_handler()  # Остановка отслеживания ключевых слов

    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
