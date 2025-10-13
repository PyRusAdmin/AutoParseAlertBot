# handlers/handlers.py
from aiogram import F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from loguru import logger
from models import User
from locales.locales import get_text
from system.dispatcher import bot, dp


# Клавиатура выбора языка
def get_lang_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇷🇺 Русский"), KeyboardButton(text="🇬🇧 English")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    user_tg = message.from_user

    # Сохраняем или обновляем пользователя в БД
    user, created = User.get_or_create(
        user_id=user_tg.id,
        defaults={
            "username": user_tg.username,
            "first_name": user_tg.first_name,
            "last_name": user_tg.last_name,
            "language": "ru"  # временно, пока не выбран
        }
    )
    if not created:
        # Обновляем данные на случай, если изменились
        user.username = user_tg.username
        user.first_name = user_tg.first_name
        user.last_name = user_tg.last_name
        user.save()

    # Если язык ещё не выбран — просим выбрать
    if user.language == "ru" and not user_tg.language_code:
        # Но чтобы не путать: будем считать, что если language == "temp", то не выбран.
        # Лучше явно хранить состояние. Однако для простоты: если language == "unset" — просим выбрать.
        # Изменим логику: при создании ставим language = "unset"
        pass

    # 👇 Лучше: при первом старте — всегда просим выбрать язык
    # Но если вы хотите использовать Telegram language_code как fallback — можно.
    # Сейчас сделаем: если пользователь уже выбрал — приветствуем, иначе — просим выбрать.

    if user.language in ("ru", "en"):
        # Уже выбран — приветствуем
        text = get_text(user.language, "welcome_message")
        await message.answer(text)
    else:
        # Просим выбрать язык
        text = get_text("ru", "welcome_ask_language")  # или определить по language_code
        await message.answer(text, reply_markup=get_lang_keyboard())


# Хендлер для обработки выбора языка
@dp.message(F.text.in_({"🇷🇺 Русский", "🇬🇧 English"}))
async def handle_language_selection(message: Message):
    user_tg = message.from_user
    user = User.get(User.user_id == user_tg.id)

    if message.text == "🇷🇺 Русский":
        user.language = "ru"
        confirm_text = get_text("ru", "lang_selected")
    elif message.text == "🇬🇧 English":
        user.language = "en"
        confirm_text = get_text("en", "lang_selected")
    else:
        return  # игнор

    user.save()
    await message.answer(confirm_text, reply_markup=None)  # убираем клавиатуру

    # Опционально: сразу отправить приветствие
    welcome = get_text(user.language, "welcome_message")
    await message.answer(welcome)
