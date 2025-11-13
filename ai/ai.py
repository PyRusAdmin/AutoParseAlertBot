# -*- coding: utf-8 -*-
import asyncio

from groq import AsyncGroq
from loguru import logger
from telethon.errors import FloodWaitError, UsernameNotOccupiedError
from telethon.sync import TelegramClient, functions
from telethon.tl.types import Channel

from core.config import GROQ_API_KEY
from core.proxy_config import setup_proxy
from system.dispatcher import api_id, api_hash


async def get_groq_response(user_input):
    """Получение ответа от Groq API."""
    setup_proxy()  # Установка прокси
    client_groq = AsyncGroq(api_key=GROQ_API_KEY)
    try:
        chat_completion = await client_groq.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": f"Придумай 10 вариаций названий для групп {user_input}. Ответ дать строго наименования в столбик, без перечисления и без пояснения. 1. 2. 3. не применяй"
                }
            ],
        )
        logger.debug(f"Полный ответ от Groq: {chat_completion}")
        return chat_completion.choices[0].message.content
    except Exception as e:
        logger.exception(e)
        return ""


async def search_groups_in_telegram(group_names):
    """
    Ищет группы в Telegram по списку названий.
    Возвращает список найденных групп с данными.
    """
    client = TelegramClient('accounts/535185511/998339414118', api_id, api_hash)
    await client.connect()

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
            # ✅ Используем SearchRequest для поиска по названию
            search_results = await client(functions.contacts.SearchRequest(q=name, limit=10))

            # Обрабатываем результаты
            for chat in search_results.chats:
                if isinstance(chat, Channel) and chat.title:
                    found_groups.append({
                        'name': chat.title,
                        'username': f"@{chat.username}" if chat.username else "нет юзернейма",
                        'link': f"https://t.me/{chat.username}" if chat.username else "недоступна",
                        'participants': chat.participants_count if hasattr(chat, 'participants_count') else 'неизвестно',
                        'id': chat.id
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