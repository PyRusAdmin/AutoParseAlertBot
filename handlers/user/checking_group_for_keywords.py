# -*- coding: utf-8 -*-
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from keyboards.keyboards import back_keyboard
from states.states import MyStatesParsing
from system.dispatcher import router


@router.message(F.text == "Проверка группы на наличие ключевых слов")
async def checking_group_for_keywords(message: Message, state: FSMContext):
    """
    Обработчик команды "Проверка группы на наличие ключевых слов".

    Принимает данные от пользователи и начинает процесс проверки группы на наличие ключевых слов.

    :param message: (Message) Объект входящего сообщения от пользователя.
    :param state: (FSMContext) Контекст машины состояний, используется для сброса текущего состояния.
    :return: None
    """
    await state.clear()  # Завершаем текущее состояние машины состояния
    user_tg = message.from_user

    text = "Введите ссылку на группу, для поиска ключевых слов"
    await message.answer(text, reply_markup=back_keyboard())

    await state.set_state(MyStatesParsing.get_url)


@router.message(MyStatesParsing.get_url)
async def get_url(message: Message, state: FSMContext):
    raw_input = message.text.strip()

    text = "Введите ключевое слово для поиска\n\n"
    await message.answer(text, reply_markup=back_keyboard())

    await state.set_state(MyStatesParsing.get_keyword)


@router.message(MyStatesParsing.get_keyword)
async def get_keyword(message: Message, state: FSMContext):
    raw_input = message.text.strip()

    text = "Данные приняты, ожидайте результата\n\n"
    await message.answer(text, reply_markup=back_keyboard())

    await state.clear()  # Завершаем текущее состояние машины состояния


def register_handlers_checking_group_for_keywords():
    """Регистрирует обработчики для проверки группы на наличие ключевых слов."""
    router.message.register(checking_group_for_keywords, F.text == "Проверка группы на наличие ключевых слов")
