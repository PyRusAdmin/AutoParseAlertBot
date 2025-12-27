# -*- coding: utf-8 -*-
import asyncio

import groq
from groq import AsyncGroq
from loguru import logger  # https://github.com/Delgan/loguru
from telethon.errors import FloodWaitError, UsernameNotOccupiedError
from telethon.sync import TelegramClient, functions
from telethon.tl.types import Channel

from core.config import GROQ_API_KEY
from core.proxy_config import setup_proxy
from system.dispatcher import api_id, api_hash


async def get_groq_response(user_input):
    """
    Асинхронно отправляет запрос к модели Llama 4 Scout через Groq API для генерации вариантов названий групп.

    Args:
        user_input (str): Тема или ключевое слово, на основе которого нужно придумать названия групп.

    Returns:
        str: Строка с 10 вариациями названий групп, разделёнными переносами строк.
             Возвращает пустую строку при ошибке аутентификации или других исключениях.

    Raises:
        groq.AuthenticationError: Если ключ API недействителен или не установлен.
        Exception: Логируется при других ошибках (сетевые ошибки, таймауты и т.д.).

    Notes:
        - Используется модель "meta-llama/llama-4-scout-17b-16e-instruct".
        - Ответ должен содержать только названия, без нумерации и пояснений.
        - Перед выполнением устанавливается прокси с помощью `setup_proxy()`.
    """
    setup_proxy()  # Установка прокси
    client_groq = AsyncGroq(api_key=GROQ_API_KEY)
    try:
        chat_completion = await client_groq.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": f"Придумай 20 вариаций названий для групп {user_input}. Ответ дать строго наименования в столбик, без перечисления и без пояснения. 1. 2. 3. не применяй"
                }
            ],
        )
        logger.debug(f"Полный ответ от Groq: {chat_completion}")
        return chat_completion.choices[0].message.content
    except groq.AuthenticationError:
        if GROQ_API_KEY:
            logger.error("Ошибка аутентификации с ключом Groq API.")
        else:
            logger.error("API ключ Groq API не установлен.")

    except Exception as e:
        logger.exception(e)
        return ""


async def search_groups_in_telegram(group_names):
    """
    Асинхронно ищет публичные группы и каналы в Telegram по заданным названиям.

    Для каждого названия выполняется поиск через Telegram API, и из результатов
    отбираются только каналы (Channel), содержащие совпадения по названию.

    Args:
        group_names (list[str]): Список строк с названиями групп для поиска.

    Returns:
        list[dict]: Список словарей с информацией о найденных группах. Каждый словарь содержит:
            - 'name' (str): Название группы.
            - 'username' (str): Юзернейм группы (с @) или "нет юзернейма".
            - 'link' (str): Ссылка на группу или "недоступна".
            - 'participants' (int or str): Количество участников или "неизвестно".
            - 'id' (int): Уникальный идентификатор чата в Telegram.

    Notes:
        - Требует предварительной авторизации клиента Telegram.
        - Обрабатывает ошибки FloodWaitError, приостанавливая выполнение на указанное время.
        - Пропускает пустые строки в списке запросов.
        - Использует Telethon для низкоуровневого взаимодействия с Telegram API.
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
                        'participants': chat.participants_count if hasattr(chat,
                                                                           'participants_count') else 'неизвестно',
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
