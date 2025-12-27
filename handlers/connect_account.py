# -*- coding: utf-8 -*-
import os

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from database.database import User
from keyboards.keyboards import back_keyboard
from locales.locales import get_text
from system.dispatcher import router


@router.message(F.text == "Подключить аккаунт")
async def handle_connect_account(message: Message, state: FSMContext):
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
async def handle_account_file(message: Message, state: FSMContext):
    """
    Приём файла аккаунта и сохранение его в папку account.
    Если есть старые файлы .session или .session-journal — они удаляются.
    """
    user_tg = message.from_user
    document = message.document
    user_id = user_tg.id
    logger.info(f"User {user_id} отправил аккаунт {document.file_name}")

    # Проверяем расширение файла
    if not document.file_name.endswith(".session"):
        await message.answer("⚠️ Пожалуйста, отправьте корректный файл сессии (.session).")
        return

    # Папка пользователя
    user_folder = os.path.join(os.getcwd(), f"accounts/{user_id}")
    os.makedirs(user_folder, exist_ok=True)

    # Полный путь к новому файлу
    new_file_path = os.path.join(user_folder, document.file_name)

    # 🧹 Удаляем старые файлы .session и .session-journal
    deleted_files = []
    for file_name in os.listdir(user_folder):
        if file_name.endswith(".session") or file_name.endswith(".session-journal"):
            full_path = os.path.join(user_folder, file_name)
            try:
                os.remove(full_path)
                deleted_files.append(file_name)
            except Exception as e:
                logger.error(f"Ошибка при удалении {file_name}: {e}")

    if deleted_files:
        logger.info(f"Удалены старые файлы: {', '.join(deleted_files)}")

    # Скачиваем новый файл
    file = await message.bot.get_file(document.file_id)
    await message.bot.download_file(file.file_path, new_file_path)

    # Ответ пользователю
    msg = f"✅ Аккаунт {document.file_name} успешно загружен."
    if deleted_files:
        msg += f"\n♻️ Старые файлы ({', '.join(deleted_files)}) были удалены. Аккаунт обновлен"
    await message.answer(msg)


def register_connect_account_handler():
    """Регистрация обработчиков"""
    router.message.register(handle_connect_account)  # обработчик для кнопки "Подключить аккаунт"
    router.message.register(handle_account_file)  # обработчик приема аккаунта в формате .session
