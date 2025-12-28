# -*- coding: utf-8 -*-
from aiogram.types import message
from loguru import logger  # https://github.com/Delgan/loguru
from telethon import TelegramClient

from keyboards.keyboards import menu_launch_tracking_keyboard
from locales.locales import get_text
from system.dispatcher import api_id, api_hash


# === Подключение клиента Telethon ===
async def connect_client(session_name, user):
    """
    Подключение клиента Telethon. Возвращается client.connect()
    :param user: Пользователь из базы данных, для определения языка пользователя
    :param session_name: имя сессии Telethon
    :return: client - клиент Telethon
    """

    client = TelegramClient(session_name, api_id, api_hash, system_version="4.16.30-vxCUSTOM")

    await client.connect()

    # === Проверка авторизации ===
    if not await client.is_user_authorized():
        logger.error(f"⚠️ Сессия {session_name} недействительна — требуется повторный вход.")
        await message.answer(
            get_text(user.language, "account_missing_2"),
            reply_markup=menu_launch_tracking_keyboard()
        )
        return

    logger.info("✅ Сессия активна, подключение успешно!")

    return client
