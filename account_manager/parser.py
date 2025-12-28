# -*- coding: utf-8 -*-
import asyncio
import os

from loguru import logger  # https://github.com/Delgan/loguru
from telethon import events
from telethon.errors import UserAlreadyParticipantError, FloodWaitError, InviteRequestSentError
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import Message

from account_manager.auth import connect_client
from database.database import create_groups_model, create_keywords_model, create_group_model
from keyboards.keyboards import menu_launch_tracking_keyboard
from locales.locales import get_text

# 🧠 Простейший трекер сообщений (в памяти)
forwarded_messages = set()


async def join_target_group(client, user_id):
    """
    Подписывает клиента Telethon на целевую группу пользователя для пересылки сообщений.

    Получает username целевой группы из персональной таблицы пользователя в базе данных
    и пытается присоединиться к ней. Возвращает идентификатор группы для дальнейшей отправки.

    Args:
        client (TelegramClient): Активный клиент Telethon для выполнения запросов.
        user_id (int): Уникальный идентификатор пользователя Telegram.

    Returns:
        int or None: Идентификатор целевой группы (entity.id) или None при ошибке.

    Raises:
        UserAlreadyParticipantError: Если клиент уже участник группы (обрабатывается).
        FloodWaitError: Если достигнут лимит запросов (обрабатывается с задержкой).
        InviteRequestSentError: Если требуется подтверждение приглашения.
        Exception: Логируется при любых других ошибках.

    Notes:
        - Использует модель `create_group_model` для доступа к данным пользователя.
        - Предполагается, что в таблице всегда одна запись (первый элемент списка).
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
    Обрабатывает входящее сообщение, проверяет его на совпадение с ключевыми словами
    и пересылает в целевую группу с контекстом при совпадении.

    Контекст включает название источника, ссылку на сообщение и сам текст.
    Использует глобальный set `forwarded_messages` для предотвращения дубликатов.

    Args:
        client (TelegramClient): Активный клиент для отправки сообщений.
        message (Message): Входящее сообщение для обработки.
        chat_id (int): Идентификатор чата-источника.
        user_id (int): Идентификатор пользователя, чьи ключевые слова используются.
        target_group_id (int): Идентификатор целевой группы для пересылки.

    Returns:
        None

    Raises:
        Exception: Логируется при ошибках отправки сообщения.

    Notes:
        - Сообщение пересылается только один раз (проверка по chat_id-message.id).
        - Ссылка формируется по разным правилам для супергрупп и обычных чатов.
        - Ключевые слова загружаются динамически из базы данных пользователя.
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
            # Получаем информацию о чате-источнике
            try:
                chat_entity = await client.get_entity(chat_id)
                chat_title = getattr(chat_entity, "title", None) or getattr(chat_entity, "username",
                                                                            None) or "Неизвестно"
            except Exception as e:
                logger.warning(f"Не удалось получить название чата: {e}")
                chat_title = "Неизвестно"

            # Формируем ссылку на сообщение
            # Для супергрупп/каналов (chat_id начинается с -100)
            if str(chat_id).startswith("-100"):
                # Удаляем префикс -100 и получаем чистый ID
                clean_chat_id = str(chat_id)[4:]
                message_link = f"https://t.me/c/{clean_chat_id}/{message.id}"
            else:
                # Для чатов с юзернеймом (если есть)
                try:
                    chat_entity = await client.get_entity(chat_id)
                    if chat_entity.username:
                        message_link = f"https://t.me/{chat_entity.username}/{message.id}"
                    else:
                        message_link = "Ссылка недоступна (нет юзернейма)"
                except Exception:
                    message_link = "Ссылка недоступна"

            # Формируем итоговое сообщение с контекстом
            context_text = (
                f"📥 **Новое сообщение**\n\n"
                f"**Источник:** {chat_title}\n"
                f"**Ссылка:** {message_link}\n\n"
                f"**Текст сообщения:**\n{message.message}"
            )

            # Отправляем в целевую группу
            await client.send_message(target_group_id, context_text)
            await client.forward_messages(target_group_id, message)
            logger.info(f"✅ Сообщение переслано в целевую группу (ID={target_group_id})")

            forwarded_messages.add(msg_key)
        except Exception as e:
            logger.exception(f"❌ Ошибка при отправке сообщения с контекстом: {e}")


async def join_required_channels(client, user_id, message):
    """
    Подписывает клиента на все отслеживаемые каналы и группы пользователя.

    Получает список username из персональной таблицы пользователя и пытается
    присоединиться к каждому. При успехе уведомляет пользователя.
    Невалидные ссылки удаляются из базы данных.

    Args:
        client (TelegramClient): Активный клиент для выполнения запросов.
        user_id (int): Идентификатор пользователя, чьи каналы нужно подключить.
        message (Message): Объект сообщения AIOgram для отправки уведомлений.

    Returns:
        None

    Raises:
        UserAlreadyParticipantError: Если клиент уже участник (обрабатывается).
        FloodWaitError: Если достигнут лимит запросов (обрабатывается с задержкой).
        InviteRequestSentError: Если требуется подтверждение приглашения.
        ValueError: Если username невалиден (обрабатывается с удалением из БД).
        Exception: Логируется при любых других ошибках.

    Notes:
        - Между подписками добавляется задержка в 5 секунд для избежания Flood.
        - Использует модель `create_groups_model` для доступа к данным.
    """

    # Получаем все username из базы данных
    Groups = create_groups_model(user_id=user_id)  # Создаём таблицу для групп
    Groups.create_table()

    channels = [group.username_chat_channel for group in Groups.select()]

    for channel in channels:
        try:
            logger.info(f"🔗 Пробую подписаться на {channel}")

            await client(JoinChannelRequest(channel))
            logger.success(f"✅ Подписка на {channel} выполнена")

            await message.answer(
                f"✅ Подписка на {channel} выполнена",
                reply_markup=menu_launch_tracking_keyboard()  # клавиатура выбора языка
            )

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


async def ensure_joined_target_group(client, message, user_id: int):
    """
    Обеспечивает подключение клиента Telethon к целевой группе пользователя.

    Обёртка вокруг `join_target_group`, которая проверяет успешность подключения
    и при необходимости отправляет пользователю сообщение об ошибке.

    Args:
        client (TelegramClient): Активный клиент для выполнения запросов.
        message (Message): Объект сообщения AIOgram для отправки уведомления об ошибке.
        user_id (int): Уникальный идентификатор пользователя Telegram.

    Returns:
        int or None: Идентификатор целевой группы (entity.id) при успехе, иначе None.

    Notes:
        - Если подключение не удалось, функция возвращает None (клиент НЕ отключается).
        - Используется для упрощения логики в функции `filter_messages`.
    """
    logger.info("Подключаемся к целевой группе для пересылки")
    target_group_id = await join_target_group(client=client, user_id=user_id)

    if not target_group_id:
        text_error = "❌ Аккаунту не удалось присоединиться к целевой группе, проверьте подключенную группу"
        logger.error(text_error)
        await message.answer(
            text=text_error,
            reply_markup=menu_launch_tracking_keyboard()
        )
        # НЕ отключаем клиент здесь — это будет сделано в finally блоке filter_messages
        return None

    return target_group_id


async def get_user_channels_or_notify(user_id: int, user, message, client):
    """
    Получает список каналов/групп пользователя из его персональной таблицы.
    Если список пуст — отправляет уведомление пользователю, отключает клиент и возвращает None.

    Args:
        user_id (int): ID пользователя Telegram.
        user: Объект пользователя (с полем `language`).
        message: Aiogram Message для отправки ответа.
        client: Telethon клиент (будет отключён в случае ошибки).

    Returns:
        list[str] | None: Список username каналов или None, если список пуст.
    """
    Groups = create_groups_model(user_id=user_id)

    # Создаём таблицу, если её ещё нет (безопасно благодаря Peewee)
    if not Groups.table_exists():
        Groups.create_table()

    channels = [group.username_chat_channel for group in Groups.select()]

    if not channels:
        logger.warning("⚠️ Список каналов пуст. Добавьте группы в базу данных.")
        await client.disconnect()
        await message.answer(
            get_text(user.language, "tracking_launch_error"),
            reply_markup=menu_launch_tracking_keyboard()
        )
        return None

    return channels


async def filter_messages(message, user_id, user, session_path):
    """
    Основная функция запуска процесса отслеживания сообщений в Telegram.

    Инициализирует клиент Telethon с помощью сессии пользователя, подключается
    к целевой группе (для пересылки) и к отслеживаемым каналам, затем начинает
    слушать новые сообщения. При совпадении с ключевыми словами — пересылает
    сообщение с контекстом.

    Работает до принудительной остановки (stop_tracking).

    :param message: (Message) Объект сообщения AIOgram для взаимодействия с пользователем.
    :param user_id: (int) Идентификатор пользователя Telegram.
    :param user: (User) Модель пользователя из базы данных (для языка и данных).
    :param session_path: (str) Полный путь к файлу сессии (.session) для авторизации.
    :return: None

    Raises:
        Exception: Логируется при ошибках инициализации или подключения.

    Notes:
        - Использует event-based обработку через `client.on(events.NewMessage)`.
        - Состояние отслеживания хранится в памяти (`forwarded_messages`).
        - После остановки клиент корректно отключается.
    """
    user_id = str(user_id)  # <-- ✅ преобразуем в строку
    logger.info(f"🚀 Запуск бота для user_id={user_id}...")

    logger.info(f"📂 Найден файл сессии: {session_path}")
    # Telethon ожидает session_name без расширения
    session_name = session_path.replace(".session", "")

    client = await connect_client(session_name, user)  # <-- ✅ подключаемся к клиенту Telethon

    try:

        # === Подключаемся к целевой группе для пересылки ===
        target_group_id = await ensure_joined_target_group(client=client, message=message, user_id=user_id)

        # Если не удалось подключиться к целевой группе — выходим
        if not target_group_id:
            return

        # === Подключаемся к обязательным каналам ===
        await join_required_channels(client=client, user_id=user_id, message=message)

        # === Загружаем список каналов из базы ===
        channels = await get_user_channels_or_notify(user_id=user_id, user=user, message=message, client=client)

        # Если каналов нет — выходим
        if not channels:
            return

        # === Обработка новых сообщений ===
        @client.on(events.NewMessage(chats=channels))
        async def handle_new_message(event: events.NewMessage.Event):
            await process_message(client, event.message, event.chat_id, user_id, target_group_id)

        logger.info("👂 Бот слушает новые сообщения...")
        await message.answer(
            "👂 Бот слушает новые сообщения...",
            reply_markup=menu_launch_tracking_keyboard()
        )

        await client.run_until_disconnected()

    except Exception as e:
        logger.exception(f"❌ Критическая ошибка в filter_messages: {e}")

    finally:
        # Гарантированное отключение клиента в любом случае
        if client.is_connected():
            await client.disconnect()
            logger.info("🛑 Клиент отключён.")


async def stop_tracking(user_id, message, user):
    """
    Останавливает процесс отслеживания сообщений для пользователя.

    Находит сессию пользователя в папке 'accounts/', инициализирует клиент Telethon
    и отключает его, что приводит к остановке `client.run_until_disconnected()`
    в функции `filter_messages`.

    Args:
        user_id (int): Идентификатор пользователя Telegram.
        message (Message): Объект сообщения AIOgram для отправки подтверждения.
        user (User): Модель пользователя (не используется напрямую, но может быть нужно для будущих уведомлений).

    Returns:
        None

    Notes:
        - Функция не проверяет, активно ли отслеживание — всегда пытается отключить сессию.
        - Использует тот же механизм подключения, что и `filter_messages`, для доступа к сессии.
        - После вызова `client.disconnect()` управление возвращается в `filter_messages`.
    """
    user_id = str(user_id)  # <-- ✅ преобразуем в строку

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
    client = await connect_client(session_name, user)  # <-- ✅ подключаемся к клиенту Telethon

    logger.info("🛑 Остановка отслеживания сообщений...")
    await client.disconnect()
