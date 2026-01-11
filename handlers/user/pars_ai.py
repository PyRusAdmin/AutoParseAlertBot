# -*- coding: utf-8 -*-
import csv
import hashlib
import io
import os
import re
from datetime import datetime

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile
from aiogram.types import Message, FSInputFile
from loguru import logger  # https://github.com/Delgan/loguru

from ai.ai import get_groq_response, search_groups_in_telegram
from database.database import User, TelegramGroup
from keyboards.keyboards import back_keyboard, search_group_ai
from locales.locales import get_text
from states.states import MyStates
from system.dispatcher import router


def clean_group_name(name):
    """
    Очищает название группы от начальных номеров, символов и лишних пробелов.

    Удаляет с начала строки последовательности из цифр, точек, тире, звёздочек,
    скобок и пробелов, которые часто присутствуют в перечисленных списках.

    Например, преобразует "1. Группа разработчиков" в "Группа разработчиков".

    :param name : (str) Исходное название группы.
    :return str: Очищенное название группы без префиксов.
    """
    cleaned = re.sub(r'^[\d\.\-\*\s\)\(\[\]]+', '', name).strip()
    return cleaned


def generate_group_hash(username=None, name=None, link=None):
    """
    Генерирует MD5-хеш для уникальной идентификации группы в базе данных.

    Использует один из трёх параметров: username, link или name (в порядке приоритета)
    для создания хеша, который служит первичным ключом в таблице `TelegramGroup`.

    Приоритет: username > link > name. Используется первый непустой параметр.

    :param username : (str, optional) Юзернейм группы (например, "@python_chat").
    :param name : (str, optional) Название группы.
    :param link : (str, optional) Прямая ссылка на группу (например, "https://t.me/python_chat").
    :return str: 32-символьная hex-строка MD5-хеша.
    """
    if username:
        return hashlib.md5(username.encode()).hexdigest()
    elif link:
        return hashlib.md5(link.encode()).hexdigest()
    else:
        return hashlib.md5(name.encode()).hexdigest()


def determine_group_type(group_data):
    """
    Определяет тип Telegram-чата на основе его данных.

    Анализирует словарь с информацией о группе и возвращает строку с типом.

    Используется при сохранении группы в базу данных.

    - 'channel': если есть флаг is_channel.
    - 'group': если есть username (предполагает, что это группа).
    - 'link': во всех остальных случаях.

    :param group_data : (dict) Словарь с данными о группе, полученный из поиска.
    :return str: Тип чата — 'channel', 'group' или 'link'.
    """
    if 'is_channel' in group_data and group_data['is_channel']:
        return 'channel'
    elif 'username' in group_data and group_data['username']:
        return 'group'
    else:
        return 'link'


def save_group_to_db(group_data, category=None):
    """
    Сохраняет или обновляет информацию о группе в централизованной базе данных.

    Использует хеш для проверки существования группы. При наличии обновляет поля,
    при отсутствии — создаёт новую запись. Поля 'participants' и 'description'
    обновляются при каждом нахождении группы.

    Функция является частью механизма deduplication и предотвращает дублирование записей.

    :param group_data : (dict) Словарь с информацией о группе (название, username, участники и т.д.).
    :param category : (str, optional) Категория, под которой был выполнен поиск (используется как тег).
    :return TelegramGroup or None: Экземпляр сохранённой модели или None при ошибке.
    :raise Exception: Логируется при ошибках работы с БД (например, нарушение ограничений).
    """
    try:
        group_hash = generate_group_hash(
            username=group_data.get('username'),
            name=group_data.get('name'),
            link=group_data.get('link')
        )

        group_type = determine_group_type(group_data)

        # Проверяем, существует ли уже такая группа
        existing = TelegramGroup.get_or_none(TelegramGroup.group_hash == group_hash)

        if existing:
            # Обновляем данные
            existing.participants = group_data.get('participants', 0)
            existing.description = group_data.get('description')
            existing.save()
            logger.info(f"Обновлена группа: {group_data['name']}")
            return existing
        else:
            # Создаём новую запись
            new_group = TelegramGroup.create(
                group_hash=group_hash,
                name=group_data.get('name', 'Без названия'),
                username=group_data.get('username'),
                description=group_data.get('description'),
                participants=group_data.get('participants', 0),
                category=category,
                group_type=group_type,
                link=group_data.get('link', ''),
                date_added=datetime.now()
            )
            logger.info(f"Добавлена новая группа: {group_data['name']}")
            return new_group

    except Exception as e:
        logger.error(f"Ошибка при сохранении группы: {e}")
        return None


