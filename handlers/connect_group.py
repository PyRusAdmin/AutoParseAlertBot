# -*- coding: utf-8 -*-
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from database.database import User, create_group_model
from keyboards.keyboards import (back_keyboard)
from locales.locales import get_text
from states.states import MyStates
from system.dispatcher import router


@router.message(F.text == "Подключить группу для сообщений")
async def handle_connect_message_group(message: Message, state: FSMContext):
    """Ввод username группы для сообщений"""
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
    """Обработка введённого ключевого слова, словосочетания"""

    group_username = message.text.strip()
    user_tg = message.from_user
    logger.info(f"Пользователь ввёл ссылку: {group_username}")

    # Создаём модель с таблицей, уникальной для конкретного пользователя
    GroupModel = create_group_model(user_id=user_tg.id)  # Создаём таблицу для групп / ключевых слов

    # Проверяем, существует ли таблица (если нет — создаём)
    if not GroupModel.table_exists():
        GroupModel.create_table()
        logger.info(f"Создана новая таблица для пользователя {user_tg.id}")

    # Добавляем запись в таблицу
    try:
        # group_record = GroupModel.create(user_group=group_username)
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
    """Регистрация обработчиков"""
    router.message.register(handle_connect_message_group)  # Регистрация обработчика
