# -*- coding: utf-8 -*-
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger  # https://github.com/Delgan/loguru

from system.dispatcher import router


@logger.catch
@router.message(F.text == "Проверка аккаунтов")
async def checking_accounts(message: Message, state: FSMContext):
    """Проверка аккаунтов на валидность"""
    try:
        await state.clear()  # Сбрасываем текущее состояние FSM






    except Exception as e:
        logger.exception(e)


def register_checking_accounts():
    router.register.message(checking_accounts)