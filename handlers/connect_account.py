# -*- coding: utf-8 -*-
import os

from aiogram import F
from aiogram.types import Message
from loguru import logger

from database.database import User
from keyboards.keyboards import (back_keyboard)
from locales.locales import get_text
from system.dispatcher import router


@router.message(F.text == "Подключить аккаунт")
async def handle_connect_account(message: Message):
    """Меню подключения аккаунта"""
    user_tg = message.from_user

    # Создаём пользователя с language = "unset", если его нет
    user, created = User.get_or_create(
        user_id=user_tg.id,
        defaults={
            "username": user_tg.username,
            "first_name": user_tg.first_name,
            "last_name": user_tg.last_name,
            "language": "unset"  # ← ключевое: "unset" = язык не выбран
        }
    )

    text = get_text(user.language, "connect_account")
    await message.answer(text, reply_markup=back_keyboard())


@router.message(F.document)
async def handle_account_file(message: Message):
    """Приём файла аккаунта и сохранение его в папку account"""
    user_tg = message.from_user
    document = message.document

    user_id = message.from_user.id
    logger.info(f"User {user_id} отправил аккаунт {document.file_name}")

    # Проверяем расширение файла
    if not document.file_name.endswith(".session"):
        await message.answer("⚠️ Пожалуйста, отправьте корректный файл сессии (.session).")
        return

    # Создаём папку, если её нет
    folder_path = os.path.join(os.getcwd(), f"accounts/{user_id}")
    os.makedirs(folder_path, exist_ok=True)

    # Путь сохранения
    file_path = os.path.join(folder_path, document.file_name)

    # Скачиваем файл
    file = await message.bot.get_file(document.file_id)
    await message.bot.download_file(file.file_path, file_path)

    await message.answer(f"✅ Файл {document.file_name} успешно загружен в папку account.")


def register_connect_account_handler():
    """Регистрация обработчиков"""
    router.message.register(handle_connect_account)  # обработчик для кнопки "Подключить аккаунт"
    router.message.register(handle_account_file)  # обработчик приема аккаунта в формате .session
