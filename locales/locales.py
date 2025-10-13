LOCALES = {
    "ru": {
        "welcome_ask_language": "Привет! Пожалуйста, выберите язык:",
        "welcome_message": "Добро пожаловать!",
        "lang_selected": "Отлично! Теперь весь интерфейс будет на этом языке.",
    },
    "en": {
        "welcome_ask_language": "Hi! Please choose your language:",
        "welcome_message": "Welcome!",
        "lang_selected": "Great! The interface will now be in this language.",
    }
}


def get_text(lang: str, key: str) -> str:
    return LOCALES.get(lang, LOCALES["ru"]).get(key, "⚠️ Text not found")
