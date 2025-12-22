# -*- coding: utf-8 -*-
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from database.database import User
from keyboards.keyboards import back_keyboard
from locales.locales import get_text
from states.states import MyStates
from system.dispatcher import router


@router.message(F.text == "Поиск групп / каналов")
async def handle_enter_keyword_menu(message: Message, state: FSMContext):
    """Ввод ключевого слова"""
    telegram_user = message.from_user
    user = User.get(User.user_id == telegram_user.id)

    logger.info(
        f"Пользователь {telegram_user.id} {telegram_user.username} {telegram_user.first_name} {telegram_user.last_name} перешел в меню Ввод ключевого слова")

    await message.answer(
        get_text(user.language, "enter_keyword"),
        reply_markup=back_keyboard()  # клавиатура назад
    )
    await state.set_state(MyStates.entering_keyword)

def register_handlers_pars_ai():
    router.register_message_handler(handle_enter_keyword_menu)