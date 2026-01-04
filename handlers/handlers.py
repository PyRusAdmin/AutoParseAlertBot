# -*- coding: utf-8 -*-
import os

from aiogram import F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from loguru import logger  # https://github.com/Delgan/loguru
from telethon.tl.types import Message

from account_manager.session import find_session_file
from database.database import (
    User, create_groups_model, getting_number_records_database, get_session_count,
    get_target_group_count, get_tracked_channels_count, get_keywords_count
)
from keyboards.keyboards import (
    get_lang_keyboard, main_menu_keyboard, settings_keyboard, back_keyboard, menu_launch_tracking_keyboard,
    connect_keyboard_account
)
from locales.locales import get_text
from account_manager.parser import filter_messages
from states.states import MyStates
from system.dispatcher import router


@router.message(CommandStart())
async def handle_start_command(message: Message, state: FSMContext) -> None:
    """
    Обработчик команды /start.

    Инициализирует пользователя в базе данных при первом запуске, обновляет его профиль
    при последующих запусках и приветствует пользователя. Если язык не выбран,
    предлагает выбрать язык интерфейса.

    Является точкой входа в бота.

    - Создаёт или получает запись в таблице `User`.
    - При повторном запуске обновляет имя и username пользователя.
    - Использует ключ "unset" для обозначения незаданного языка.

    :param message: (Message) Входящее сообщение от пользователя с командой /start.
    :param state: (FSMContext) Контекст машины состояний, сбрасывается при старте.
    :return: None
    """
    await state.clear()  # Завершаем текущее состояние машины состояния
    user_tg = message.from_user

    user = get_or_create_user(
        user_tg
    )  # Получаем или создаём пользователя в базе данных, синхронизируя его данные с Telegram

    # Если язык ещё не выбран — просим выбрать
    if user.language == "unset":
        # Можно предложить язык по умолчанию из Telegram, но всё равно дать выбор
        await message.answer(
            "👋 Привет! Пожалуйста, выберите язык / Please choose your language:",
            reply_markup=get_lang_keyboard()
        )
    else:
        text = generate_welcome_message(user_language=user.language, user_tg_id=user_tg.id)
        await message.answer(text=text, reply_markup=main_menu_keyboard(), parse_mode="HTML")


@router.message(F.text == "🔙 Назад")
async def handle_back_to_main_menu(message: Message, state: FSMContext):
    """
    Обработчик команды "🔙 Назад".

    Очищает состояние FSM и возвращает пользователя в главное меню.
    Логика аналогична обработчику /start: проверяет наличие пользователя,
    обновляет профиль и показывает главное меню или запрос языка.

    Используется для навигации из подменю (настройки, добавление групп и т.д.) в основное меню.

    - Повторно использует логику инициализации из handle_start_command.
    - Не сохраняет состояние после возврата.

    :param message: (Message) Входящее сообщение от пользователя.
    :param state: (FSMContext) Контекст машины состояний, сбрасывается перед возвратом.
    :return: None
    """
    await state.clear()  # Завершаем текущее состояние машины состояния
    user_tg = message.from_user

    user = get_or_create_user(
        user_tg
    )  # Получаем или создаём пользователя в базе данных, синхронизируя его данные с Telegram

    # Если язык ещё не выбран — просим выбрать
    if user.language == "unset":
        # Можно предложить язык по умолчанию из Telegram, но всё равно дать выбор
        await message.answer(
            "👋 Привет! Пожалуйста, выберите язык / Please choose your language:",
            reply_markup=get_lang_keyboard()
        )
    else:
        # Язык уже выбран — приветствуем
        text = generate_welcome_message(user_language=user.language, user_tg_id=user_tg.id)
        await message.answer(text=text, reply_markup=main_menu_keyboard(), parse_mode="HTML")