def create_csv_file(groups):
    """
    Создаёт байтовый CSV-файл с данными о найденных группах для отправки пользователю.

    Использует точку с запятой как разделитель для совместимости с Excel и добавляет BOM
    для корректного отображения кириллицы. Все поля экранированы.

    Файл содержит колонки: ID (Hash), Название, Username, Описание, Участников,
    Категория, Тип, Ссылка, Дата добавления.
    Username приводится к формату '@username'.

    :param groups : (list[TelegramGroup]) Список экземпляров модели TelegramGroup.
    :return bytes: Содержимое CSV-файла в кодировке UTF-8 с BOM.
    """
    output = io.StringIO()

    # Создаём CSV writer с разделителем точка с запятой для лучшей совместимости с Excel
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)

    # Заголовки
    writer.writerow([
        'ID (Hash)',
        'Название',
        'Username',
        'Описание',
        'Участников',
        'Категория',
        'Тип',
        'Ссылка',
        'Дата добавления'
    ])

    # Данные
    for group in groups:
        # Очищаем username от лишних символов
        username = group.username or ''
        if username:
            # Убираем все @ в начале и оставляем только один
            username = username.lstrip('@')
            username = f"@{username}"

        writer.writerow([
            group.group_hash,
            group.name,
            username,
            group.description or '',
            group.participants,
            group.category or '',
            group.group_type,
            group.link,
            group.date_added.strftime('%Y-%m-%d %H:%M:%S')
        ])

    # Получаем содержимое и кодируем в UTF-8 с BOM для корректного отображения в Excel
    csv_content = output.getvalue()
    output.close()

    # Добавляем BOM для UTF-8
    csv_bytes = '\ufeff'.encode('utf-8') + csv_content.encode('utf-8')

    return csv_bytes


def format_summary_message(groups_count):
    """
    Форматирует HTML-сообщение с краткой сводкой о результатах поиска.

    Включает статус выполнения, количество найденных групп и уведомление о файле.

    Сообщение отправляется перед CSV-файлом.

    :param groups_count: (int) Количество успешно сохранённых и отправленных групп.
    :return: (str) Сообщение с HTML-разметкой (теги <b>).
    """

    message = f"✅ <b>Поиск завершён!</b>\n\n"
    message += f"📊 Найдено и сохранено: <b>{groups_count}</b> групп/каналов\n"
    message += f"📁 Результаты отправлены в CSV файле"
    return message


