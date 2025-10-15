# -*- coding: utf-8 -*-
import os

from loguru import logger
from telethon import TelegramClient, events
from telethon.errors import UserAlreadyParticipantError
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import Message

from database.database import create_groups_model
from keyboards.keyboards import menu_launch_tracking_keyboard
from locales.locales import get_text
from system.dispatcher import api_id, api_hash

# ⚙️ Конфигурация
CONFIG = {
    "target_channel_id": -1001918436153,
    "keywords": ["киевский район", "донецк сити", "шахтерская площадь"],
}

# 🧠 Простейший трекер сообщений (в памяти)
forwarded_messages = set()


async def process_message(client, message: Message, chat_id: int):
    if not message.message:
        return

    message_text = message.message.lower()
    msg_key = f"{chat_id}-{message.id}"

    if msg_key in forwarded_messages:
        return

    if any(keyword in message_text for keyword in CONFIG["keywords"]):
        logger.info(f"📌 Найдено совпадение. Пересылаю сообщение ID={message.id}")
        try:
            await client.forward_messages(CONFIG["target_channel_id"], message)
            forwarded_messages.add(msg_key)
        except Exception as e:
            logger.exception(f"❌ Ошибка при пересылке: {e}")


async def join_required_channels(client: TelegramClient, user_tg):
    """
    Подписываемся на обязательные каналы
    :param client: Объект TelegramClient
    :param user_tg: Объект пользователя Telegram
    :return: None
    """

    # Получаем все username из базы данных
    Groups = create_groups_model(user_id=user_tg.id)  # Создаём таблицу для групп
    Groups.create_table()

    channels = [group.username_chat_channel for group in Groups.select()]

    for channel in channels:
        try:
            logger.info(f"🔗 Пробую подписаться на {channel}...")
            await client(JoinChannelRequest(channel))
            logger.success(f"✅ Подписка на {channel} выполнена")
        except UserAlreadyParticipantError:
            logger.info(f"ℹ️ Уже подписан на {channel}")
        except Exception as e:
            logger.exception(f"❌ Не удалось подписаться на {channel}: {e}")


async def filter_messages(message, user_id, user):
    """
    Запускает поиск сообщений по ключевым словам.
    :param message: Объект сообщения AIOgram
    :param user_id: ID пользователя Telegram, используется для поиска папки accounts/<user_id>/
    :param user: Объект пользователя
    """
    user_id = str(user_id)  # <-- ✅ преобразуем в строку
    logger.info(f"🚀 Запуск бота для user_id={user_id}...")

    # === Папка, где хранятся сессии ===
    session_dir = os.path.join("accounts", user_id)
    os.makedirs(session_dir, exist_ok=True)

    # === Поиск любого .session файла ===
    session_path = None
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

    logger.info(f"📂 Найден файл сессии: {session_path}")
    # Telethon ожидает session_name без расширения
    session_name = session_path.replace(".session", "")

    # === Подключение клиента Telethon ===
    client = TelegramClient(session_name, api_id, api_hash)
    await client.connect()

    # === Проверка авторизации ===
    if not await client.is_user_authorized():
        logger.error(f"⚠️ Сессия {session_path} недействительна — требуется повторный вход.")
        await message.answer(
            get_text(user.language, "account_missing_2"),
            reply_markup=menu_launch_tracking_keyboard()  # клавиатура выбора языка
        )
        return

    logger.info("✅ Сессия активна, подключение успешно!")

    # === Подключаемся к обязательным каналам ===
    await join_required_channels(client=client, user_tg=user_id)

    # === Загружаем список каналов из базы ===
    # Получаем список username из базы данных

    Groups = create_groups_model(user_id=user_id)  # Создаём таблицу для групп
    Groups.create_table()

    channels = [group.username_chat_channel for group in Groups.select()]
    if not channels:
        logger.warning("⚠️ Список каналов пуст. Добавьте группы в базу данных.")
        await client.disconnect()
        await message.answer(
            get_text(user.language, "tracking_launch_error"),
            reply_markup=menu_launch_tracking_keyboard()  # клавиатура выбора языка
        )
        return

    # === Обработка новых сообщений ===
    @client.on(events.NewMessage(chats=channels))
    async def handle_new_message(event: events.NewMessage.Event):
        await process_message(client, event.message, event.chat_id)

    logger.info("👂 Бот слушает новые сообщения...")
    try:
        await client.run_until_disconnected()
    finally:
        await client.disconnect()
        logger.info("🛑 Бот остановлен.")
