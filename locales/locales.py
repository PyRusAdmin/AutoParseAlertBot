LOCALES = {
    "ru": {
        "welcome_ask_language": "Привет! Пожалуйста, выберите язык:",
        "welcome_message": "Добро пожаловать!",
        "lang_selected": "Отлично! Теперь весь интерфейс будет на этом языке.",
        "settings_message": "В данном меню вы можете подключить аккаунт Telegram, а также изменить язык интерфейса, добавить группы / каналы для отслеживания, изменить ключевые слова и т.д.",
    },
    "en": {
        "welcome_ask_language": "Hi! Please choose your language:",
        "welcome_message": "Welcome!",
        "lang_selected": "Great! The interface will now be in this language.",
        "settings_message": "In this menu, you can connect a Telegram account, as well as change the interface language, add groups/channels for tracking, change keywords, etc.",
    }
}


def get_text(lang: str, key: str) -> str:
    return LOCALES.get(lang, LOCALES["ru"]).get(key, "⚠️ Text not found")
