# -*- coding: utf-8 -*-
import os
import shutil
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
    """
    Приём файла аккаунта и сохранение его в папку account.

    Если файл уже есть — старый перемещается в общую папку 'accounts/old'.
    """
    user_tg = message.from_user
    document = message.document

    user_id = message.from_user.id
    logger.info(f"User {user_id} отправил аккаунт {document.file_name}")

    # Проверяем расширение файла
    if not document.file_name.endswith(".session"):
        await message.answer("⚠️ Пожалуйста, отправьте корректный файл сессии (.session).")
        return

    # Основные пути
    user_folder = os.path.join(os.getcwd(), f"accounts/{user_id}")
    old_folder = os.path.join(os.getcwd(), "accounts/old")

    # Создаём папки при необходимости
    os.makedirs(user_folder, exist_ok=True)
    os.makedirs(old_folder, exist_ok=True)

    new_file_path = os.path.join(user_folder, document.file_name)
    old_file_path = os.path.join(old_folder, f"{user_id}_{document.file_name}")

    # Проверяем, есть ли уже старый аккаунт
    if os.path.exists(new_file_path):
        # Перемещаем старый в общую папку с новым именем (с user_id)
        shutil.move(new_file_path, old_file_path)
        logger.info(f"Старый аккаунт {document.file_name} перемещён в {old_folder}")

    # Скачиваем новый файл
    file = await message.bot.get_file(document.file_id)
    await message.bot.download_file(file.file_path, new_file_path)

    await message.answer(
        f"✅ Новый аккаунт {document.file_name} успешно загружен.\n"
        f"📦 Старый перемещён в общую папку 'accounts/old'."
    )


def register_connect_account_handler():
    """Регистрация обработчиков"""
    router.message.register(handle_connect_account)  # обработчик для кнопки "Подключить аккаунт"
    router.message.register(handle_account_file)  # обработчик приема аккаунта в формате .session
