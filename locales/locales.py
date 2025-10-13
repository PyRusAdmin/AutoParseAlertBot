# locales.py

LOCALES = {
    "ru": {
        "welcome_message": "Добро пожаловать!",
    },
    "en": {
        "welcome_message": "Welcome!",
    }
}


def get_text(lang: str, key: str) -> str:
    # Возвращаем текст на нужном языке, по умолчанию — русский
    return LOCALES.get(lang, LOCALES["ru"]).get(key, "⚠️ Текст не найден")
