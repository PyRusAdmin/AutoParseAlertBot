# -*- coding: utf-8 -*-
import asyncio

from aiogram import F
from aiogram.types import Message
from loguru import logger  # https://github.com/Delgan/loguru

from ai.ai import category_assignment
from database.database import TelegramGroup, db
from system.dispatcher import router


@router.message(F.text == "Присвоить категорию")
async def checking_group_for_ai_db(message: Message):
    """
    Присваивает категории группам/каналам с помощью ИИ (Groq + Llama).

    Последовательность:
    - Находит все записи с пустой категорией;
    - Для каждой собирает контекст: название, описание, username;
    - Отправляет в ИИ;
    - Сохраняет полученную категорию.

    Особенности:
    - Обновляется ТОЛЬКО поле `category`;
    - Ошибки логируются, обработка продолжается;
    - Каждые 20 обновлений — прогресс в чат.

     :param message: (Message) Входящее сообщение от администратора.
     :return: None
     """
    await message.answer("🧠 Запуск присвоения категорий с помощью ИИ...")

    try:
        # Убедимся, что БД подключена
        if db.is_closed():
            db.connect()

        # Получаем группы без категории
        groups_to_update = list(TelegramGroup.select().where(
            (TelegramGroup.username.is_null(False)) &
            (TelegramGroup.category == '')
        ))

        total_count = len(groups_to_update)
        logger.info(f"Найдено {total_count} групп без категории")

        # Отправляем начальное сообщение
        await message.answer(f"🔄 Будет обработано: {total_count} групп")

        processed = 0
        updated = 0
        errors = 0

        for group in groups_to_update:
            try:
                await asyncio.sleep(1)

                # Собираем контекст для ИИ
                context = f"""
Название: {group.name or 'Без названия'}
Описание: {group.description or 'Без описания'}
Username: {group.username or 'Неизвестен'}
Тип: {group.group_type or 'Неизвестен'}
                """.strip()

                # Получаем категорию от ИИ
                category = await category_assignment(context)
                category = category.strip().strip('".')  # чистим кавычки и лишние символы

                # Обновляем ТОЛЬКО категорию
                TelegramGroup.update(
                    category=category
                ).where(TelegramGroup.telegram_id == group.telegram_id).execute()

                updated += 1
                logger.info(f"[{processed + 1}/{total_count}] Категория для {group.username}: {category}")

                # Отправляем прогресс каждые 20
                if (processed + 1) % 20 == 0:
                    await message.answer(
                        f"📊 Прогресс: {processed + 1}/{total_count}\n"
                        f"✅ Успешно: {updated}\n"
                        f"❌ Ошибок: {errors}"
                    )

                processed += 1
                await asyncio.sleep(1)  # уважаем API Groq

            except Exception as e:
                errors += 1
                logger.exception(f"Ошибка при обработке {group.username}: {e}")
                continue

        # Финальное сообщение
        await message.answer(
            f"✅ Присвоение категорий завершено!\n\n"
            f"📊 Всего: {processed}/{total_count}\n"
            f"✅ Успешно: {updated}\n"
            f"❌ Ошибок: {errors}"
        )

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        await message.answer(f"❌ Критическая ошибка: {e}")

    finally:
        if not db.is_closed():
            db.close()

        logger.info("Актуализация завершена.")


def register_handlers_checking_group_for_ai():
    """Регистрирует обработчики для проверки группы на наличие ключевых слов."""
    router.message.register(checking_group_for_ai_db, F.text == "Присвоить категорию")
