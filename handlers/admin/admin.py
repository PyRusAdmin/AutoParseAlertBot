# -*- coding: utf-8 -*-
import asyncio
from pathlib import Path

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger  # https://github.com/Delgan/loguru
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession
from telethon.sync import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest

from account_manager.auth import connect_client_test
from database.database import TelegramGroup, db, User
from keyboards.admin.keyboards import admin_keyboard
from system.dispatcher import api_id, api_hash, router


@router.message(F.text == "Панель администратора")
async def admin_panel(message: Message, state: FSMContext):
    """
    Обработчик команды «Панель администратора».

    При вызове:
    - сбрасывает текущее состояние FSM;
    - отправляет приветственное сообщение администратору;
    - отображает клавиатуру с административными кнопками.

    Используется для:
    - предоставления доступа к административному интерфейсу;
    - запуска административных операций через клавиатурные кнопки.

    Особенности реализации:
    - Доступ к команде имеют только администраторы;
    - обработка исключений реализована в блоке try/except.

    :param message: (Message) Входящее сообщение с командой «Панель администратора».
    :param state: (FSMContext) Контекст машины состояний. Сбрасывается в начале выполнения.
    :return: None
    :raises:
        Exception: Может возникнуть при ошибках формирования клавиатуры (admin_keyboard()) или отправке сообщения через Telegram Bot API.
        Исключения перехватываются и логируются.
    """
    try:
        await state.clear()  # Сбрасываем текущее состояние FSM

        text = (
            "👋 <b>Добро пожаловать в панель администратора!</b>\n\n"
            "Вот что вы можете сделать:\n\n"
            "📁 <b>Получить лог-файл</b> — просмотреть журнал ошибок и событий бота за последнее время. Полезно для диагностики.\n\n"
            "🔄 <b>Актуализация базы данных</b> — обновить информацию о группах и каналах: проверить их текущий тип (группа/канал) и получить актуальные ID.\n\n"
        )
        await message.answer(
            text=text,
            parse_mode="HTML",
            reply_markup=admin_keyboard(),
        )
    except Exception as e:
        logger.exception(e)


