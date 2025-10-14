LOCALES = {
    "ru": {
        "welcome_ask_language": "🌍 Привет! Пожалуйста, выберите язык интерфейса:",
        "welcome_message": "🤖 Добро пожаловать в Telegram-бота для отслеживания 🔍 ключевых слов в группах и каналах!",
        "lang_selected": "✅ Отлично! Интерфейс теперь будет отображаться на выбранном языке.",
        "settings_message": (
            "⚙️ В этом меню вы можете:\n"
            "• 🔗 Подключить аккаунт Telegram\n"
            "• 🌐 Изменить язык интерфейса\n"
            "• 📢 Добавить группы и каналы для отслеживания\n"
            "• 🧩 Настроить ключевые слова и фильтры\n\n"
            "Выберите нужный пункт ниже 👇"
        ),
        "connect_account": (
            "📱 Для подключения аккаунта Telegram отправьте файл сессии в формате:\n"
            "`+79599999999.session`\n\n"
            "После загрузки бот начнёт использовать этот аккаунт для отслеживания сообщений."
        ),
        "launching_tracking": "🚀 Запуск отслеживания сообщений...",
        "tracking_launch_error": (
            "⚠️ Список каналов пуст.\n\n"
            "Добавьте хотя бы одну группу или канал для отслеживания 🔍\n"
            "через меню настроек ⚙️"
        ),
    },

    "en": {
        "welcome_ask_language": "🌍 Hi! Please choose your interface language:",
        "welcome_message": "🤖 Welcome to the Telegram bot for tracking 🔍 keywords in groups and channels!",
        "lang_selected": "✅ Great! The interface will now be displayed in your selected language.",
        "settings_message": (
            "⚙️ In this menu you can:\n"
            "• 🔗 Connect a Telegram account\n"
            "• 🌐 Change the interface language\n"
            "• 📢 Add groups and channels to track\n"
            "• 🧩 Configure keywords and filters\n\n"
            "Choose an option below 👇"
        ),
        "connect_account": (
            "📱 To connect your Telegram account, send a session file in the format:\n"
            "`+79599999999.session`\n\n"
            "Once uploaded, the bot will use this account to track messages."
        ),
        "launching_tracking": "🚀 Launching message tracking...",
        "tracking_launch_error": (
            "⚠️ The list of channels is empty.\n\n"
            "Please add at least one group or channel to track 🔍\n"
            "via the settings menu ⚙️"
        ),
    }
}


def get_text(lang: str, key: str) -> str:
    return LOCALES.get(lang, LOCALES["ru"]).get(key, "⚠️ Text not found")
