from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_lang_keyboard():
    """Клавиатура выбора языка"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇷🇺 Русский"), KeyboardButton(text="🇬🇧 English")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False  # Отправлять сообщение только один раз
    )


def main_menu_keyboard():
    """Клавиатура главного меню"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Настройки")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False  # Отправлять сообщение только один раз
    )


def settings_keyboard():
    """Клавиатура настроек"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔁 Обновить список")],
            [KeyboardButton(text="Подключить аккаунт")],
            [KeyboardButton(text="Сменить язык")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False  # Отправлять сообщение только один раз
    )
