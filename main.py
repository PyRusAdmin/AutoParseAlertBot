# -*- coding: utf-8 -*-
import asyncio
import logging
import sys

from loguru import logger

from ai.ai import get_groq_response, search_groups_in_telegram
from handlers.connect_group import register_entering_group_handler
from handlers.entering_keyword import register_entering_keyword_handler
from handlers.get_dada import register_data_export_handlers
from handlers.handlers import register_greeting_handlers
from handlers.pars_ai import register_handlers_pars_ai
from handlers.stop_tracking import register_stop_tracking_handler
from system.dispatcher import dp, bot

logger.add("logs/log.log", retention="1 days", enqueue=True)  # Логирование бота

# Разбиваем ответ на строки и очищаем от номеров, точек, тире, звёздочек и прочего
def clean_group_name(name):
    # Удаляем начало строки: цифры, точки, тире, звёздочки, скобки, пробелы
    import re
    # Убираем всё, что до первого буквенного/кириллического символа
    cleaned = re.sub(r'^[\d\.\-\*\s\)\(\[\]]+', '', name).strip()
    return cleaned

async def main() -> None:
    """
    Функция запуска бота
    :return: None
    """
    user_input = "Парсинг бот"
    answer = await get_groq_response(user_input)
    logger.info(f"Ответ от Groq: {answer}")

    # Разбиваем ответ на строки
    group_names = [clean_group_name(line) for line in answer.splitlines() if line.strip()]
    # Убираем пустые и слишком короткие
    group_names = [name for name in group_names if len(name) > 2]
    logger.info(f"Получено {len(group_names)} названий: {group_names}")

    all_results = []
    for group_name in group_names:
        # Ищем в Telegram
        results = await search_groups_in_telegram([group_name])  # ✅ Передаём список
        logger.info(f"Найдено {len(results)} групп для '{group_name}':")
        all_results.extend(results)

        # Выводим результаты
        if results:
            logger.info("\n🔍 Найденные группы:")
            for group in results:
                logger.info(f"✅ {group['name']} | {group['username']} | {group['link']} | Участников: {group['participants']}")
        else:
            logger.info("❌ Ничего не найдено.")


    register_greeting_handlers()
    register_entering_keyword_handler()  # Регистрация обработчика для ввода и записи в БД ключевых слов
    register_entering_group_handler()  # Регистрация обработчика для ввода и записи в БД групп (техническая группа)
    register_data_export_handlers()  # Выдача пользователю введенных им данных

    register_stop_tracking_handler()  # Остановка отслеживания ключевых слов

    register_handlers_pars_ai()

    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