@router.message(F.text == "📥 Получить всю базу")
async def export_all_groups(message: Message, state: FSMContext):
    """Выдаёт CSV-файл со всей базой данных групп и каналов."""
    await state.clear()  # Завершаем текущее состояние машины состояния
    # Путь к временному CSV-файлу
    csv_file_path = "telegram_groups_export.csv"

    try:
        # Получаем все записи из базы
        groups = TelegramGroup.select()

        count = groups.count()
        if count == 0:
            await message.answer("📭 База данных пуста.")
            return

        # Записываем данные в CSV
        with open(csv_file_path, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            # Заголовки
            writer.writerow([
                "Название", "Юзернейм", "Описание", "Участники",
                "Категория", "Тип", "Ссылка", "Дата добавления"
            ])
            # Данные
            for group in groups:
                writer.writerow([
                    group.name,
                    group.username or "",
                    group.description or "",
                    group.participants,
                    group.category or "",
                    group.group_type,
                    group.link,
                    group.date_added.strftime("%Y-%m-%d %H:%M:%S")
                ])

        # Отправляем файл пользователю
        document = FSInputFile(csv_file_path, filename="База_всех_групп.csv")
        await message.answer_document(
            document=document,
            caption=f"📦 Вся база данных Telegram-групп и каналов.\n\n"
                    f"📊 Всего записей: {count}"
        )

    except Exception as e:
        await message.answer("❌ Произошла ошибка при создании файла.")
        print(f"Error generating CSV: {e}")

    finally:
        # Удаляем временный файл после отправки
        if os.path.exists(csv_file_path):
            os.remove(csv_file_path)


@router.message(F.text == "📥 Получить всю базу Каналов")
async def export_channels(message: Message, state: FSMContext):
    """Выдаёт CSV-файл со всей базой данных групп и каналов."""
    await state.clear()  # Завершаем текущее состояние машины состояния
    # Путь к временному CSV-файлу
    csv_file_path = "telegram_channels_export.csv"

    try:
        # Получаем только КАНАЛЫ
        groups = TelegramGroup.select().where(
            TelegramGroup.group_type == 'Канал'
        )

        count = groups.count()
        if count == 0:
            await message.answer("📭 В базе данных нет каналов.")
            return

        # Записываем данные в CSV
        with open(csv_file_path, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            # Заголовки
            writer.writerow([
                "Название", "Юзернейм", "Описание", "Участники",
                "Категория", "Тип", "Ссылка", "Дата добавления"
            ])
            # Данные
            for group in groups:
                writer.writerow([
                    group.name,
                    group.username or "",
                    group.description or "",
                    group.participants,
                    group.category or "",
                    group.group_type,
                    group.link,
                    group.date_added.strftime("%Y-%m-%d %H:%M:%S")
                ])

        # Отправляем файл
        document = FSInputFile(csv_file_path, filename="База_каналов.csv")
        await message.answer_document(
            document=document,
            caption=f"📺 База данных Telegram-каналов.\n\n"
                    f"📊 Всего каналов: {count}"
        )

    except Exception as e:
        await message.answer("❌ Произошла ошибка при создании файла.")
        print(f"Error generating CSV: {e}")

    finally:
        # Удаляем временный файл после отправки
        if os.path.exists(csv_file_path):
            os.remove(csv_file_path)


@router.message(F.text == "📥 Получить всю базу Групп (супергрупп)")
async def export_supergroups(message: Message, state: FSMContext):
    """Выдаёт CSV-файл со всей базой данных групп и каналов."""
    await state.clear()  # Завершаем текущее состояние машины состояния
    # Путь к временному CSV-файлу
    csv_file_path = "telegram_supergroups_export.csv"

    try:
        # Получаем только СУПЕРГРУППЫ
        groups = TelegramGroup.select().where(
            TelegramGroup.group_type == 'Группа (супергруппа)'
        )

        count = groups.count()
        if count == 0:
            await message.answer("📭 В базе данных нет супергрупп.")
            return

        # Записываем данные в CSV
        with open(csv_file_path, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            # Заголовки
            writer.writerow([
                "Название", "Юзернейм", "Описание", "Участники",
                "Категория", "Тип", "Ссылка", "Дата добавления"
            ])
            # Данные
            for group in groups:
                writer.writerow([
                    group.name,
                    group.username or "",
                    group.description or "",
                    group.participants,
                    group.category or "",
                    group.group_type,
                    group.link,
                    group.date_added.strftime("%Y-%m-%d %H:%M:%S")
                ])

        # Отправляем файл
        document = FSInputFile(csv_file_path, filename="База_супергрупп.csv")
        await message.answer_document(
            document=document,
            caption=f"👥 База данных Telegram-супергрупп.\n\n"
                    f"📊 Всего супергрупп: {count}"
        )

    except Exception as e:
        await message.answer("❌ Произошла ошибка при создании файла.")
        print(f"Error generating CSV: {e}")

    finally:
        # Удаляем временный файл после отправки
        if os.path.exists(csv_file_path):
            os.remove(csv_file_path)


@router.message(F.text == "📥 Получить всю базу Обычных чатов (группы старого типа)")
async def export_legacy_groups(message: Message, state: FSMContext):
    """Выдаёт CSV-файл со всей базой данных групп и каналов."""
    await state.clear()  # Завершаем текущее состояние машины состояния
    # Путь к временному CSV-файлу
    csv_file_path = "telegram_oldgroups_export.csv"

    try:
        # Получаем только ОБЫЧНЫЕ ЧАТЫ (группы старого типа)
        groups = TelegramGroup.select().where(
            TelegramGroup.group_type == 'Обычный чат (группа старого типа)'
        )

        count = groups.count()
        if count == 0:
            await message.answer("📭 В базе данных нет обычных чатов.")
            return

        # Записываем данные в CSV
        with open(csv_file_path, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            # Заголовки
            writer.writerow([
                "Название", "Юзернейм", "Описание", "Участники",
                "Категория", "Тип", "Ссылка", "Дата добавления"
            ])
            # Данные
            for group in groups:
                writer.writerow([
                    group.name,
                    group.username or "",
                    group.description or "",
                    group.participants,
                    group.category or "",
                    group.group_type,
                    group.link,
                    group.date_added.strftime("%Y-%m-%d %H:%M:%S")
                ])

        # Отправляем файл
        document = FSInputFile(csv_file_path, filename="База_обычных_чатов.csv")
        await message.answer_document(
            document=document,
            caption=f"💬 База данных обычных чатов (группы старого типа).\n\n"
                    f"📊 Всего чатов: {count}"
        )

    except Exception as e:
        await message.answer("❌ Произошла ошибка при создании файла.")
        print(f"Error generating CSV: {e}")

    finally:
        # Удаляем временный файл после отправки
        if os.path.exists(csv_file_path):
            os.remove(csv_file_path)


@router.message(F.text == "🔎 Поиск групп / каналов")
async def handle_enter_keyword_menu(message: Message, state: FSMContext):
    """
    Обрабатывает запрос пользователя на поиск Telegram-групп и каналов через ИИ.

    Отображает информационное сообщение с описанием доступных действий:
    - 🔍 AI-поиск по ключевому слову
    - 📥 Получение всей базы данных
    - 🔙 Возврат в главное меню

    Используется как промежуточное меню для навигации в разделе поиска.

    :param message: (Message) Входящее сообщение от пользователя.
    :param state: (FSMContext, optional) Контекст состояния конечного автомата (не используется, но передаётся).
    :return: None
    """
    await state.clear()  # Завершаем текущее состояние машины состояния
    text = (
        "👋 Добро пожаловать в режим поиска!\n\n"
        "Вот что вы можете сделать:\n\n"
        "🔹 <b>🔍 AI-поиск групп / каналов</b> — найдём релевантные чаты по вашему ключевому слову с помощью искусственного интеллекта.\n\n"
        "🔹 <b>📥 Получить всю базу</b> — получите полный список всех сохранённых групп и каналов в формате CSV.\n\n"
        "🔸 Нажмите <b>🔙 Назад</b>, чтобы вернуться в главное меню."
    )
    await message.answer(
        text=text,
        reply_markup=search_group_ai(),
        parse_mode="HTML"
    )


@router.message(F.text == "🤖 AI поиск")
async def ai_search(message: Message, state: FSMContext):
    """
    Обработчик команды "🔎 Поиск групп / каналов".

    Очищает состояние FSM, получает данные пользователя, логирует действие
    и запрашивает у пользователя ключевое слово для поиска групп через AI.
    Переводит пользователя в состояние ожидания ввода (MyStates.entering_keyword_ai_search).

    :param message: (Message) Входящее сообщение от пользователя.
    :param state: (FSMContext) Контекст машины состояний, сбрасывается при входе.
    :return: None
    """
    await state.clear()  # Сбрасывает состояние

    telegram_user = message.from_user
    user = User.get(User.user_id == telegram_user.id)

    logger.info(
        f"Пользователь {telegram_user.id} {telegram_user.username} перешел в меню поиска групп")

    await message.answer(
        get_text(user.language, "enter_keyword"),
        reply_markup=back_keyboard()
    )
    await state.set_state(MyStates.entering_keyword_ai_search)


@router.message(MyStates.entering_keyword_ai_search)
async def handle_enter_keyword(message: Message, state: FSMContext):
    """
    Обработчик ввода ключевого слова для AI-поиска групп и каналов.

    Получает запрос от пользователя, генерирует варианты названий через Groq API,
    ищет соответствующие группы в Telegram, сохраняет их в базу данных и отправляет
    результаты пользователю в виде CSV-файла.

    В процессе показывает статус "Ищу...", удаляет его после завершения и отправляет
    сводку и файл.

    Обрабатывает ошибки и пустые результаты.

    - Использует `get_groq_response` для генерации названий.
    - Использует `search_groups_in_telegram` для поиска в Telegram.
    - Результаты сохраняются через `save_group_to_db`.
    - Файл создаётся через `create_csv_file` и отправляется как документ.

    :param message: (Message) Входящее сообщение с ключевым словом.
    :param state: (FSMContext) Контекст машины состояний, сбрасывается после обработки.
    :return: None

    Raises:
        Exception: Перехватывается локально, логируется и преобразуется в пользовательское сообщение.
    """

    telegram_user = message.from_user
    user_input = message.text.strip()
    # Отправляем сообщение о начале поиска
    processing_msg = await message.answer("🔍 Ищу группы и каналы...")

    try:
        # Получаем ответ от AI
        answer = await get_groq_response(user_input)
        logger.info(f"Ответ от Groq: {answer}")

        # Разбиваем ответ на строки и очищаем
        group_names = [clean_group_name(line) for line in answer.splitlines() if line.strip()]
        group_names = [name for name in group_names if len(name) > 2]
        logger.info(f"Получено {len(group_names)} названий: {group_names}")

        saved_groups = []

        for group_name in group_names:
            # Ищем в Telegram
            results = await search_groups_in_telegram([group_name])
            logger.info(f"Найдено {len(results)} групп для '{group_name}'")

            # Сохраняем результаты в БД
            for group_data in results:
                saved_group = save_group_to_db(group_data, category=user_input)
                if saved_group:
                    saved_groups.append(saved_group)

        # Удаляем сообщение о поиске
        await processing_msg.delete()

        # Отправляем результаты пользователю
        if saved_groups:
            # Создаём CSV файл
            csv_bytes = create_csv_file(saved_groups)
            # Генерируем имя файла с датой
            filename = f"telegram_groups_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            # Создаём файл для отправки
            csv_file = BufferedInputFile(csv_bytes, filename=filename)
            # Отправляем краткую сводку
            summary = format_summary_message(len(saved_groups))
            await message.answer(summary, parse_mode="HTML")
            # Отправляем CSV файл
            await message.answer_document(
                document=csv_file,
                caption=f"📄 Результаты поиска по запросу: <b>{user_input}</b>",
                parse_mode="HTML"
            )
            logger.info(f"Отправлено {len(saved_groups)} групп пользователю {telegram_user.id} в CSV файле")
        else:
            await message.answer(
                "❌ К сожалению, по вашему запросу ничего не найдено. Попробуйте другие ключевые слова.",
                reply_markup=back_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса: {e}")
        await processing_msg.delete()
        await message.answer(
            "❌ Произошла ошибка при поиске. Попробуйте ещё раз.",
            reply_markup=back_keyboard()
        )
    await state.clear()  # Завершаем текущее состояние машины состояния


def register_handlers_pars_ai():
    """
    Регистрирует обработчики для AI-поиска и экспорта Telegram-групп и каналов.

    Добавляет в маршрутизатор (router) следующие обработчики:
        1. search_menu — отображает меню поиска по нажатию кнопки "🔎 Поиск групп / каналов".
        2. start_ai_search — запускает процесс AI-поиска по нажатию "🤖 AI поиск".
        3. process_ai_search_keyword — обрабатывает ввод ключевого слова в состоянии MyStates.entering_keyword_ai_search.
        4. export_all_groups — экспортирует всю базу групп и каналов в CSV.
        5. export_channels — экспортирует только каналы.
        6. export_supergroups — экспортирует только супергруппы.
        7. export_legacy_groups — экспортирует обычные чаты (группы старого типа).

    Эти обработчики позволяют пользователю:
        - Использовать ИИ для поиска релевантных Telegram-чats по ключевому слову.
        - Получать результаты в виде CSV-файла.
        - Экспортировать всю или часть базы данных по типам чатов.

    :return: None
    """
    router.message.register(handle_enter_keyword_menu, F.text == "🔎 Поиск групп / каналов")
    router.message.register(ai_search, F.text == "🤖 AI поиск")
    router.message.register(export_all_groups, F.text == "📥 Получить всю базу")
    router.message.register(export_channels, F.text == "📥 Получить всю базу Каналов")
    router.message.register(export_supergroups, F.text == "📥 Получить всю базу Групп (супергрупп)")
    router.message.register(export_legacy_groups, F.text == "📥 Получить всю базу Обычных чатов (группы старого типа)")
