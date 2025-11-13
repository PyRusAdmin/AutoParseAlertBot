# -*- coding: utf-8 -*-
from groq import AsyncGroq
from loguru import logger

from core.config import selectedmodel, GROQ_API_KEY
from core.proxy_config import setup_proxy


async def get_groq_response(user_input):
    """Получение ответа от Groq API."""
    setup_proxy()  # Установка прокси
    # Инициализация Groq клиента
    client_groq = AsyncGroq(api_key=GROQ_API_KEY)
    try:
        # Формируем запрос к Groq API
        chat_completion = await client_groq.chat.completions.create(

            model="meta-llama/llama-4-scout-17b-16e-instruct",

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
