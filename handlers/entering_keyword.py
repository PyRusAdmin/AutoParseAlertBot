# -*- coding: utf-8 -*-

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from database.database import User, create_keywords_model
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
        f"Пользователь {user_tg.id} {user_tg.username} {user_tg.first_name} {user_tg.last_name} перешел в меню Ввод ключевого слова")

    await message.answer(
        get_text(user.language, "enter_keyword"),
        reply_markup=back_keyboard()  # клавиатура назад
    )
    await state.set_state(MyStates.entering_keyword)


@router.message(MyStates.entering_keyword)
async def handle_keyword(message: Message, state: FSMContext):
    """Обработка введённого ключевого слова, словосочетания"""

    user_keyword = message.text.strip()
    user_tg = message.from_user
    logger.info(f"Пользователь ввёл ключевое слово: {user_keyword}")

    # Создаём модель с таблицей, уникальной для конкретного пользователя
    Keywords = create_keywords_model(user_id=user_tg.id)  # Создаём таблицу для групп / ключевых слов

    # Проверяем, существует ли таблица (если нет — создаём)
    if not Keywords.table_exists():
        Keywords.create_table()
        logger.info(f"Создана новая таблица для пользователя {user_tg.id}")

    # Добавляем запись в таблицу
    try:
        keywords = Keywords.create(user_keyword=user_keyword)
        await message.answer(f"✅ Слово / словосочетание {user_keyword} добавлено в отслеживание.")
        logger.info(f"Ключевое слово {user_keyword} добавлено пользователем {user_tg.id}")
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            await message.answer("⚠️ Такое слово / словосочетание уже есть в отслеживаемых.")
        else:
            await message.answer("⚠️ Ошибка при добавлении слова / словосочетания.")
        logger.error(f"Ошибка при добавлении ключевого слова: {e}")
    await state.clear()  # Очищаем состояние


def register_entering_keyword_handler():
    """Регистрация обработчиков"""
    router.message.register(entering_keyword)  # Регистрация обработчика
