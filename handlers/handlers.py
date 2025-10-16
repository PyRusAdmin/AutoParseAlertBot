# -*- coding: utf-8 -*-
import os

from aiogram import F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from database.database import User, create_groups_model
from keyboards.keyboards import (get_lang_keyboard, main_menu_keyboard, settings_keyboard, back_keyboard,
                                 menu_launch_tracking_keyboard)
from locales.locales import get_text
from parsing.parser import filter_messages
from states.states import MyStates
from system.dispatcher import router


@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    user_tg = message.from_user

    # Создаём пользователя с language = "unset", если его нет
    user, created = User.get_or_create(
        user_id=user_tg.id,
        defaults={
            "username": user_tg.username,
            "first_name": user_tg.first_name,
            "last_name": user_tg.last_name,
            "language": "unset"  # ← ключевое: "unset" = язык не выбран
        }
    )
    if not created:
        # Обновляем профиль (на случай смены имени и т.п.)
        user.username = user_tg.username
        user.first_name = user_tg.first_name
        user.last_name = user_tg.last_name
        user.save()

    logger.info(
        f"Пользователь {user_tg.id} {user_tg.username} {user_tg.first_name} {user_tg.last_name} начал работу с ботом.")

    # Если язык ещё не выбран — просим выбрать
    if user.language == "unset":
        # Можно предложить язык по умолчанию из Telegram, но всё равно дать выбор
        await message.answer(
            "👋 Привет! Пожалуйста, выберите язык / Please choose your language:",
            reply_markup=get_lang_keyboard()
        )
    else:
        # Язык уже выбран — приветствуем
        text = get_text(user.language, "welcome_message")
        await message.answer(text, reply_markup=main_menu_keyboard())


@router.message(F.text.in_(["🇷🇺 Русский", "🇬🇧 English"]))
async def handle_language_selection(message: Message):
    """Выбор языка"""
    user_tg = message.from_user
    user = User.get(User.user_id == user_tg.id)

    if message.text == "🇷🇺 Русский":
        user.language = "ru"
        confirm = get_text("ru", "lang_selected")
    elif message.text == "🇬🇧 English":
        user.language = "en"
        confirm = get_text("en", "lang_selected")

    user.save()

    await message.answer(confirm, reply_markup=main_menu_keyboard())


@router.message(F.text == "Настройки")
async def handle_settings(message: Message):
    """Открытие меню настроек"""
    user_tg = message.from_user
    user = User.get(User.user_id == user_tg.id)

    await message.answer(
        get_text(user.language, "settings_message"),
        reply_markup=settings_keyboard()  # клавиатура выбора языка
    )


@router.message(F.text == "🔙 Назад")
async def handle_main_menu(message: Message):
    """Возврат в главное меню"""
    user_tg = message.from_user

    # Создаём пользователя с language = "unset", если его нет
    user, created = User.get_or_create(
        user_id=user_tg.id,
        defaults={
            "username": user_tg.username,
            "first_name": user_tg.first_name,
            "last_name": user_tg.last_name,
            "language": "unset"  # ← ключевое: "unset" = язык не выбран
        }
    )
    if not created:
        # Обновляем профиль (на случай смены имени и т.п.)
        user.username = user_tg.username
        user.first_name = user_tg.first_name
        user.last_name = user_tg.last_name
        user.save()

    # Если язык ещё не выбран — просим выбрать
    if user.language == "unset":
        # Можно предложить язык по умолчанию из Telegram, но всё равно дать выбор
        await message.answer(
            "👋 Привет! Пожалуйста, выберите язык / Please choose your language:",
            reply_markup=get_lang_keyboard()
        )
    else:
        # Язык уже выбран — приветствуем
        text = get_text(user.language, "welcome_message")
        await message.answer(text, reply_markup=main_menu_keyboard())


@router.message(F.text == "Подключить аккаунт")
async def handle_connect_account(message: Message):
    """Меню подключения аккаунта"""
    user_tg = message.from_user

    # Создаём пользователя с language = "unset", если его нет
    user, created = User.get_or_create(
        user_id=user_tg.id,
        defaults={
            "username": user_tg.username,
            "first_name": user_tg.first_name,
            "last_name": user_tg.last_name,
            "language": "unset"  # ← ключевое: "unset" = язык не выбран
        }
    )

    text = get_text(user.language, "connect_account")
    await message.answer(text, reply_markup=back_keyboard())


