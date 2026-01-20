# -*- coding: utf-8 -*-
import asyncio
from pathlib import Path

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger  # https://github.com/Delgan/loguru
from telethon.sessions import StringSession
from telethon.sync import TelegramClient

from account_manager.auth import connect_client_test
from account_manager.subscription import subscription_telegram
from keyboards.keyboards import back_keyboard
from states.states import MyStatesParsing
from system.dispatcher import api_id, api_hash
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
    text = "Введите ссылку на группу, для поиска ключевых слов"
    await message.answer(text, reply_markup=back_keyboard())

    await state.set_state(MyStatesParsing.get_url)


@router.message(MyStatesParsing.get_url)
async def get_url(message: Message, state: FSMContext):
    """
    Обработчик команды "Получить URL".
    :param message:
    :param state:
    :return:
    """
    await state.update_data(url=message.text.strip())  # Сохраняем URL в контекст данных
    text = "Введите ключевое слово для поиска\n\n"
    await message.answer(text, reply_markup=back_keyboard())
    await state.set_state(MyStatesParsing.get_keyword)


@router.message(MyStatesParsing.get_keyword)
async def get_keyword(message: Message, state: FSMContext):
    """
    J
    :param message:
    :param state:
    :return:
    """
    keyword = message.text.strip()  # Получаем ключевое слово из сообщения
    text = "Данные приняты, ожидайте результата\n\n"
    await message.answer(text, reply_markup=back_keyboard())
    await state.update_data(keyword=keyword)
    data = await state.get_data()  # Получаем данные из контекста состояния
    await state.clear()  # Завершаем текущее состояние машины состояния
    logger.info(f"Полученые данные от пользователя: ссылка {data.get("url")}, ключевое слово: {data.get('keyword')}")
    await parse_group_for_keywords(url=data.get("url"), keyword=data.get("keyword"), message=message)


async def scanning_folder_for_session_files(message: Message, path):
    """
    Сканируем папку на наличие session-файлов
    :param message:
    :param path:
    :return:
    """
    sessions_dir = Path(path)
    session_files = list(sessions_dir.glob('*.session'))

    if not session_files:
        await message.answer("❌ Не найдено ни одного session-файла в папке accounts/parsing")
        logger.error("Session-файлы не найдены")
        return
    return session_files


async def checking_accounts_for_validity(message):
    """
    Проверка аккаунтов на валидность
    :param message: (telegram.Message) Объект сообщения, отправленный пользователем.
    :return:
    """
    # 1. Сканируем папку на наличие session-файлов
    session_files = await scanning_folder_for_session_files(message=message, path="accounts/parsing_grup")
    logger.info(f"{session_files}")
    # Получаем имена сессий (без расширения .session)
    available_sessions = [str(f.stem) for f in session_files]
    logger.info(f"Найдено {len(available_sessions)} аккаунтов: {available_sessions}")
    # Проверка аккаунтов на валидность из папки parsing
    await connect_client_test(available_sessions=available_sessions, path="accounts/parsing_grup")


async def parse_group_for_keywords(url, keyword, message: Message):
    """
    Парсит группу на наличие ключевых слов.
    :param url:
    :param keyword:
    :param message: (telegram.Message) Объект сообщения, отправленный пользователем.
    :return:
    """

    await checking_accounts_for_validity(message)
    session_files = await scanning_folder_for_session_files(message=message, path="accounts/parsing_grup")
    # Получаем имена сессий (без расширения .session)
    available_sessions = [str(f.stem) for f in session_files]
    logger.info(f"Найдено {len(available_sessions)} аккаунтов: {available_sessions}")

    # processed = 0
    # current_session_index = 0
    # while processed < len(available_sessions):
    # Подключаемся к текущему аккаунту
    session_path = f'accounts/parsing_grup/{available_sessions[0]}'
    logger.info(f"Подключаемся к сессии: {session_path}")
    client = TelegramClient(
        session_path, api_id, api_hash,
        system_version="4.16.30-vxCUSTOM"
    )
    await client.connect()
    session_string = StringSession.save(client.session)
    # Создаем клиент, используя StringSession и вашу строку
    client = TelegramClient(
        StringSession(session_string),
        api_id=api_id,
        api_hash=api_hash,
        system_version="4.16.30-vxCUSTOM"
    )

    await client.connect()
    await asyncio.sleep(1)

    await subscription_telegram(client, url)


def register_handlers_checking_group_for_keywords():
    """Регистрирует обработчики для проверки группы на наличие ключевых слов."""
    router.message.register(checking_group_for_keywords, F.text == "Проверка группы на наличие ключевых слов")
