# -*- coding: utf-8 -*-
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger  # https://github.com/Delgan/loguru

from database.database import User, create_group_model
from keyboards.keyboards import (back_keyboard)
from locales.locales import get_text
from states.states import MyStates
from system.dispatcher import router


@router.message(F.text == "Подключить группу для сообщений")
async def handle_connect_message_group(message: Message, state: FSMContext):
    """
    Обработчик команды "Подключить группу для сообщений".

    Очищает текущее состояние FSM, получает данные пользователя из базы,
    логирует переход в меню и отправляет приглашение ввести username
    группы или канала, куда бот будет пересылать сообщения с ключевыми словами.

    Переводит пользователя в состояние ожидания ввода (MyStates.entering_group).

    Args:
        message (Message): Объект входящего сообщения от пользователя.
        state (FSMContext): Контекст машины состояний, используется для сброса и установки состояния.

    Returns:
        None
    """
    await state.clear()  # Завершаем текущее состояние машины состояния
    user_tg = message.from_user
    user = User.get(User.user_id == user_tg.id)

    logger.info(
        f"Пользователь {user_tg.id} {user_tg.username} {user_tg.first_name} {user_tg.last_name} перешел в меню Подключить группу для сообщений")

    await message.answer(
        get_text(user.language, "enter_group"),
        reply_markup=back_keyboard()  # клавиатура назад
    )
    await state.set_state(MyStates.entering_group)


@router.message(MyStates.entering_group)
async def handle_group_username_submission(message: Message, state: FSMContext):
    """
    Обработчик ввода username технической группы пользователем.

    Получает username из текста сообщения, создаёт или получает модель базы данных
    для хранения технической группы пользователя, создаёт таблицу при необходимости,
    и сохраняет введённый username. Уведомляет пользователя об успешном добавлении
    или ошибке (например, дубликат).

    Args:
        message (Message): Объект входящего сообщения с username группы.
        state (FSMContext): Контекст машины состояний, используется для сброса состояния после обработки.

    Returns:
        None

    Raises:
        Exception: При ошибке добавления в БД (например, нарушение уникальности).
            Обрабатывается локально с отправкой пользователю соответствующего сообщения.

    Notes:
        - Используется динамическая модель `create_group_model` для изоляции данных пользователей.
        - После успешной или неуспешной обработки состояние FSM очищается.
    """

    group_username = message.text.strip()
    user_tg = message.from_user
    logger.info(f"Пользователь ввёл ссылку: {group_username}")

    # Создаём модель с таблицей, уникальной для конкретного пользователя
    GroupModel = create_group_model(user_id=user_tg.id)  # Создаём таблицу для групп / ключевых слов
    GroupModel.create_table(safe=True)
    logger.info(f"Создана новая таблица для пользователя {user_tg.id}")

    # Проверяем, существует ли таблица (если нет — создаём)
    # if not GroupModel.table_exists():
    #     GroupModel.create_table()
    #     logger.info(f"Создана новая таблица для пользователя {user_tg.id}")

    # Добавляем запись в таблицу
    try:
        # group_record = GroupModel.create(user_group=group_username)

        # Удаляем старую запись, если есть
        GroupModel.delete().execute()
        # Вставляем новую
        GroupModel.create(user_group=group_username)

        await message.answer(f"✅ Группа {group_username} добавлена для отправки сообщений.")
        logger.info(f"username {group_username} добавлено пользователем {user_tg.id}")
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            await message.answer("⚠️ Эта группа уже добавлена.")
        else:
            await message.answer("⚠️ Ошибка при добавлении группы.")
        logger.error(f"Ошибка при добавлении ключевого слова: {e}")
    await state.clear()  # Очищаем состояние


def register_entering_group_handler():
    """
    Регистрирует обработчики для подключения технической группы.

    Добавляет в маршрутизатор (router) два обработчика:
        1. handle_connect_message_group — реагирует на нажатие кнопки "Подключить группу для сообщений".
        2. handle_group_username_submission — обрабатывает ввод username группы в состоянии MyStates.entering_group.

    Эти обработчики позволяют пользователю указать чат, куда бот будет пересылать
    найденные сообщения, содержащие ключевые слова.

    Returns:
        None
    """
    router.message.register(handle_connect_message_group)  # Регистрация обработчика
    router.message.register(handle_group_username_submission)  # Регистрация обработчика ввода username