def generate_welcome_message(user_language: str, user_tg_id: int) -> str:
    """
    Генерирует приветственное сообщение для пользователя с подставленными данными.

    Собирает информацию о:
    - версии бота
    - общем количестве найденных групп в базе
    - количестве подключённых пользователем сессий (аккаунтов)
    - количестве подключённых технических групп (для пересылки)
    - количестве отслеживаемых каналов
    - количестве сохранённых ключевых слов

    :param user_language: Язык пользователя (например, 'ru', 'en') для выбора шаблона.
    :param user_tg_id: Telegram ID пользователя для получения его данных.
    :return: Готовое текстовое сообщение для отправки.
    """
    template = get_text(user_language, "welcome_message_template")
    version = "0.0.5"
    groups_count = getting_number_records_database()  # Общее число найденных групп
    count = get_session_count(user_id=user_tg_id)  # Сессии пользователя
    group_count = get_target_group_count(user_id=user_tg_id)  # Группы для пересылки
    get_groups = get_tracked_channels_count(user_id=user_tg_id)  # Отслеживаемые каналы
    keywords_count = get_keywords_count(user_id=user_tg_id)  # Ключевые слова

    return template.format(
        version=version,
        groups_count=groups_count,
        count=count,
        group_count=group_count,
        get_groups=get_groups,
        keywords_count=keywords_count
    )


def get_or_create_user(user_tg):
    """
    Получает существующего пользователя из базы данных или создаёт нового, если он не существует.

    При создании нового пользователя устанавливает язык интерфейса в "unset" (не выбран).
    При наличии существующего пользователя обновляет его профиль (username, имя, фамилия),
    чтобы синхронизировать данные с актуальной информацией из Telegram.

    :param user_tg: (User) Объект пользователя из Telegram (aiogram.types.User).
    :return: (User) Экземпляр модели пользователя из базы данных.
    """
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

    return user


@router.message(F.text.in_(["🇷🇺 Русский", "🇬🇧 English"]))
async def handle_language_selection(message: Message, state: FSMContext):
    """
    Обработчик выбора языка пользователем.

    Обрабатывает нажатие на кнопки "🇷🇺 Русский" или "🇬🇧 English".
    Сохраняет выбранный язык в базе данных и отображает главное меню.

    Используется при первом запуске бота, когда язык установлен в "unset".

    :param message: (Message) Входящее сообщение с выбранным языком.
    :param state: (FSMContext) Контекст машины состояний, сбрасывается перед обработкой.
    :return: None

    Raises:
        Exception: Не ожидается, но возможна ошибка записи в БД.

    Notes:
        - Выбранный язык используется для локализации всех последующих сообщений.
        - После выбора пользователь переходит в основное меню.
    """
    await state.clear()  # Завершаем текущее состояние машины состояния
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
async def handle_settings_menu(message: Message, state: FSMContext):
    """
    Обработчик команды "⚙ Настройки".

    Отображает меню настроек с возможностью смены языка интерфейса.
    Не требует предварительной настройки аккаунта.

    :param message: (Message) Входящее сообщение от пользователя.
    :param state: (FSMContext) Контекст машины состояний, не используется напрямую.
    :return: None

    Notes:
        - Текст меню локализован в зависимости от языка пользователя.
        - Клавиатура включает кнопку для смены языка.
    """

    user_tg = message.from_user
    user = User.get(User.user_id == user_tg.id)

    await message.answer(
        get_text(user.language, "settings_message"),
        reply_markup=settings_keyboard()  # клавиатура выбора языка
    )


@router.message(F.text == "⏯ Запуск отслеживания")
async def handle_start_tracking(message: Message, state: FSMContext):
    """
    Обработчик команды "⏯ Запуск отслеживания".

    Проверяет наличие подключенного Telegram-аккаунта (.session файл) у пользователя.
    Если аккаунт найден, запускает процесс фильтрации сообщений с помощью `filter_messages`.
    Если аккаунт не найден, уведомляет пользователя и предлагает 🔐 Подключить аккаунт.

    :param message: (Message) Входящее сообщение от пользователя.
    :param state: (FSMContext) Контекст машины состояний, не используется напрямую.
    :return: None

    Raises:
        Exception: Передаётся в `filter_messages`, где обрабатывается.

    Notes:
        - Путь к сессии ищется в папке `accounts/{user_id}/`.
        - Используется первое найденное .session-расширение.
        - Сообщение о запуске отправляется до начала парсинга.
    """
    try:
        user_tg = message.from_user  # Получаем данные пользователя из Telegram
        user_id = user_tg.id  # Получаем ID пользователя
        user = User.get(User.user_id == user_tg.id)

        logger.info(
            f"Пользователь {user_tg.id} {user_tg.username} {user_tg.first_name} {user_tg.last_name} перешел в меню запуска парсинга.")

        # === Папка, где хранятся сессии ===
        session_dir = os.path.join("accounts", str(user_id))
        os.makedirs(session_dir, exist_ok=True)

        session_path = await find_session_file(session_dir, user, message)  # <-- ✅ ищем файл сессии

        logger.info(session_path)
        if session_path is None:
            logger.warning("Нет подключенного аккаунта")

            await message.answer(
                text="Нет подключенного аккаунта. Подключите аккаунт.",
                reply_markup=connect_keyboard_account()
            )
            return  # Правильный способ прервать выполнение обработчика

            # Если у пользователя подключенный аккаунт
        await message.answer(
            get_text(user.language, "launching_tracking"),
            reply_markup=menu_launch_tracking_keyboard()  # клавиатура выбора языка
        )

        await filter_messages(
            message=message,  # сообщение
            user_id=user_id,  # ID пользователя
            user=user,  # модель пользователя
            session_path=session_path  # путь к сессии
        )
    except Exception as e:
        logger.exception(e)