@router.message(F.document)
async def handle_account_file(message: Message):
    """Приём файла аккаунта и сохранение его в папку account"""
    user_tg = message.from_user
    document = message.document

    user_id = message.from_user.id
    logger.info(f"User {user_id} отправил аккаунт {document.file_name}")

    # Проверяем расширение файла
    if not document.file_name.endswith(".session"):
        await message.answer("⚠️ Пожалуйста, отправьте корректный файл сессии (.session).")
        return

    # Создаём папку, если её нет
    folder_path = os.path.join(os.getcwd(), f"accounts/{user_id}")
    os.makedirs(folder_path, exist_ok=True)

    # Путь сохранения
    file_path = os.path.join(folder_path, document.file_name)

    # Скачиваем файл
    file = await message.bot.get_file(document.file_id)
    await message.bot.download_file(file.file_path, file_path)

    await message.answer(f"✅ Файл {document.file_name} успешно загружен в папку account.")


@router.message(F.text == "Запуск отслеживания")
async def handle_launching_tracking(message: Message):
    """Запуск отслеживания"""
    user_tg = message.from_user
    user = User.get(User.user_id == user_tg.id)

    logger.info(
        f"Пользователь {user_tg.id} {user_tg.username} {user_tg.first_name} {user_tg.last_name} перешел в меню запуска парсинга.")

    await message.answer(
        get_text(user.language, "launching_tracking"),
        reply_markup=menu_launch_tracking_keyboard()  # клавиатура выбора языка
    )

    await  filter_messages(
        message=message,
        user_id=user_tg.id,
        user=user
    )


@router.message(F.text == "🔁 Обновить список")
async def handle_update_list(message: Message, state: FSMContext):
    """Запуск 🔁 Обновить список"""
    user_tg = message.from_user
    user = User.get(User.user_id == user_tg.id)

    logger.info(
        f"Пользователь {user_tg.id} {user_tg.username} {user_tg.first_name} {user_tg.last_name} перешел в меню 🔁 Обновить список")

    await message.answer(
        get_text(user.language, "update_list"),
        reply_markup=back_keyboard()  # клавиатура назад
    )
    await state.set_state(MyStates.waiting_username_group)


@router.message(MyStates.waiting_username_group)
async def handle_username_group(message: Message, state: FSMContext):
    """Обработка введённого имени группы в формате @username"""

    # username_group = message.text
    # user_tg = message.from_user
    username_group = message.text.strip()
    user_tg = message.from_user
    logger.info(f"Пользователь ввёл имя группы: {username_group}")

    # Создаём модель с таблицей, уникальной для конкретного пользователя
    Groups = create_groups_model(user_id=user_tg.id)  # Создаём таблицу для групп

    # Проверяем, существует ли таблица (если нет — создаём)
    if not Groups.table_exists():
        Groups.create_table()
        logger.info(f"Создана новая таблица для пользователя {user_tg.id}")

    # Добавляем запись в таблицу
    try:
        group = Groups.create(username_chat_channel=username_group)
        await message.answer(f"✅ Группа {username_group} добавлена в отслеживание.")
        logger.info(f"Группа {username_group} добавлена пользователем {user_tg.id}")
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            await message.answer("⚠️ Такая группа уже добавлена.")
        else:
            await message.answer("⚠️ Ошибка при добавлении группы.")
        logger.error(f"Ошибка при добавлении группы: {e}")


def register_greeting_handler():
    """Регистрация обработчиков"""
    router.message.register(command_start_handler)
    router.message.register(handle_language_selection)
    router.message.register(handle_settings)
    router.message.register(handle_main_menu)  # обработчик для кнопки "Назад"
    router.message.register(handle_connect_account)  # обработчик для кнопки "Подключить аккаунт"
    router.message.register(handle_account_file)  # обработчик приема аккаунта в формате .session
    router.message.register(handle_launching_tracking)  # обработчик запуска отслеживания

    router.message.register(handle_update_list)  # обработчик запуска 🔁 Обновить список
