# -*- coding: utf-8 -*-
import os

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger  # https://github.com/Delgan/loguru

from database.database import User
from keyboards.user.keyboards import back_keyboard
from locales.locales import get_text
from system.dispatcher import router


@router.message(F.text == "🔐 Подключить аккаунт")
async def handle_connect_account(message: Message, state: FSMContext):
    """
    Обработчик команды "🔐 Подключить аккаунт".

    Очищает текущее состояние FSM, регистрирует пользователя в базе данных (если его ещё нет)
    с языком по умолчанию "unset", и отправляет пользователю сообщение с приглашением
    🔐 Подключить аккаунт через отправку .session-файла.

    :param message: (Message) Объект входящего сообщения от пользователя.
    :param state: (FSMContext) Контекст машины состояний, используется для сброса текущего состояния.
    :return: None
    """
    await state.clear()  # Завершаем текущее состояние машины состояния
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
async def handle_account_file(message: Message, state: FSMContext):
    """
    Обработчик приёма файла сессии (.session) от пользователя для подключения аккаунта Telegram.

    Функция выполняет следующие действия:
    1. Сбрасывает текущее состояние FSM.
    2. Проверяет, что присланный файл имеет расширение .session.
    3. Создаёт папку пользователя в директории 'accounts/' если её нет.
    4. Удаляет старые файлы сессий (.session и .session-journal) в папке пользователя.
    5. Скачивает и сохраняет новый .session-файл.
    6. Уведомляет пользователя об успешной загрузке (и удалении старых файлов, если было).

    - Принимаются только файлы с расширением '.session'.
    - Старые сессии удаляются для предотвращения конфликтов.
    - Файлы хранятся по пути 'accounts/{user_id}/'.
    - Используется бот API для скачивания файла.

    :param message: (Message) Входящее сообщение с документом от пользователя.
    :param state: (FSMContext) Контекст машины состояний, используется для сброса состояния.
    :return: None
    """
    await state.clear()  # Завершаем текущее состояние машины состояния
    user_tg = message.from_user
    document = message.document
    user_id = user_tg.id
    logger.info(f"User {user_id} отправил аккаунт {document.file_name}")

    # Проверяем расширение файла
    if not document.file_name.endswith(".session"):
        await message.answer("⚠️ Пожалуйста, отправьте корректный файл сессии (.session).")
        return

    # Папка пользователя
    user_folder = os.path.join(os.getcwd(), f"accounts/{user_id}")
    os.makedirs(user_folder, exist_ok=True)

    # Полный путь к новому файлу
    new_file_path = os.path.join(user_folder, document.file_name)

    # 🧹 Удаляем старые файлы .session и .session-journal
    deleted_files = []
    for file_name in os.listdir(user_folder):
        if file_name.endswith(".session") or file_name.endswith(".session-journal"):
            full_path = os.path.join(user_folder, file_name)
            try:
                os.remove(full_path)
                deleted_files.append(file_name)
            except Exception as e:
                logger.error(f"Ошибка при удалении {file_name}: {e}")

    if deleted_files:
        logger.info(f"Удалены старые файлы: {', '.join(deleted_files)}")

    # Скачиваем новый файл
    file = await message.bot.get_file(document.file_id)
    await message.bot.download_file(file.file_path, new_file_path)

    # Ответ пользователю
    msg = f"✅ Аккаунт {document.file_name} успешно загружен."
    if deleted_files:
        msg += f"\n♻️ Старые файлы ({', '.join(deleted_files)}) были удалены. Аккаунт обновлен"
    await message.answer(msg)


def register_connect_account_handler():
    """
    Регистрирует обработчики для подключения аккаунта.

    Добавляет в маршрутизатор (router) два обработчика:
        1. handle_connect_account — для обработки нажатия кнопки "🔐 Подключить аккаунт".
        2. handle_account_file — для приёма файла сессии (.session) от пользователя.

    Обработчики реагируют на текстовые сообщения и документы соответственно.
    """
    router.message.register(handle_connect_account)  # обработчик для кнопки "🔐 Подключить аккаунт"
    router.message.register(handle_account_file)  # обработчик приема аккаунта в формате .session
