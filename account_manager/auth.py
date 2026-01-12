# -*- coding: utf-8 -*-
from loguru import logger  # https://github.com/Delgan/loguru
from telethon import TelegramClient
import asyncio
from keyboards.keyboards import menu_launch_tracking_keyboard
from locales.locales import get_text
from system.dispatcher import api_id, api_hash
import os


# === Подключение клиента Telethon ===
async def connect_client(session_name, user, message):
    """
    Подключение клиента Telethon и проверка сессий. Возвращается client.connect()
    :param user: Пользователь из базы данных, для определения языка пользователя
    :param session_name: имя сессии Telethon
    :param message: сообщение от пользователя
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

    me = await client.get_me()
    phone = me.phone or ""
    logger.info(f"🧾 Аккаунт: | ID: {me.id} | Phone: {phone}")

    logger.info("✅ Сессия активна, подключение успешно!")

    return client


# === Подключение клиента Telethon ===
async def connect_client_test(available_sessions):
    """
    Подключение клиента Telethon и проверка сессий. Возвращается client.connect()
    :param available_sessions: список доступных сессий Telethon
    :return: client - клиент Telethon
    """
    logger.info(f"🧾 Проверка сессий... {available_sessions}")

    for session_name in available_sessions:

        client = TelegramClient(f"accounts/parsing/{session_name}", api_id, api_hash, system_version="4.16.30-vxCUSTOM")

        await client.connect()

        # === Проверка авторизации ===
        if not await client.is_user_authorized():
            logger.error(f"⚠️ Сессия {session_name} недействительна — требуется повторный вход.")
            await client.disconnect()
            await asyncio.sleep(1)  # дать время ОС освободить файл
            try:
                os.remove(f"accounts/parsing/{session_name}.session")
            except FileNotFoundError:
                pass  # файл уже удалён

            continue  # переходим к следующей сессии

        me = await client.get_me()
        phone = me.phone or ""
        logger.info(f"🧾 Аккаунт: | ID: {me.id} | Phone: {phone}")
        logger.info("✅ Сессия активна, подключение успешно!")

        await asyncio.sleep(1)  # дать время ОС освободить файл
        await client.disconnect()
        try:
            os.rename(f"accounts/parsing/{session_name}.session", f"accounts/parsing/{phone}.session")
        except FileExistsError:
            await client.disconnect()
            os.remove(f"accounts/parsing/{session_name}.session")

        if client.is_connected():
            await client.disconnect()
