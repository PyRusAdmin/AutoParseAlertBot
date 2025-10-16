# -*- coding: utf-8 -*-

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from database.database import User, create_groups_model
from keyboards.keyboards import (back_keyboard)
from locales.locales import get_text
from states.states import MyStates
from system.dispatcher import router


@router.message(F.text == "Ввод ключевого слова")
async def entering_keyword(message: Message, state: FSMContext):
    """Ввод ключевого слова"""
    user_tg = message.from_user
    user = User.get(User.user_id == user_tg.id)

    logger.info(
        f"Пользователь {user_tg.id} {user_tg.username} {user_tg.first_name} {user_tg.last_name} перешел в меню 🔁 Обновить список")

    await message.answer(
        get_text(user.language, "update_list"),
        reply_markup=back_keyboard()  # клавиатура назад
    )
    await state.set_state(MyStates.waiting_username_group)


@router.message(MyStates.waiting_username_group)
async def handle_username_group(message: Message, state: FSMContext):
    """Обработка введённого имени группы в формате @username"""

    # username_group = message.text
    # user_tg = message.from_user
    username_group = message.text.strip()
    user_tg = message.from_user
    logger.info(f"Пользователь ввёл имя группы: {username_group}")

    # Создаём модель с таблицей, уникальной для конкретного пользователя
    Groups = create_groups_model(user_id=user_tg.id)  # Создаём таблицу для групп

    # Проверяем, существует ли таблица (если нет — создаём)
    if not Groups.table_exists():
        Groups.create_table()
        logger.info(f"Создана новая таблица для пользователя {user_tg.id}")

    # Добавляем запись в таблицу
    try:
        group = Groups.create(username_chat_channel=username_group)
        await message.answer(f"✅ Группа {username_group} добавлена в отслеживание.")
        logger.info(f"Группа {username_group} добавлена пользователем {user_tg.id}")
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            await message.answer("⚠️ Такая группа уже добавлена.")
        else:
            await message.answer("⚠️ Ошибка при добавлении группы.")
        logger.error(f"Ошибка при добавлении группы: {e}")


def register_entering_keyword_handler():
    """Регистрация обработчиков"""
    router.message.register(entering_keyword)  # Регистрация обработчика
