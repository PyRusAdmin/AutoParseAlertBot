# -*- coding: utf-8 -*-
import asyncio
from concurrent.futures import ProcessPoolExecutor

from aiogram import F
from loguru import logger

from ai.ai import ai_llama
from database.database import TelegramGroup
from system.dispatcher import router


async def get_groups_without_language() -> list[dict]:
    """
    Получить список групп без языка из БД.
    Возвращает список словарей для передачи в процессы.
    """
    try:
        # Получаем группы где language пустой или NULL
        groups = TelegramGroup.select().where(
            (TelegramGroup.language.is_null()) |
            (TelegramGroup.language == '')
        )

        # Преобразуем в список словарей
        groups_data = []
        for group in groups:
            groups_data.append({
                "group_hash": group.group_hash,
                "name": group.name,
                "username": group.username,
                "description": group.description,
            })

        logger.info(f"📊 Найдено {len(groups_data)} групп без языка")
        return groups_data

    except Exception as e:
        logger.error(f"❌ Ошибка получения групп из БД: {e}")
        return []


async def update_group_language(group_hash: str, language: str) -> bool:
    """
    Обновить язык группы в БД.
    """
    try:
        logger.debug(f"🔄 Попытка обновить {group_hash} -> {language}")  # ← Добавлено

        query = TelegramGroup.update(language=language).where(
            TelegramGroup.group_hash == group_hash
        )
        rows_updated = query.execute()

        if rows_updated > 0:
            logger.debug(f"✅ Обновлён язык для {group_hash}: {language}")
            return True
        else:
            logger.warning(f"⚠️ Группа {group_hash} не найдена для обновления")
            return False

    except Exception as e:
        logger.error(f"❌ Ошибка обновления языка для {group_hash}: {e}")
        return False


@router.message(F.text == "Присвоить язык")
async def language_detection(message):
    """
    Присвоение языка на основе названия, описания и username группы.
    Использует multiprocessing для параллельной обработки.
    """

    # Получаем группы из БД
    groups_to_process = await get_groups_without_language()

    if not groups_to_process:
        await message.answer("❌ Нет групп для обработки (все уже имеют язык)")
        return

    total = len(groups_to_process)
    await message.answer(
        f"🚀 Запуск обработки {total} групп в 10 параллельных процессах..."
    )

    # Запускаем параллельную обработку через multiprocessing
    loop = asyncio.get_event_loop()

    try:
        with ProcessPoolExecutor(max_workers=10) as executor:
            # Отправляем все задачи в пул процессов
            futures = [
                loop.run_in_executor(executor, ai_llama, group_data)
                for group_data in groups_to_process
            ]

            # Ждём завершения всех задач
            results = await asyncio.gather(*futures, return_exceptions=True)

    except Exception as e:
        logger.error(f"❌ Критическая ошибка при обработке: {e}")
        await message.answer(f"❌ Ошибка обработки: {e}")
        return

    # Обрабатываем результаты и обновляем БД
    successful = 0
    failed = 0
    updated = 0

    for result in results:
        if isinstance(result, Exception):
            logger.error(f"❌ Исключение в процессе: {result}")
            failed += 1
            continue

        if result.get("success") and result.get("language"):
            successful += 1

            # Обновляем язык в БД
            if await update_group_language(
                    result["group_hash"],
                    result["language"]
            ):
                updated += 1
                logger.info(
                    f"✅ '{result['name']}': {result['language']}"
                )
        else:
            failed += 1
            logger.error(
                f"❌ Ошибка для '{result.get('name')}': "
                f"{result.get('error', 'Unknown')}"
            )

    # Итоговое сообщение
    await message.answer(
        f"✅ Обработка завершена!\n\n"
        f"📊 Статистика:\n"
        f"• Всего обработано: {total}\n"
        f"• Успешно определён язык: {successful}\n"
        f"• Обновлено в БД: {updated}\n"
        f"• Ошибок: {failed}"
    )

    logger.info(
        f"\n{'=' * 70}\n"
        f"Все процессы завершены\n"
        f"Успешно: {successful} | Ошибок: {failed} | Обновлено: {updated}\n"
        f"{'=' * 70}\n"
    )


def register_handlers_languages():
    router.message.register(language_detection, F.text == "Присвоить язык")
