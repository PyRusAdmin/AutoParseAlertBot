# -*- coding: utf-8 -*-
import os

from loguru import logger  # https://github.com/Delgan/loguru

from keyboards.keyboards import menu_launch_tracking_keyboard
from locales.locales import get_text


async def find_session_file(session_dir, user, message):
    """
    Поиск .session файла в указанной директории.
    Ожидается, что имя файла соответствует шаблону: {user_id}.session
    :param session_dir: (str) Путь к папке с сессией (например, accounts/123456/)
    :param user: (User) Модель пользователя
    :param message: (aiogram.types.Message) Для отправки ответа
    :return: Полный путь к .session файлу или None
    """
    session_path = None

    # Ищем первый .session файл
    for file in os.listdir(session_dir):
        if file.endswith(".session"):
            session_path = os.path.join(session_dir, file)
            break

    if not session_path:
        logger.error(f"❌ Не найден файл .session в {session_dir}")
        await message.answer(
            get_text(user.language, "account_missing"),
            reply_markup=menu_launch_tracking_keyboard()  # клавиатура выбора языка
        )
        return

    logger.info(f"✅ Найден файл сессии: {session_path}")
    return session_path
