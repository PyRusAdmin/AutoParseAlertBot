# -*- coding: utf-8 -*-
import re

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from ai.ai import get_groq_response, search_groups_in_telegram
from database.database import User
from keyboards.keyboards import back_keyboard
from locales.locales import get_text
from states.states import MyStates
from system.dispatcher import router


# Разбиваем ответ на строки и очищаем от номеров, точек, тире, звёздочек и прочего
def clean_group_name(name):
    # Удаляем начало строки: цифры, точки, тире, звёздочки, скобки, пробелы

    # Убираем всё, что до первого буквенного/кириллического символа
    cleaned = re.sub(r'^[\d\.\-\*\s\)\(\[\]]+', '', name).strip()
    return cleaned


@router.message(F.text == "Поиск групп / каналов")
async def handle_enter_keyword_menu(message: Message, state: FSMContext):
    """Ввод ключевого слова для поиска групп и каналов с помощью Ai"""
    await state.clear()

    telegram_user = message.from_user
    user = User.get(User.user_id == telegram_user.id)

    logger.info(
        f"Пользователь {telegram_user.id} {telegram_user.username} {telegram_user.first_name} {telegram_user.last_name} перешел в меню Ввод ключевого слова")

    await message.answer(
        get_text(user.language, "enter_keyword"),
        reply_markup=back_keyboard()  # клавиатура назад
    )
    await state.set_state(MyStates.entering_keyword_ai_search)


@router.message(MyStates.entering_keyword_ai_search)
async def handle_enter_keyword(message: Message, state: FSMContext):
    """Обработка введенного ключевого слова, для поиска групп и каналов"""

    user_input = message.text.strip()
    answer = await get_groq_response(user_input)
    logger.info(f"Ответ от Groq: {answer}")

    # Разбиваем ответ на строки
    group_names = [clean_group_name(line) for line in answer.splitlines() if line.strip()]
    # Убираем пустые и слишком короткие
    group_names = [name for name in group_names if len(name) > 2]
    logger.info(f"Получено {len(group_names)} названий: {group_names}")

    all_results = []
    for group_name in group_names:
        # Ищем в Telegram
        results = await search_groups_in_telegram([group_name])  # ✅ Передаём список
        logger.info(f"Найдено {len(results)} групп для '{group_name}':")
        all_results.extend(results)

        # Выводим результаты
        if results:
            logger.info("\n🔍 Найденные группы:")
            for group in results:
                logger.info(
                    f"✅ {group['name']} | {group['username']} | {group['link']} | Участников: {group['participants']}")
        else:
            logger.info("❌ Ничего не найдено.")

    await state.clear()


def register_handlers_pars_ai():
    router.message.register(handle_enter_keyword_menu)
