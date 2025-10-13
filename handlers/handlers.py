from aiogram.filters import CommandStart
from aiogram.types import Message
from loguru import logger

from locales.locales import get_text
from system.dispatcher import bot, dp


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    user_id = message.from_user.id
    user_name = message.from_user.username
    user_first_name = message.from_user.first_name
    user_last_name = message.from_user.last_name
    user_date = message.date.strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"{user_id} {user_name} {user_first_name} {user_last_name} {user_date}")

    # Определяем язык пользователя
    lang = message.from_user.language_code
    if lang not in ("ru", "en"):
        lang = "ru"

    sign_up_text = get_text(lang, "welcome_message")
    await bot.send_message(message.from_user.id, sign_up_text, disable_web_page_preview=True)


def register_greeting_handler():
    """Регистрируем handlers для бота"""
    dp.message.register(command_start_handler)
