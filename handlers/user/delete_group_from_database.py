# -*- coding: utf-8 -*-
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger  # https://github.com/Delgan/loguru

from keyboards.user.keyboards import back_keyboard
from states.states import MyStates
from system.dispatcher import router


@router.message(F.text == "Удалить группу из отслеживания")
async def delete_group_from_database(message: Message, state: FSMContext):
    """
    Удаление группы из базы данных
    """
    await state.clear()  # Сбрасываем текущее состояние FSM
    await message.answer("Введите username в виде @username, для удаления из базы данных", reply_markup=back_keyboard())
    await state.set_state(MyStates.del_username_groups)


@router.message(MyStates.del_username_groups)
async def del_user_in_db(message: Message, state: FSMContext) -> None:
    """
    Удаляем пользователя
    """
    group_username = message.text.strip()
    logger.info(f"Пользователь ввёл ссылку: {group_username}")
    await state.clear()  # Завершаем текущее состояние машины состояния


def register_handlers_delete():
    router.message.register(delete_group_from_database)
