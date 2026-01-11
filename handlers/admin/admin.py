# -*- coding: utf-8 -*-
import time

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger  # https://github.com/Delgan/loguru
from telethon.sync import TelegramClient

from database.database import TelegramGroup
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
    - Команда доступна всем пользователям — в продакшен‑среде необходимо ограничить доступ только для авторизованных администраторов;
    - обработка исключений не реализована: возможные ошибки (например, при формировании клавиатуры) не перехватываются и могут привести к аварийному завершению обработчика.

    :param message: (Message) Входящее сообщение с командой «Панель администратора».
    :param state: (FSMContext) Контекст машины состояний. Сбрасывается в начале выполнения.
    :return: None
    :raises:
        Exception: Может возникнуть при:
        - ошибках формирования клавиатуры (admin_keyboard());
        - проблемах при отправке сообщения через Telegram Bot API.
        В текущей реализации исключения не обрабатываются.
    """
    try:
        await state.clear()  # Сбрасываем текущее состояние FSM

        text = (
            "Рад видеть тебя снова, администратор!\n"
            "На кнопке 'Получить лог файл' ты можешь получить лог файл с ошибками бота.\n"
            "На кнопке 'Актуализация базы данных' ты можешь актуализировать базу данных (проверить на сущность Группа или Канал)."
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
    """Актуализация базы данных на группу или канал"""
    # 1. Считываем с базы данных данные
    # Получаем все записи
    all_groups = TelegramGroup.select()
    # Создаем список для результатов
    result_list = []
    # Перебираем все записи
    for group in all_groups:
        # Результат делаем в словарь
        result = [group.name, group.username]
        # Выводим полученные данные
        logger.info(result)
        result_list.append(result)
    # Выводим полученные данные
    logger.info(result_list)

    # Подключаемся к аккаунту телеграмм (Путь к аккаунту для перебора accounts/parsing/998771571378)
    client = TelegramClient('accounts/parsing/998771571378', api_id, api_hash)
    await client.connect()

    for group in result_list:
        logger.info(f"Проверяемый username: {group[1]}")

        entity = await client.get_entity(group[1])

        # Проверяем тип сущности
        if entity.megagroup:
            print(f"Ссылка: {group[1]}")
            print("Тип: Группа (супергруппа)")
            print(f"ID: {entity.id}")
        elif entity.broadcast:
            print(f"Ссылка: {group[1]}")
            print("Тип: Канал")
            print(f"ID: {entity.id}")
        else:
            print(f"Ссылка: {group[1]}")
            print("Тип: Обычный чат (группа старого типа)")
            print(f"ID: {entity.id}")

        time.sleep(3)


def register_handlers_admin_panel():
    """
    Регистрирует обработчик команды «Панель администратора» в маршрутизаторе.

    Добавляет в router обработчик для команды, активируемой по тексту «Панель администратора».
    Обеспечивает запуск функции admin_panel при получении соответствующего сообщения.

    Рекомендации по безопасности:
    - В текущей реализации команда доступна любому пользователю;
    - в продакшене необходимо добавить проверку прав доступа (например, по списку разрешённых user_id);
    - рекомендуется реализовать обработку возможных исключений.

    :return: None
    """
    router.message.register(admin_panel)  # Админ панель
    router.message.register(update_db)  # Актуализация базы данных (c пометкой Группа или Канал)
