# -*- coding: utf-8 -*-
import asyncio
from pathlib import Path

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger  # https://github.com/Delgan/loguru
from telethon import TelegramClient
from telethon.sessions import StringSession

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


async def get_available_sessions(message, path: str = "accounts/parsing_grup"):
    """
    Сканирует указанную папку и возвращает список имён session-файлов без расширения.

    :param message: Объект сообщения от пользователя (для логирования или передачи в scanning_folder_for_session_files)
    :param path: Путь к папке с session-файлами
    :return: Список имён сессий (без расширения .session)
    """
    session_files = await scanning_folder_for_session_files(message=message, path=path)
    available_sessions = [str(f.stem) for f in session_files]
    logger.info(f"Найдено {len(available_sessions)} аккаунтов: {available_sessions}")
    return available_sessions


async def checking_accounts_for_validity(message):
    """
    Проверка аккаунтов на валидность
    :param message: (telegram.Message) Объект сообщения, отправленный пользователем.
    :return:
    """
    available_sessions = await get_available_sessions(message)
    # Проверка аккаунтов на валидность из папки parsing
    await connect_client_test(available_sessions=available_sessions, path="accounts/parsing_grup")


async def create_client_from_session(session_path: str, api_id: int, api_hash: str):
    """
    Создаёт подключённого TelegramClient, используя session-файл,
    затем переходит на StringSession для безопасного хранения в памяти.

    :param session_path: Путь к .session файлу
    :param api_id: API ID от Telegram
    :param api_hash: API Hash от Telegram
    :return: Подключённый клиент TelegramClient
    """

    # Создаём клиент из файла сессии
    client = TelegramClient(
        session_path, api_id, api_hash,
        system_version="4.16.30-vxCUSTOM"
    )
    await client.connect()

    # Сохраняем данные сессии в строку (StringSession)
    session_string = StringSession.save(client.session)

    # Отключаемся от первого клиента (можно освободить ресурсы при необходимости)
    await client.disconnect()

    # Создаём новый клиент на основе StringSession (без сохранения на диск)
    client = TelegramClient(
        StringSession(session_string),
        api_id=api_id,
        api_hash=api_hash,
        system_version="4.16.30-vxCUSTOM"
    )

    await client.connect()
    await asyncio.sleep(1)  # Даём время на стабильное подключение

    return client


async def parse_group_for_keywords(url, keyword, message: Message):
    """
    Парсит группу на наличие ключевых слов.
    :param url:
    :param keyword:
    :param message: (telegram.Message) Объект сообщения, отправленный пользователем.
    :return:
    """

    await checking_accounts_for_validity(message)
    available_sessions = await get_available_sessions(message)

    # Подключаемся к текущему аккаунту
    session_path = f'accounts/parsing_grup/{available_sessions[0]}'
    logger.info(f"Подключаемся к сессии: {session_path}")

    client = await create_client_from_session(session_path, api_id, api_hash)

    await subscription_telegram(client, url)


def register_handlers_checking_group_for_keywords():
    """Регистрирует обработчики для проверки группы на наличие ключевых слов."""
    router.message.register(checking_group_for_keywords, F.text == "Проверка группы на наличие ключевых слов")
