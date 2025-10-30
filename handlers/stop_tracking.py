# -*- coding: utf-8 -*-
from aiogram import F
from aiogram.types import Message
from loguru import logger

from database.database import User
from keyboards.keyboards import (menu_launch_tracking_keyboard)
from parsing.parser import stop_tracking
from system.dispatcher import router


@router.message(F.text == "Остановить отслеживание")
async def handle_stop_tracking(message: Message):
    """Остановить отслеживание"""
    user_tg = message.from_user
    user = User.get(User.user_id == user_tg.id)

    logger.info(
        f"Пользователь {user_tg.id} {user_tg.username} {user_tg.first_name} {user_tg.last_name} нажал кнопку остановки отслеживания")

    await stop_tracking(user_id=user_tg.id, message=message, user=user)

    await message.answer(
        "Отслеживание отменено",
        reply_markup=menu_launch_tracking_keyboard()  # клавиатура выбора языка
    )


def register_stop_tracking_handler():
    """Регистрация обработчиков"""
    router.message.register(handle_stop_tracking)  # Регистрация обработчика