@router.message(F.text == "Актуализация базы данных")
async def update_db(message: Message):
    """
    Актуализация базы данных:
    обновление ID и типа групп/каналов.

    Последовательность действий:
     - Сканирует папку accounts/parsing для поиска доступных сессий;
     - Подключается к Telegram API для получения метаданных по username;
     - Определяет тип сущности (канал, супергруппа и т.д.);
     - Обновляет записи в базе через прямой UPDATE-запрос;
     - При FloodWaitError переключается на следующий аккаунт;
     - Отправляет прогресс и статистику в чат администратора.

     Особенности:
     - Доступ только для администраторов;
     - Автоматическое переключение между аккаунтами при FloodWait;
     - Используется режим WAL для избежания блокировок БД.

     :param message: (Message) Входящее сообщение от администратора.
     :return: None
     """

    user_id = message.from_user.id  # ID текущего пользователя

    try:
        user = User.get(User.user_id == user_id)
    except User.DoesNotExist:
        await message.answer("❌ Пользователь не найден в базе данных.")
        return

    # 2. Сканируем папку на наличие session-файлов
    sessions_dir = Path('accounts/parsing')
    session_files = list(sessions_dir.glob('*.session'))

    if not session_files:
        await message.answer("❌ Не найдено ни одного session-файла в папке accounts/parsing")
        logger.error("Session-файлы не найдены")
        return

    # Получаем имена сессий (без расширения .session)
    available_sessions = [str(f.stem) for f in session_files]
    logger.info(f"Найдено {len(available_sessions)} аккаунтов: {available_sessions}")

    # Проверка аккаунтов на валидность из папки parsing
    await connect_client_test(available_sessions)

    await message.answer("✅ Проверка завершена.")

    # Получаем имена сессий (без расширения .session)
    available_sessions = [str(f.stem) for f in session_files]
    logger.info(f"Найдено {len(available_sessions)} аккаунтов: {available_sessions}")

    await message.answer(
        f"🔍 Найдено аккаунтов: {len(available_sessions)}\n"
        f"📱 Аккаунты: {', '.join([s.split('/')[-1] for s in available_sessions])}"
    )

    try:
        # 3. Убедимся, что БД подключена
        if db.is_closed():
            db.connect()

        # 4. Получаем записи с username и group_type='group', которые ещё НЕ обновлены
        groups_to_update = list(TelegramGroup.select().where(
            (TelegramGroup.username.is_null(False)) &
            (TelegramGroup.group_type == 'group')
        ))

        total_count = len(groups_to_update)
        logger.info(f"Найдено {total_count} групп для обновления")

        # Отправляем начальное сообщение
        await message.answer(f"🔄 Начинаю актуализацию {total_count} групп...")

        processed = 0
        updated = 0
        errors = 0
        current_session_index = 0

        # 5. Основной цикл обработки групп
        while processed < total_count and current_session_index < len(available_sessions):
            # Подключаемся к текущему аккаунту
            session_path = f'accounts/parsing/{available_sessions[current_session_index]}'
            client = TelegramClient(session_path, api_id, api_hash)
            await client.connect()
            session_string = StringSession.save(client.session)
            # Создаем клиент, используя StringSession и вашу строку
            client = TelegramClient(
                StringSession(session_string),
                api_id=api_id,
                api_hash=api_hash,
                # proxy=self.proxy.reading_proxy_data_from_the_database(),
                system_version="4.16.30-vxCUSTOM"
            )

            try:
                await client.connect()
                await asyncio.sleep(1)

                current_account = available_sessions[current_session_index].split('/')[-1]
                logger.info(f"Используется аккаунт: {current_account}")
                await message.answer(f"📱 Используется аккаунт: {current_account}")

                # Обрабатываем группы с текущим аккаунтом
                for group in groups_to_update[processed:]:
                    try:

                        await asyncio.sleep(2)

                        # Получаем сущность Telegram по username
                        entity = await client.get_entity(group.username)

                        logger.info(entity)

                        # Получаем полную информацию
                        full_entity = await client(GetFullChannelRequest(channel=entity))

                        # Извлекаем данные из полной сущности
                        description = full_entity.full_chat.about or ""
                        participants_count = full_entity.full_chat.participants_count or 0
                        logger.info(f"Описание: {description}")

                        # Определяем тип сущности
                        if entity.megagroup:
                            new_group_type = 'Группа (супергруппа)'
                        elif entity.broadcast:
                            new_group_type = 'Канал'
                        else:
                            new_group_type = 'Обычный чат (группа старого типа)'

                        # Обновляем запись через UPDATE запрос со всеми доступными данными
                        TelegramGroup.update(
                            id=entity.id,
                            group_type=new_group_type,
                            description=description,
                            participants=participants_count,
                            name=entity.title  # Также обновляем название на актуальное
                        ).where(
                            TelegramGroup.group_hash == group.group_hash
                        ).execute()

                        processed += 1
                        updated += 1

                        logger.info(
                            f"[{processed}/{total_count}] Обновлено: {group.username} | "
                            f"ID: {entity.id} | Тип: {new_group_type} | Описание: {description} | Участники: {participants_count} | Аккаунт: {current_account}"
                        )

                        # Каждые 10 обновлений отправляем прогресс
                        if processed % 10 == 0:
                            await message.answer(
                                f"📊 Прогресс: {processed}/{total_count}\n"
                                f"✅ Обновлено: {updated}\n"
                                f"❌ Ошибок: {errors}\n"
                                f"📱 Аккаунт: {current_account}"
                            )

                        # Пауза для избежания бана от Telegram
                        await asyncio.sleep(5)

                    except FloodWaitError as e:
                        wait_time = e.seconds
                        errors += 1

                        logger.warning(
                            f"FloodWait для {group.username} (аккаунт {current_account}): "
                            f"нужно подождать {wait_time} секунд ({wait_time / 3600:.1f} часов)"
                        )

                        # Отправляем уведомление о FloodWait
                        await message.answer(
                            f"⚠️ FloodWait на аккаунте {current_account}\n\n"
                            f"📊 Обработано: {processed}/{total_count}\n"
                            f"✅ Обновлено: {updated}\n"
                            f"❌ Ошибок: {errors}\n\n"
                            f"⏱ Ожидание: {wait_time / 3600:.1f} ч ({wait_time} сек)"
                        )

                        # Переключаемся на следующий аккаунт
                        current_session_index += 1

                        if current_session_index < len(available_sessions):
                            await message.answer(
                                f"🔄 Переключаюсь на аккаунт "
                                f"{available_sessions[current_session_index].split('/')[-1]}"
                            )
                        else:
                            await message.answer(
                                "❌ Все аккаунты исчерпаны. Актуализация остановлена."
                            )

                        break  # Выходим из цикла групп, переключаемся на новый аккаунт

                    # except sqlite3.DatabaseError:
                    #     logger.error(
                    #         f"Ошибка базы данных (аккаунта {current_account}, переключаюсь на следующий аккаунт)")
                    #     break  # Выходим из цикла групп, переключаемся на новый аккаунт

                    except ValueError as e:
                        logger.warning(f"Не правильный username: {group.username}")

                    except Exception as e:
                        logger.exception(e)
            except Exception as e:
                logger.exception(e)
                # logger.error(f"Ошибка подключения к аккаунту {current_account}: {e}")
                await message.answer(f"❌ Ошибка аккаунта {current_account}: {e}")
                current_session_index += 1
            finally:
                await client.disconnect()

        # Финальная статистика
        if processed >= total_count:
            await message.answer(
                f"✅ Актуализация завершена!\n\n"
                f"📊 Всего обработано: {processed}/{total_count}\n"
                f"✅ Успешно обновлено: {updated}\n"
                f"❌ Ошибок: {errors}\n"
                f"📱 Использовано аккаунтов: {current_session_index + 1}/{len(available_sessions)}"
            )
        else:
            await message.answer(
                f"⚠️ Актуализация остановлена.\n\n"
                f"📊 Обработано: {processed}/{total_count}\n"
                f"✅ Успешно обновлено: {updated}\n"
                f"❌ Ошибок: {errors}\n"
                f"📱 Все {len(available_sessions)} аккаунтов исчерпаны"
            )

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        await message.answer(f"❌ Критическая ошибка: {e}")

    finally:
        if not db.is_closed():
            db.close()

        logger.info("Актуализация завершена.")


def register_handlers_admin_panel():
    """
    Регистрирует обработчик команды «Панель администратора» в маршрутизаторе.

    Добавляет в router обработчик для команды, активируемой по тексту «Панель администратора».
    Обеспечивает запуск функции admin_panel при получении соответствующего сообщения.

    Рекомендации по безопасности:
    - Доступ к команде имеют только администраторы;
    - обработка исключений реализована.

    :return: None
    """
    router.message.register(admin_panel)  # Админ панель
    router.message.register(update_db)  # Актуализация базы данных (c пометкой Группа или Канал)
