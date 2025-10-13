from aiogram import F
from aiogram.filters import CommandStart
from aiogram.types import Message

from database.database import User
from keyboards.keyboards import get_lang_keyboard
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


@router.message(F.text.in_({"🇷🇺 Русский", "🇬🇧 English"}))
async def handle_language_selection(message: Message):
    user_tg = message.from_user
    user = User.get(User.user_id == user_tg.id)

    # Устанавливаем язык в зависимости от выбора
    if message.text == "🇷🇺 Русский":
        user.language = "ru"
        confirm = get_text("ru", "lang_selected")
    elif message.text == "🇬🇧 English":
        user.language = "en"
        confirm = get_text("en", "lang_selected")
    else:
        return  # не должно случиться, но на всякий

    user.save()

    # Подтверждаем выбор и отправляем приветствие
    await message.answer(confirm, reply_markup=None)
    await message.answer(get_text(user.language, "welcome_message"))


def register_greeting_handler():
    router.message.register(command_start_handler)
    router.message.register(handle_language_selection)
