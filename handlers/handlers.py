from aiogram import F
from aiogram.filters import CommandStart
from aiogram.types import Message

from database.database import User
from keyboards.keyboards import get_lang_keyboard, main_menu_keyboard, settings_keyboard
from locales.locales import get_text
from system.dispatcher import router


@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    user_tg = message.from_user

    # Создаём пользователя с language = "unset", если его нет
    user, created = User.get_or_create(
        user_id=user_tg.id,
        defaults={
            "username": user_tg.username,
            "first_name": user_tg.first_name,
            "last_name": user_tg.last_name,
            "language": "unset"  # ← ключевое: "unset" = язык не выбран
        }
    )
    if not created:
        # Обновляем профиль (на случай смены имени и т.п.)
        user.username = user_tg.username
        user.first_name = user_tg.first_name
        user.last_name = user_tg.last_name
        user.save()

    # Если язык ещё не выбран — просим выбрать
    if user.language == "unset":
        # Можно предложить язык по умолчанию из Telegram, но всё равно дать выбор
        await message.answer(
            "👋 Привет! Пожалуйста, выберите язык / Please choose your language:",
            reply_markup=get_lang_keyboard()
        )
    else:
        # Язык уже выбран — приветствуем
        text = get_text(user.language, "welcome_message")
        await message.answer(text)


@router.message(F.text.in_(["🇷🇺 Русский", "🇬🇧 English"]))
async def handle_language_selection(message: Message):
    """Выбор языка"""
    user_tg = message.from_user
    user = User.get(User.user_id == user_tg.id)

    if message.text == "🇷🇺 Русский":
        user.language = "ru"
        confirm = get_text("ru", "lang_selected")
    elif message.text == "🇬🇧 English":
        user.language = "en"
        confirm = get_text("en", "lang_selected")

    user.save()

    await message.answer(confirm, reply_markup=main_menu_keyboard())


@router.message(F.text == "Настройки")
async def handle_settings(message: Message):
    """Открытие меню настроек"""
    user_tg = message.from_user
    user = User.get(User.user_id == user_tg.id)

    await message.answer(
        get_text(user.language, "settings_message"),
        reply_markup=settings_keyboard()  # клавиатура выбора языка
    )


@router.message(F.text == "Настройки")
async def handle_settings(message: Message):
    """Открытие меню настроек"""
    user_tg = message.from_user
    user = User.get(User.user_id == user_tg.id)

    await message.answer(
        get_text(user.language, "settings_message"),
        reply_markup=settings_keyboard()  # клавиатура выбора языка
    )


@router.message(F.text == "🔙 Назад")
async def handle_main_menu(message: Message):
    """Возврат в главное меню"""
    user_tg = message.from_user

    # Создаём пользователя с language = "unset", если его нет
    user, created = User.get_or_create(
        user_id=user_tg.id,
        defaults={
            "username": user_tg.username,
            "first_name": user_tg.first_name,
            "last_name": user_tg.last_name,
            "language": "unset"  # ← ключевое: "unset" = язык не выбран
        }
    )
    if not created:
        # Обновляем профиль (на случай смены имени и т.п.)
        user.username = user_tg.username
        user.first_name = user_tg.first_name
        user.last_name = user_tg.last_name
        user.save()

    # Если язык ещё не выбран — просим выбрать
    if user.language == "unset":
        # Можно предложить язык по умолчанию из Telegram, но всё равно дать выбор
        await message.answer(
            "👋 Привет! Пожалуйста, выберите язык / Please choose your language:",
            reply_markup=get_lang_keyboard()
        )
    else:
        # Язык уже выбран — приветствуем
        text = get_text(user.language, "welcome_message")
        await message.answer(text, reply_markup=main_menu_keyboard())


def register_greeting_handler():
    router.message.register(command_start_handler)
    router.message.register(handle_language_selection)
    router.message.register(handle_settings)
    router.message.register(handle_main_menu)  # обработчик для кнопки "Назад"
