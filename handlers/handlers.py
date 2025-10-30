# -*- coding: utf-8 -*-
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
async def handle_start_command(message: Message) -> None:
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
        confirmation_text = get_text("ru", "lang_selected")
    elif message.text == "🇬🇧 English":
        user.language = "en"
        confirmation_text = get_text("en", "lang_selected")

    user.save()

    await message.answer(confirmation_text, reply_markup=main_menu_keyboard())


@router.message(F.text == "⚙ Настройки")
async def handle_settings_menu(message: Message):
    """Открытие меню настроек"""
    user_tg = message.from_user
    user = User.get(User.user_id == user_tg.id)

    await message.answer(
        get_text(user.language, "settings_message"),
        reply_markup=settings_keyboard()  # клавиатура выбора языка
    )


@router.message(F.text == "🔙 Назад")
async def handle_back_to_main_menu(message: Message):
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


@router.message(F.text == "⏯ Запуск отслеживания")
async def handle_start_tracking(message: Message):
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
async def handle_refresh_groups_list(message: Message, state: FSMContext):
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
async def handle_group_usernames_input(message: Message, state: FSMContext):
    """Обработка введённого имени группы в формате @username"""

    # username_group = message.text
    # user_tg = message.from_user
    raw_text = message.text.strip()
    user_tg = message.from_user
    logger.info(f"Пользователь ввёл имя группы: {raw_text}")

    # Разбиваем сообщение по пробелам и переносам строк
    usernames = [u.strip() for u in raw_text.replace("\n", " ").split() if u.strip()]

    if not usernames:
        await message.answer("⚠️ Вы не указали ни одной группы.")
        await state.clear()
        return

    # Создаём модель с таблицей, уникальной для конкретного пользователя
    Groups = create_groups_model(user_id=user_tg.id)  # Создаём таблицу для групп

    # Проверяем, существует ли таблица (если нет — создаём)
    if not Groups.table_exists():
        Groups.create_table()
        logger.info(f"Создана новая таблица для пользователя {user_tg.id}")

    added = []
    skipped = []
    errors = []

    # Добавляем каждую группу по очереди
    for username in usernames:
        try:
            Groups.create(username_chat_channel=username, user_keyword=None)
            added.append(username)
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                skipped.append(username)
            else:
                errors.append((username, str(e)))
                logger.error(f"Ошибка при добавлении {username}: {e}")

    # Формируем итоговое сообщение
    response = []
    if added:
        response.append("✅ Добавлены группы:\n" + "\n".join(added))
    if skipped:
        response.append("⚠️ Уже были добавлены:\n" + "\n".join(skipped))
    if errors:
        response.append("❌ Ошибки при добавлении:\n" + "\n".join(f"{u}: {e}" for u, e in errors))

    await message.answer("\n\n".join(response))
    await state.clear()


def register_greeting_handlers():
    """Регистрация обработчиков"""
    router.message.register(handle_start_command)
    router.message.register(handle_language_selection)
    router.message.register(handle_settings_menu)
    router.message.register(handle_back_to_main_menu)  # обработчик для кнопки "Назад"
    router.message.register(handle_start_tracking)  # обработчик запуска отслеживания
    router.message.register(handle_refresh_groups_list)  # обработчик запуска 🔁 Обновить список
