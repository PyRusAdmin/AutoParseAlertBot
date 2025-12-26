# -*- coding: utf-8 -*-

from aiogram import types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile

from system.dispatcher import router


@router.message(Command('log'))
async def log(message: types.Message, state: FSMContext):
    """Отправка логов администратору бота"""
    await state.clear()  # Завершаем текущее состояние машины состояния

    document = FSInputFile("logs/log.log")

    await message.answer_document(
        document=document,
        caption=f"📄 Лог файл с ошибками.",
        parse_mode="HTML"
    )


def register_handlers_log():
    """Регистрация обработчиков."""
    router.message.register(log)
