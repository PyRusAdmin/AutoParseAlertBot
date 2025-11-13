# -*- coding: utf-8 -*-
import asyncio

from groq import AsyncGroq
from loguru import logger
from telethon import TelegramClient
from telethon.errors import UsernameNotOccupiedError, FloodWaitError
from telethon.tl.types import Channel

from core.config import GROQ_API_KEY
from core.proxy_config import setup_proxy
from system.dispatcher import api_id, api_hash


async def get_groq_response(user_input):
    """Получение ответа от Groq API."""
    setup_proxy()  # Установка прокси
    # Инициализация Groq клиента
    client_groq = AsyncGroq(api_key=GROQ_API_KEY)
    try:
        # Формируем запрос к Groq API
        chat_completion = await client_groq.chat.completions.create(
            model="llama-3.1-70b-versatile",  # ✅ Заменено на подходящую модель
            messages=[
                {
                    "role": "user",
                    "content": f"Придумай 10 вариаций названий для групп {user_input}. Ответ дать строго наименования в столбик, без перечисления и без пояснения. 1. 2. 3. не применяй"
                }
            ],
        )
        # Возвращаем ответ от ИИ
        logger.debug(f"Полный ответ от Groq: {chat_completion}")
        return chat_completion.choices[0].message.content
    except Exception as e:
        logger.exception(e)
        return ""  # ✅ Добавлен возврат пустой строки в случае ошибки


async def search_groups_in_telegram(group_names):
    """
    Ищет группы в Telegram по списку названий.
    Возвращает список найденных групп с данными.
    """
    client = TelegramClient('accounts/535185511/998339414118', api_id, api_hash)
    await client.connect()

    # ✅ Проверяем, нужно ли логиниться (если сессия не валидна)
    if not await client.is_user_authorized():
        logger.error("Клиент не авторизован. Запустите сначала авторизацию.")
        await client.disconnect()
        return []

    logger.info("Телеграм-клиент запущен.")

    found_groups = []

    for name in group_names:
        if not name.strip():
            continue

        logger.info(f"Ищу группу: '{name}'")

        try:
            # ✅ Поиск по названию
            result = await client.search_messages(
                None,  # Все чаты
                limit=5,
                filter='channels',
                search=name.strip()
            )

            # Извлекаем уникальные каналы
            channels = set()
            for msg in result:
                if hasattr(msg.peer_id, 'channel_id'):
                    entity = await client.get_entity(msg.peer_id)
                    if isinstance(entity, Channel) and entity.title:
                        channels.add(entity)

            # Добавляем найденные каналы
            for channel in channels:
                found_groups.append({
                    'name': channel.title,
                    'username': f"@{channel.username}" if channel.username else "нет юзернейма",
                    'link': f"https://t.me/{channel.username}" if channel.username else "недоступна",
                    'participants': channel.participants_count if hasattr(channel, 'participants_count') else 'неизвестно'
                })

        except UsernameNotOccupiedError:
            logger.warning(f"Группа '{name}' не найдена.")
        except FloodWaitError as e:
            logger.error(f"Слишком много запросов. Ждём {e.seconds} секунд.")
            await asyncio.sleep(e.seconds + 1)
        except Exception as e:
            logger.exception(f"Ошибка при поиске '{name}': {e}")

    await client.disconnect()
    logger.info("Телеграм-клиент отключён.")
    return found_groups