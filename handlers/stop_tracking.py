# -*- coding: utf-8 -*-
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from database.database import User
from keyboards.keyboards import menu_launch_tracking_keyboard
from parsing.parser import stop_tracking
from system.dispatcher import router


@router.message(F.text == "Остановить отслеживание")
async def handle_stop_tracking(message: Message, state: FSMContext):
    """
    Обработчик команды "Остановить отслеживание".

    Очищает состояние FSM, получает данные пользователя и вызывает функцию `stop_tracking`
    для прекращения фонового парсинга сообщений в отслеживаемых группах.
    После остановки отправляет подтверждение пользователю.

    Args:
        message (Message): Входящее сообщение от пользователя.
        state (FSMContext): Контекст машины состояний, сбрасывается перед остановкой.

    Returns:
        None

    Raises:
        Exception: Передаётся в `stop_tracking`, где обрабатывается.

    Notes:
        - Команда доступна только во время активного отслеживания.
        - Использует глобальный механизм управления задачами в `parsing/parser.py`.
    """
    await state.clear()  # Завершаем текущее состояние машины состояния
    user_tg = message.from_user
    user = User.get(User.user_id == user_tg.id)

    logger.info(
        f"Пользователь {user_tg.id} {user_tg.username} {user_tg.first_name} {user_tg.last_name} нажал кнопку остановки отслеживания")

    await stop_tracking(user_id=user_tg.id, message=message, user=user)

    await message.answer(
        "Отслеживание отменено",
        reply_markup=menu_launch_tracking_keyboard()  # клавиатура выбора языка
    )


def register_stop_tracking_handler():
    """
    Регистрирует обработчик для остановки отслеживания.

    Добавляет в маршрутизатор (router) обработчик команды "Остановить отслеживание".
    Позволяет пользователю вручную завершить процесс парсинга сообщений.

    Вызывается при инициализации бота в `main.py`.

    Returns:
        None
    """
    router.message.register(handle_stop_tracking)  # Регистрация обработчика