@router.message(F.text == "🔁 Обновить список")
async def handle_refresh_groups_list(message: Message, state: FSMContext):
    """
    Обработчик команды "🔁 Обновить список".

    Позволяет пользователю добавить новые группы или каналы для отслеживания.
    Отправляет приглашение ввести username-ы и переводит пользователя в состояние ожидания ввода.

    :param message: (Message) Входящее сообщение от пользователя.
    :param state: (FSMContext) Контекст машины состояний, используется для установки состояния.
    :return: None

    Notes:
        - Принимает несколько username за раз, разделённые пробелами или переносами строк.
        - После отправки сообщения пользователь должен ввести @username-ы.
        - Используется состояние `MyStates.waiting_username_group`.
    """
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
    """
    Обработчик ввода списка групп/каналов пользователем.

    Принимает строку с одним или несколькими @username-ами, разделёнными пробелами или переносами строк,
    и добавляет их в персональную таблицу пользователя. Поддерживает массовую загрузку.
    Обрабатывает дубликаты и ошибки, формирует отчёт.

    :param message: (Message) Входящее сообщение с @username-ами.
    :param state: (FSMContext) Контекст машины состояний, сбрасывается после обработки.
    :return: None

    Raises:
        Exception: Перехватывается локально при ошибках добавления (например, нарушение уникальности).

    Notes:
        - Используется динамическая модель `create_groups_model` для изоляции данных.
        - Пустые строки и дубликаты пропускаются.
        - После обработки состояние сбрасывается и пользователь возвращается в меню.
    """

    # username_group = message.text
    # user_tg = message.from_user
    raw_text = message.text.strip()
    user_tg = message.from_user
    logger.info(f"Пользователь ввёл имя группы: {raw_text}")

    # Разбиваем сообщение по пробелам и переносам строк
    usernames = [u.strip() for u in raw_text.replace("\n", " ").split() if u.strip()]

    if not usernames:
        await message.answer("⚠️ Вы не указали ни одной группы.")
        await state.clear()  # Завершаем текущее состояние машины состояния
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
    await state.clear()  # Завершаем текущее состояние машины состояния


def register_greeting_handlers():
    """
    Регистрирует основные обработчики команд и навигации бота.

    Добавляет в маршрутизатор (router) обработчики для:
        - Команды /start (приветствие и инициализация)
        - Выбора языка интерфейса
        - Открытия меню настроек
        - Возврата в главное меню (кнопка "Назад")
        - Запуска отслеживания сообщений
        - Обновления списка отслеживаемых групп

    Эти обработчики формируют основную логику взаимодействия пользователя с ботом.

    Вызывается при инициализации бота в `main.py`.

    Returns:
        None
    """
    router.message.register(handle_start_command)  # обработчик команды /start
    router.message.register(handle_language_selection)  # обработчик выбора языка
    router.message.register(handle_settings_menu)  # обработчик меню настроек
    router.message.register(handle_back_to_main_menu)  # обработчик для кнопки "Назад"
    router.message.register(handle_start_tracking)  # обработчик запуска отслеживания
    router.message.register(handle_refresh_groups_list)  # обработчик запуска 🔁 Обновить список
    router.message.register(handle_group_usernames_input)  # обработчик ввода username групп
