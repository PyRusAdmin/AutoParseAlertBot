# -*- coding: utf-8 -*-

LOCALES = {
    "ru": {
        "welcome_ask_language": "🌍 Привет! Пожалуйста, выберите язык интерфейса:",

        "welcome_message_template": (
            "🤖 Добро пожаловать в Telegram-бота для отслеживания 🔍 ключевых слов в группах и каналах!\n\n"

            "📋 <b>Версия:</b> {version}\n"
            "📅 <b>Дата выхода:</b> 28 декабря 2025 года\n\n"

            "📊 <b>Найдено групп / каналов пользователями:</b> {groups_count}\n\n"

            "📱 <b>Подключённых аккаунтов:</b> {count}\n"
            "📤 <b>Технических групп (для пересылки):</b> {group_count}\n"
            "🔍 <b>Ключевых слов:</b> {keywords_count}\n"
            "📡 <b>Отслеживаемых каналов:</b> {get_groups}\n\n"

            "💡 <b>Совет:</b> для получения обновлённого функционала рекомендуется перезапускать бота через /start"
        ),

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
        "launching_tracking": "🚀 Запуск отслеживания сообщений...\n\nОстановка отслеживания возможна только после подписки на группы / каналы",
        "tracking_launch_error": (
            "⚠️ Список каналов пуст.\n\n"
            "Добавьте хотя бы одну группу или канал для отслеживания 🔍\n"
            "через меню настроек ⚙️"
        ),
        "update_list": "Пришлите ссылку на группу в формате @username",
        "account_missing": "⚠️ У вас нет подключенного аккаунта Telegram.\n\n",
        "account_missing_2": (
            "⚠️ Сессия аккаунта недействительна (session файл не валидный) — требуется повторный вход. Отправьте валидный файл сессии"
        ),
        "enter_keyword": "🔍 Введите ключевое слово / словосочетание для отслеживания",
        "enter_group": (
            "🔍 Введите ссылку на группу в формате @username, в которую будет пересылаться сообщение, обнаруженное по ключевому слову"
        ),
    },

    "en": {
        "welcome_ask_language": "🌍 Hi! Please choose your interface language:",

        "welcome_message_template_en": (
            "🤖 Welcome to the Telegram bot for tracking 🔍 keywords in groups and channels!\n\n"

            "📋 <b>Version:</b> {version}\n"
            "📅 <b>Release date:</b> December 28, 2025\n\n"

            "📊 <b>Groups/channels found by users:</b> {groups_count}\n\n"

            "📱 <b>Connected accounts:</b> {count}\n"
            "📤 <b>Technical groups (for forwarding):</b> {group_count}\n"
            "🔍 <b>Keywords tracked:</b> {keywords_count}\n"
            "📡 <b>Channels being monitored:</b> {get_groups}\n\n"

            "💡 <b>Tip:</b> to get the latest features, please restart the bot using /start"
        ),

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
        "update_list": "Please send a link to the group in the format @username",
        "account_missing": "⚠️ You do not have a connected Telegram account.\n\n",
        "account_missing_2": (
            "⚠️ The session file for your Telegram account is invalid — you need to log in again. Send a valid session file."
        ),
        "enter_keyword": "🔍 Enter a keyword / phrase to track",
        "enter_group": (
            "🔍 Enter a link to the group in the format @username to which the message will be forwarded when a keyword is detected"
        ),
    }
}


def get_text(lang: str, key: str) -> str:
    return LOCALES.get(lang, LOCALES["ru"]).get(key, "⚠️ Text not found")
