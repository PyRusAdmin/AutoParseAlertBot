# -*- coding: utf-8 -*-
import asyncio
import os

from loguru import logger
from telethon import TelegramClient, events
from telethon.errors import UserAlreadyParticipantError, FloodWaitError, InviteRequestSentError
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import Message

from database.database import create_groups_model, create_keywords_model, create_group_model
from keyboards.keyboards import menu_launch_tracking_keyboard
from locales.locales import get_text
from system.dispatcher import api_id, api_hash

# ⚙️ Конфигурация
CONFIG = {
    "target_channel_id": -1001918436153,
}

# 🧠 Простейший трекер сообщений (в памяти)
forwarded_messages = set()


async def get_target_group_id(client: TelegramClient, user_id: int):
    """
    Получает ID целевой группы для пересылки сообщений из базы данных
    :param client: Объект TelegramClient
    :param user_id: ID пользователя
    :return: ID группы или None
    """
    GroupModel = create_group_model(user_id=user_id)

    # Создаем таблицу, если не существует
    if not GroupModel.table_exists():
        GroupModel.create_table()
        logger.info(f"Created target group table for user {user_id}")
        return None

    # Получаем первую группу из базы (можно модифицировать для нескольких групп)
    groups = list(GroupModel.select())
    if not groups:
        logger.warning(f"No target group found for user {user_id}")
        return None

    target_username = groups[0].user_group
    logger.info(f"Target group username: {target_username}")

    try:
        # Получаем сущность группы/канала
        entity = await client.get_entity(target_username)
        target_group_id = entity.id
        logger.success(f"✅ Target group ID resolved: {target_group_id}")
        return target_group_id
    except Exception as e:
        logger.error(f"❌ Failed to resolve target group {target_username}: {e}")
        return None


async def join_target_group(client: TelegramClient, user_id):
    """
    Подписывается на целевую группу для пересылки сообщений
    :param client: Объект TelegramClient
    :param user_id: ID пользователя
    :return: ID группы или None
    """
    GroupModel = create_group_model(user_id=user_id)

    if not GroupModel.table_exists():
        GroupModel.create_table()
        return None

    groups = list(GroupModel.select())
    if not groups:
        return None

    target_username = groups[0].user_group

    try:
        logger.info(f"🔗 Attempting to join target group {target_username}...")
        await client(JoinChannelRequest(target_username))
        logger.success(f"✅ Successfully joined target group {target_username}")

        # Получаем ID группы
        entity = await client.get_entity(target_username)
        return entity.id

    except UserAlreadyParticipantError:
        logger.info(f"ℹ️ Already member of target group {target_username}")
        entity = await client.get_entity(target_username)
        return entity.id

    except FloodWaitError as e:
        logger.warning(f"⚠️ FloodWait error. Waiting {e.seconds} seconds...")
        await asyncio.sleep(e.seconds)
        try:
            await client(JoinChannelRequest(target_username))
            entity = await client.get_entity(target_username)
            return entity.id
        except Exception as retry_error:
            logger.error(f"❌ Failed to join target group after retry: {retry_error}")
            return None

    except ValueError:
        logger.error(f"❌ Invalid target group username: {target_username}")
        return None

    except InviteRequestSentError:
        logger.error(f"❌ Invite request sent for {target_username}, waiting for approval")
        return None

    except Exception as e:
        logger.exception(f"❌ Failed to join target group {target_username}: {e}")
        return None


async def process_message(client, message: Message, chat_id: int, user_id, target_group_id):
    """
    Обрабатывает сообщение и пересылает его в целевую группу при наличии ключевых слов
    """
    if not message.message:
        return

    message_text = message.message.lower()
    msg_key = f"{chat_id}-{message.id}"

    if msg_key in forwarded_messages:
        return

    # Получаем ключевые слова из базы данных для данного пользователя
    Keywords = create_keywords_model(user_id=user_id)

    # Создаем таблицу, если она не существует
    if not Keywords.table_exists():
        Keywords.create_table()
        logger.info(f"Создана таблица ключевых слов для пользователя {user_id}")
        return  # Таблица только что создана, ключевых слов еще нет

    keywords = [keyword.user_keyword for keyword in Keywords.select() if keyword.user_keyword]

    # Если нет ключевых слов, выходим
    if not keywords:
        return

    # Приводим ключевые слова к нижнему регистру для поиска
    keywords_lower = [keyword.lower() for keyword in keywords]

    # Используем ключевые слова из базы данных
    if any(keyword in message_text for keyword in keywords_lower):
        logger.info(f"📌 Найдено совпадение. Пересылаю сообщение ID={message.id}")
        try:
            # Убедитесь, что CONFIG["target_channel_id"] определен
            # await client.forward_messages(CONFIG["target_channel_id"], message)
            await client.forward_messages(target_group_id, message)
            forwarded_messages.add(msg_key)
        except Exception as e:
            logger.exception(f"❌ Ошибка при пересылке: {e}")


async def join_required_channels(client: TelegramClient, user_id):
    """
    Подписывается на обязательные каналы (источники сообщений)
    :param client: Объект TelegramClient
    :param user_id: Объект пользователя Telegram
    :return: None
    """

    # Получаем все username из базы данных
    Groups = create_groups_model(user_id=user_id)  # Создаём таблицу для групп
    Groups.create_table()

    channels = [group.username_chat_channel for group in Groups.select()]

    for channel in channels:
        try:
            logger.info(f"🔗 Пробую подписаться на {channel}...")
            await client(JoinChannelRequest(channel))
            logger.success(f"✅ Подписка на {channel} выполнена")
            logger.warning("⚠️ Ожидание 5 секунд для подписки на следующую группу")
            await asyncio.sleep(5)
        except UserAlreadyParticipantError:
            logger.info(f"ℹ️ Уже подписан на {channel}")
        except FloodWaitError as e:
            if e.seconds:
                logger.warning(
                    f"⚠️ Превышено ограничение на количество запросов в секунду. Ожидание {e.seconds} секунд...")
                await asyncio.sleep(e.seconds)
                try:
                    await client(JoinChannelRequest(channel))
                    logger.success(f"✅ Подписка на {channel} выполнена")
                except InviteRequestSentError:
                    logger.error(f"❌ Невозможно подписаться на {channel} (приглашение уже отправлено)")
        except ValueError:
            logger.error(f"❌ Не удалось подписаться на {channel} (невалидная ссылка)")
            # Удаляем невалидную запись из базы
            deleted = Groups.delete().where(Groups.username_chat_channel == channel).execute()
            if deleted:
                logger.info(f"🗑️ Канал {channel} удалён из базы данных пользователя {user_id}")
        except InviteRequestSentError:
            logger.error(f"❌ Невозможно подписаться на {channel} (приглашение уже отправлено)")
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

    # === Подключаемся к целевой группе для пересылки ===
    target_group_id = await join_target_group(client=client, user_id=user_id)

    if not target_group_id:
        logger.error("❌ Failed to join target group or group not configured")
        await message.answer(
            get_text(user.language, "target_group_missing"),
            reply_markup=menu_launch_tracking_keyboard()
        )
        await client.disconnect()
        return

    # === Подключаемся к обязательным каналам ===
    await join_required_channels(client=client, user_id=user_id)

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
        await process_message(client, event.message, event.chat_id, user_id, target_group_id)

    logger.info("👂 Бот слушает новые сообщения...")
    try:
        await client.run_until_disconnected()
    finally:
        await client.disconnect()
        logger.info("🛑 Бот остановлен.")
