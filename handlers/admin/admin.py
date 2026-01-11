# -*- coding: utf-8 -*-
import asyncio

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger  # https://github.com/Delgan/loguru
from telethon.errors import FloodWaitError
from telethon.sync import TelegramClient

from database.database import TelegramGroup, add_id_column, db
from keyboards.admin.keyboards import admin_keyboard
from system.dispatcher import api_id, api_hash
from system.dispatcher import router


@router.message(F.text == "Панель администратора")
async def admin_panel(message: Message, state: FSMContext):
    """
    Обработчик команды «Панель администратора».

    При вызове:
    - сбрасывает текущее состояние FSM;
    - отправляет приветственное сообщение администратору;
    - отображает клавиатуру с административными кнопками.

    Используется для:
    - предоставления доступа к административному интерфейсу;
    - запуска административных операций через клавиатурные кнопки.

    Особенности реализации:
    - Доступ к команде имеют только администраторы;
    - обработка исключений реализована в блоке try/except.

    :param message: (Message) Входящее сообщение с командой «Панель администратора».
    :param state: (FSMContext) Контекст машины состояний. Сбрасывается в начале выполнения.
    :return: None
    :raises:
        Exception: Может возникнуть при ошибках формирования клавиатуры (admin_keyboard()) или отправке сообщения через Telegram Bot API.
        Исключения перехватываются и логируются.
    """
    try:
        await state.clear()  # Сбрасываем текущее состояние FSM

        text = (
            "👋 <b>Добро пожаловать в панель администратора!</b>\n\n"
            "Вот что вы можете сделать:\n\n"
            "📁 <b>Получить лог-файл</b> — просмотреть журнал ошибок и событий бота за последнее время. Полезно для диагностики.\n\n"
            "🔄 <b>Актуализация базы данных</b> — обновить информацию о группах и каналах: проверить их текущий тип (группа/канал) и получить актуальные ID.\n\n"
        )
        await message.answer(
            text=text,
            parse_mode="HTML",
            reply_markup=admin_keyboard(),
        )
    except Exception as e:
        logger.exception(e)


@router.message(F.text == "Актуализация базы данных")
async def update_db(message: Message):
    """Актуализация базы данных: обновление ID и типа групп/каналов."""

    # 1. Выполняем миграцию (один раз за вызов)
    add_id_column()

    # 2. Подключаемся к Telegram
    client = TelegramClient('accounts/parsing/998771571378', api_id, api_hash)
    await client.connect()

    # 3. Небольшая пауза для стабильности
    await asyncio.sleep(1)

    try:
        # 3. Убедимся, что БД подключена
        if db.is_closed():
            db.connect()

        # 4. Получаем записи с username и group_type='group', которые ещё НЕ обновлены
        groups_to_update = TelegramGroup.select().where(
            (TelegramGroup.username.is_null(False)) &
            (TelegramGroup.group_type == 'group')
        )

        total_count = groups_to_update.count()
        logger.info(f"Найдено {total_count} групп для обновления")

        # Отправляем начальное сообщение
        await message.answer(f"🔄 Начинаю актуализацию {total_count} групп...")

        processed = 0
        updated = 0
        errors = 0

        for group in groups_to_update:
            try:
                # 5. Получаем сущность Telegram по username
                entity = await client.get_entity(group.username)

                # 6. Определяем тип сущности
                if entity.megagroup:
                    new_group_type = 'Группа (супергруппа)'
                elif entity.broadcast:
                    new_group_type = 'Канал'
                else:
                    new_group_type = 'Обычный чат (группа старого типа)'

                # 7. Обновляем запись через UPDATE запрос
                TelegramGroup.update(
                    id=entity.id,
                    group_type=new_group_type
                ).where(
                    TelegramGroup.group_hash == group.group_hash
                ).execute()

                processed += 1
                updated += 1

                logger.info(
                    f"[{processed}/{total_count}] Обновлено: {group.username} | ID: {entity.id} | Тип: {new_group_type}"
                )

                # Каждые 10 обновлений отправляем прогресс
                if processed % 10 == 0:
                    await message.answer(
                        f"📊 Прогресс: {processed}/{total_count}\n"
                        f"✅ Обновлено: {updated}\n"
                        f"❌ Ошибок: {errors}"
                    )

                # 8. Пауза для избежания бана от Telegram
                await asyncio.sleep(5)

            except FloodWaitError as e:
                wait_time = e.seconds
                processed += 1
                errors += 1

                logger.warning(
                    f"FloodWait для {group.username}: нужно подождать {wait_time} секунд "
                    f"({wait_time / 3600:.1f} часов). Останавливаем обработку."
                )

                # Отправляем итоговую статистику при FloodWait
                await message.answer(
                    f"⚠️ Telegram ограничил запросы.\n\n"
                    f"📊 Обработано: {processed}/{total_count}\n"
                    f"✅ Обновлено: {updated}\n"
                    f"❌ Ошибок: {errors}\n\n"
                    f"⏱ Необходимо подождать {wait_time / 3600:.1f} часов ({wait_time} сек)"
                )
                break  # Останавливаем обработку

            except Exception as e:
                processed += 1
                errors += 1
                logger.error(f"[{processed}/{total_count}] Ошибка при обработке {group.username}: {e}")

        # Финальная статистика (если не было FloodWait)
        else:
            await message.answer(
                f"✅ Актуализация завершена!\n\n"
                f"📊 Всего обработано: {processed}/{total_count}\n"
                f"✅ Успешно обновлено: {updated}\n"
                f"❌ Ошибок: {errors}"
            )

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        await message.answer(f"❌ Критическая ошибка: {e}")

    finally:
        if not db.is_closed():
            db.close()

        await client.disconnect()
        logger.info("Актуализация завершена.")


def register_handlers_admin_panel():
    """
    Регистрирует обработчик команды «Панель администратора» в маршрутизаторе.

    Добавляет в router обработчик для команды, активируемой по тексту «Панель администратора».
    Обеспечивает запуск функции admin_panel при получении соответствующего сообщения.

    Рекомендации по безопасности:
    - Доступ к команде имеют только администраторы;
    - обработка исключений реализована.

    :return: None
    """
    router.message.register(admin_panel)  # Админ панель
    router.message.register(update_db)  # Актуализация базы данных (c пометкой Группа или Канал)
