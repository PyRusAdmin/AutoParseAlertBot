# -*- coding: utf-8 -*-
import asyncio

from aiogram import F
from aiogram.types import Message
from loguru import logger  # https://github.com/Delgan/loguru
from telethon.errors import FloodWaitError, AuthKeyUnregisteredError

from database.database import TelegramGroup, db
from system.dispatcher import router


@router.message(F.text == "Присвоить категорию")
async def checking_group_for_ai_db(message: Message):
    """
    Актуализация базы данных:
    обновление ID и типа групп/каналов.

    Последовательность действий:
     - Сканирует папку accounts/parsing для поиска доступных сессий;
     - Подключается к Telegram API для получения метаданных по username;
     - Определяет тип сущности (канал, супергруппа и т.д.);
     - Обновляет записи в базе через прямой UPDATE-запрос;
     - При FloodWaitError переключается на следующий аккаунт;
     - Отправляет прогресс и статистику в чат администратора.

     Особенности:
     - Доступ только для администраторов;
     - Автоматическое переключение между аккаунтами при FloodWait;
     - Используется режим WAL для избежания блокировок БД.

     :param message: (Message) Входящее сообщение от администратора.
     :return: None
     """
    await message.answer("✅ Начало актуализации...")

    try:
        # 3. Убедимся, что БД подключена
        if db.is_closed():
            db.connect()

        # 4. Получаем записи с username и group_type='group', которые ещё НЕ обновлены
        groups_to_update = list(TelegramGroup.select().where(
            (TelegramGroup.username.is_null(False)) &
            (TelegramGroup.category == '')
        ))

        total_count = len(groups_to_update)
        logger.info(f"Найдено {total_count} групп для обновления")

        # Отправляем начальное сообщение
        await message.answer(f"🔄 Начинаю актуализацию {total_count} групп...")

        processed = 0
        updated = 0
        errors = 0
        current_session_index = 0

        # 5. Основной цикл обработки групп
        while processed < total_count and current_session_index < len(available_sessions):

            try:
                await asyncio.sleep(1)

                # Обрабатываем группы с текущим аккаунтом
                for group in groups_to_update[processed:]:
                    try:
                        await asyncio.sleep(2)

                        # Обновляем запись через UPDATE запрос со всеми доступными данными
                        TelegramGroup.update(
                            id=entity.id,
                            group_hash=str(entity.id),
                            group_type=new_group_type,
                            username=actual_username,
                            description=description,
                            participants=participants_count,
                            name=entity.title  # Также обновляем название на актуальное
                        ).where(
                            TelegramGroup.group_hash == group.group_hash
                        ).execute()

                        processed += 1
                        updated += 1

                        logger.info(
                            f"[{processed}/{total_count}] Обновлено: {group.username} | "
                            f"ID: {entity.id} | Тип: {new_group_type} | Описание: {description} | Участники: {participants_count} | Аккаунт: {current_account}"
                        )

                        # Каждые 10 обновлений отправляем прогресс
                        if processed % 10 == 0:
                            await message.answer(
                                f"📊 Прогресс: {processed}/{total_count}\n"
                                f"✅ Обновлено: {updated}\n"
                                f"❌ Ошибок: {errors}\n"
                                f"📱 Аккаунт: {current_account}"
                            )

                        # Пауза для избежания бана от Telegram
                        await asyncio.sleep(5)

                    except Exception as e:
                        logger.exception(e)
            except Exception as e:
                logger.exception(e)
                await message.answer(f"❌ Ошибка аккаунта {current_account}: {e}")
                current_session_index += 1

        # Финальная статистика
        if processed >= total_count:
            await message.answer(
                f"✅ Актуализация завершена!\n\n"
                f"📊 Всего обработано: {processed}/{total_count}\n"
                f"✅ Успешно обновлено: {updated}\n"
                f"❌ Ошибок: {errors}\n"
                f"📱 Использовано аккаунтов: {current_session_index + 1}/{len(available_sessions)}"
            )
        else:
            await message.answer(
                f"⚠️ Актуализация остановлена.\n\n"
                f"📊 Обработано: {processed}/{total_count}\n"
                f"✅ Успешно обновлено: {updated}\n"
                f"❌ Ошибок: {errors}\n"
                f"📱 Все {len(available_sessions)} аккаунтов исчерпаны"
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
