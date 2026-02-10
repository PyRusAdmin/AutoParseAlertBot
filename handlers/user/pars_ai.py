# -*- coding: utf-8 -*-
import io
import re
from datetime import datetime

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, ReplyKeyboardRemove, Message
from loguru import logger  # https://github.com/Delgan/loguru
from openpyxl import Workbook
from openpyxl.styles import Font

from ai.ai import get_groq_response, search_groups_in_telegram
from database.database import User, TelegramGroup
from keyboards.user.keyboards import back_keyboard, search_group_ai, get_categories_keyboard
from locales.locales import get_text
from states.states import MyStates, ExportStates
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


# def generate_group_hash(username=None, name=None, link=None):
#     """
#     Генерирует MD5-хеш для уникальной идентификации группы в базе данных.
#
#     Использует один из трёх параметров: username, link или name (в порядке приоритета)
#     для создания хеша, который служит первичным ключом в таблице `TelegramGroup`.
#
#     Приоритет: username > link > name. Используется первый непустой параметр.
#
#     :param username : (str, optional) Юзернейм группы (например, "@python_chat").
#     :param name : (str, optional) Название группы.
#     :param link : (str, optional) Прямая ссылка на группу (например, "https://t.me/python_chat").
#     :return str: 32-символьная hex-строка MD5-хеша.
#     """
#     if username:
#         return hashlib.md5(username.encode()).hexdigest()
#     elif link:
#         return hashlib.md5(link.encode()).hexdigest()
#     else:
#         return hashlib.md5(name.encode()).hexdigest()


# def determine_group_type(group_data):
#     """
#     Определяет тип Telegram-чата на основе его данных.
#
#     Анализирует словарь с информацией о группе и возвращает строку с типом.
#
#     Используется при сохранении группы в базу данных.
#
#     - 'channel': если есть флаг is_channel.
#     - 'group': если есть username (предполагает, что это группа).
#     - 'link': во всех остальных случаях.
#
#     :param group_data : (dict) Словарь с данными о группе, полученный из поиска.
#     :return str: Тип чата — 'channel', 'group' или 'link'.
#     """
#     if 'is_channel' in group_data and group_data['is_channel']:
#         return 'channel'
#     elif 'username' in group_data and group_data['username']:
#         return 'group'
#     else:
#         return 'link'


def save_group_to_db(group_data):
    """
    Сохраняет или обновляет информацию о группе в централизованной базе данных.

    Использует хеш для проверки существования группы. При наличии обновляет поля,
    при отсутствии — создаёт новую запись. Поля 'participants' и 'description'
    обновляются при каждом нахождении группы.

    Функция является частью механизма deduplication и предотвращает дублирование записей.

    :param group_data : (dict) Словарь с информацией о группе (название, username, участники и т.д.).
    :return TelegramGroup or None: Экземпляр сохранённой модели или None при ошибке.
    :raise Exception: Логируется при ошибках работы с БД (например, нарушение ограничений).
    """
    try:
        telegram_id = group_data.get('telegram_id')
        group_hash = group_data.get('group_hash')
        name = group_data.get('name')
        username = group_data.get('username')
        description = group_data.get('description')
        participants = group_data.get('participants')
        category = group_data.get('category')
        group_type = group_data.get('group_type')
        language = group_data.get('language')
        link = group_data.get('link')
        date_added = datetime.now()
        # Проверяем, существует ли уже такая группа
        existing = TelegramGroup.get_or_none(TelegramGroup.group_hash == group_hash)

        if existing:
            # Обновляем данные
            existing.name = name
            existing.username = username
            existing.description = description
            existing.participants = participants
            existing.link = link
            existing.date_added = date_added
            existing.save()
            logger.info(f"Обновлена группа: {group_data['name']}")
            return existing
        else:
            # Создаём новую запись
            new_group = TelegramGroup.create(
                telegram_id=telegram_id,
                group_hash=group_hash,
                name=name,
                username=username,
                description=description,
                participants=participants,
                category=category,
                group_type=group_type,
                language=language,
                link=link,
                date_added=date_added
            )
            logger.info(f"Добавлена новая группа: {group_data['name']}")
            return new_group

    except Exception as e:
        logger.exception(f"Ошибка при сохранении группы: {e}")
        return None


def format_summary_message(groups_count):
    """
    Форматирует HTML-сообщение с краткой сводкой о результатах поиска.

    Включает статус выполнения, количество найденных групп и уведомление о файле.

    Сообщение отправляется перед XLSX-файлом.

    :param groups_count: (int) Количество успешно сохранённых и отправленных групп.
    :return: (str) Сообщение с HTML-разметкой (теги <b>).
    """

    message = f"✅ <b>Поиск завершён!</b>\n\n"
    message += f"📊 Найдено и сохранено: <b>{groups_count}</b> групп/каналов\n"
    message += f"📁 Результаты отправлены в Excel-файле"
    return message


def create_excel_file(groups):
    """
    Создаёт байтовый Excel-файл (.xlsx) с данными о найденных группах для отправки пользователю.

    Содержит колонки: ID (Hash), Название, Username, Описание, Участников,
    Категория, Тип, Ссылка, Дата добавления.
    Username приводится к формату '@username'.

    :param groups: (list[TelegramGroup]) Список экземпляров модели TelegramGroup.
    :return: bytes — содержимое .xlsx файла в памяти.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Результаты поиска"

    # Заголовки
    headers = [
        'ID (Hash)',
        'Название',
        'Username',
        'Описание',
        'Участников',
        'Категория',
        'Тип',
        'Ссылка',
        'Дата добавления'
    ]
    ws.append(headers)

    # Жирный шрифт для заголовков
    for col in range(1, len(headers) + 1):
        ws.cell(row=1, column=col).font = Font(bold=True)

    # Данные
    for group in groups:
        username = group.username or ''
        if username:
            username = f"@{username.lstrip('@')}"

        ws.append([
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

    # Автоподбор ширины (опционально)
    for column_cells in ws.columns:
        length = max(len(str(cell.value)) for cell in column_cells) + 2
        ws.column_dimensions[column_cells[0].column_letter].width = min(length, 50)

    # Сохраняем в BytesIO
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


@router.message(F.text == "📥 Вся база")
async def export_all_groups(message: Message, state: FSMContext):
    """Выдаёт CSV-файл со всей базой данных групп и каналов."""
    await state.clear()  # Завершаем текущее состояние машины состояния
    try:
        # Получаем все записи из базы
        groups = TelegramGroup.select()
        if not groups:
            await message.answer("📭 База данных пуста.")
            return

        excel_bytes = create_excel_file(groups)
        document = BufferedInputFile(excel_bytes, filename="Вся_база.xlsx")
        await message.answer_document(
            document=document,
            caption=f"📦 Вся база данных Telegram-групп и каналов.\n\n📊 Всего записей: {len(groups)}"
        )

    except Exception as e:
        await message.answer("❌ Произошла ошибка при создании файла.")
        logger.exception(e)


@router.message(F.text == "📥 База каналов")
async def export_channels(message: Message, state: FSMContext):
    """Выдаёт CSV-файл со всей базой данных групп и каналов."""
    await state.clear()  # Завершаем текущее состояние машины состояния
    # Путь к временному CSV-файлу
    try:
        # Получаем только КАНАЛЫ
        groups = TelegramGroup.select().where(
            TelegramGroup.group_type == 'Канал'
        )

        if not groups:
            await message.answer("📭 База данных пуста.")
            return

        excel_bytes = create_excel_file(groups)
        document = BufferedInputFile(excel_bytes, filename="База_каналов.xlsx")
        await message.answer_document(
            document=document,
            caption=f"📦 Вся база данных Telegram-групп и каналов.\n\n📊 Всего записей: {len(groups)}"
        )

    except Exception as e:
        await message.answer("❌ Произошла ошибка при создании файла.")
        logger.exception(e)


@router.message(F.text == "📥 База групп")
async def export_supergroups(message: Message, state: FSMContext):
    """Выдаёт CSV-файл со всей базой данных групп и каналов."""
    await state.clear()  # Завершаем текущее состояние машины состояния
    try:
        # Получаем только СУПЕРГРУППЫ
        groups = TelegramGroup.select().where(
            TelegramGroup.group_type == 'Группа (супергруппа)'
        )
        if not groups:
            await message.answer("📭 База данных пуста.")
            return

        excel_bytes = create_excel_file(groups)
        document = BufferedInputFile(excel_bytes, filename="База_групп.xlsx")
        await message.answer_document(
            document=document,
            caption=f"📦 Вся база данных Telegram-групп и каналов.\n\n📊 Всего записей: {len(groups)}"
        )

    except Exception as e:
        await message.answer("❌ Произошла ошибка при создании файла.")
        logger.exception(e)


@router.message(F.text == "📥 Получить базу")
async def handle_enter_keyword_menu(message: Message, state: FSMContext):
    """
    Обрабатывает запрос пользователя на получение базы Telegram-групп и каналов.

    Отображает информационное сообщение с описанием доступных действий:
    - 📥 Получение всей базы данных
    - 🔙 Возврат в главное меню

    Используется как промежуточное меню для навигации в разделе поиска.

    :param message: (Message) Входящее сообщение от пользователя.
    :param state: (FSMContext, optional) Контекст состояния конечного автомата (не используется, но передаётся).
    :return: None
    """
    await state.clear()  # Завершаем текущее состояние машины состояния
    text = (
        "👋 Добро пожаловать в режим получения базы данных!\n\n"
        "Вот что вы можете сделать:\n\n"

        "🔹 <b>📥 Получить всю базу</b> — получите полный список всех сохранённых групп и каналов в формате Excel.\n"
        "🔹 <b>📥 Получить базу Каналов</b> — получите список всех сохранённых каналов в формате Excel.\n"
        "🔹 <b>📥 Получить базу Групп (супергрупп)</b> — получите список всех сохранённых супергрупп в формате Excel.\n"
        "🔹 <b>📥 Получить базу Обычных чатов (группы старого типа)</b> — получите список всех сохранённых обычных чатов (групп старого типа) в формате Excel.\n"
        "🔹 Выбрать категорию для получения базы\n\n"

        "🔸 Нажмите <b>🔙 Назад</b>, чтобы вернуться в главное меню."
    )
    await message.answer(
        text=text,
        reply_markup=search_group_ai(),
        parse_mode="HTML"
    )


@router.message(F.text == "Выбрать категорию")
async def start_category_export(message: Message, state: FSMContext):
    """
    Запускает процесс выбора категории для экспорта.
    Показывает клавиатуру с категориями и переводит в состояние ожидания выбора.
    """
    await message.answer(
        "📌 Выберите категорию, по которой хотите получить список групп/каналов:",
        reply_markup=get_categories_keyboard()
    )
    await state.set_state(ExportStates.waiting_for_category)


@router.message(ExportStates.waiting_for_category)
async def handle_category_selection(message: Message, state: FSMContext):
    """
    Обрабатывает выбор категории и формирует файл со списком групп.
    """
    selected_category = message.text.strip()

    # Проверка на кнопку "Назад"
    if selected_category == "🔙 Назад":
        await message.answer("❌ Отменено.", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        return

    # Список допустимых категорий (для защиты от ручного ввода)
    valid_categories = {
        "Инвестиции",
        "Финансы и личный бюджет",
        "Криптовалюты и блокчейн",
        "Бизнес и предпринимательство",
        "Маркетинг и продвижение",
        "Технологии и IT",
        "Образование и саморазвитие",
        "Работа и карьера",
        "Недвижимость",
        "Здоровье и медицина",
        "Путешествия",
        "Авто и транспорт",
        "Шоппинг и скидки",
        "Развлечения и досуг",
        "Политика и общество",
        "Наука и исследования",
        "Спорт и фитнес",
        "Кулинария и еда",
        "Мода и красота",
        "Хобби и творчество"
    }

    if selected_category not in valid_categories:
        await message.answer(
            "⚠️ Неверная категория. Пожалуйста, выберите из списка.",
            reply_markup=get_categories_keyboard()
        )
        return

    # Получаем группы из базы
    groups = TelegramGroup.select().where(TelegramGroup.category == selected_category)
    group_count = groups.count()

    if group_count == 0:
        await message.answer(
            f"📭 В категории «{selected_category}» пока нет ни одной группы.",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
        return

    # === Создаём Excel-файл ===
    wb = Workbook()
    ws = wb.active
    ws.title = "Группы"

    # Заголовки
    headers = ["Username", "Название", "Описание", "Тип", "Участники", "Ссылка"]
    ws.append(headers)

    # Жирный шрифт для заголовков
    for col in range(1, len(headers) + 1):
        ws.cell(row=1, column=col).font = Font(bold=True)

    # Данные
    for group in groups:
        ws.append([
            group.username or "",
            group.name or "",
            group.description or "",
            group.group_type or "",
            group.participants or 0,
            group.link or ""
        ])

    # Автоподбор ширины колонок (опционально)
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)  # ограничим ширину
        ws.column_dimensions[column].width = adjusted_width

    # Сохраняем в память
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    # Отправляем файл
    file_name = f"groups_{selected_category.replace(' ', '_')}.xlsx"
    await message.answer_document(
        document=BufferedInputFile(
            file=output.getvalue(),
            filename=file_name
        ),
        caption=f"✅ Экспортировано {group_count} групп/каналов по категории:\n«{selected_category}»",
        reply_markup=ReplyKeyboardRemove()
    )

    logger.info(f"Пользователь {message.from_user.id} экспортировал Excel по категории: {selected_category}")
    await state.clear()


@router.message(F.text == "🤖 AI поиск")
async def ai_search(message: Message, state: FSMContext):
    """
    Обработчик команды "📥 Получить базу".

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
    результаты пользователю в виде XLSX-файла.

    В процессе показывает статус "Ищу...", удаляет его после завершения и отправляет
    сводку и файл.

    Обрабатывает ошибки и пустые результаты.

    - Использует `get_groq_response` для генерации названий.
    - Использует `search_groups_in_telegram` для поиска в Telegram.
    - Результаты сохраняются через `save_group_to_db`.
    - Файл создаётся через `create_excel_file` и отправляется как документ.

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
                saved_group = save_group_to_db(group_data)
                if saved_group:
                    saved_groups.append(saved_group)

        # Удаляем сообщение о поиске
        await processing_msg.delete()

        # Отправляем результаты пользователю
        if saved_groups:

            # Создаём Excel-файл
            excel_bytes = create_excel_file(saved_groups)
            filename = f"telegram_groups_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            excel_file = BufferedInputFile(excel_bytes, filename=filename)

            summary = format_summary_message(len(saved_groups))
            await message.answer(summary, parse_mode="HTML")
            # Отправляем CSV файл
            await message.answer_document(
                document=excel_file,
                caption=f"📄 Результаты поиска по запросу: <b>{user_input}</b>",
                parse_mode="HTML"
            )
            logger.info(f"Отправлено {len(saved_groups)} групп пользователю {telegram_user.id} в Excel файле")
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
        1. search_menu — отображает меню поиска по нажатию кнопки "📥 Получить базу".
        2. start_ai_search — запускает процесс AI-поиска по нажатию "🤖 AI поиск".
        3. process_ai_search_keyword — обрабатывает ввод ключевого слова в состоянии MyStates.entering_keyword_ai_search.
        4. export_all_groups — экспортирует всю базу групп и каналов в XLSX.
        5. export_channels — экспортирует только каналы.
        6. export_supergroups — экспортирует только супергруппы.
        7. export_legacy_groups — экспортирует обычные чаты (группы старого типа).

    Эти обработчики позволяют пользователю:
        - Использовать ИИ для поиска релевантных Telegram-чats по ключевому слову.
        - Получать результаты в виде XLSX-файла.
        - Экспортировать всю или часть базы данных по типам чатов.

    :return: None
    """
    router.message.register(handle_enter_keyword_menu, F.text == "📥 Получить базу")
    router.message.register(ai_search, F.text == "🤖 AI поиск")
    router.message.register(export_all_groups, F.text == "📥 Вся база")
    router.message.register(export_channels, F.text == "📥 База каналов")
    router.message.register(export_supergroups, F.text == "📥 База групп")

    router.message.register(start_category_export, F.text == "Выбрать категорию")
    router.message.register(handle_category_selection, ExportStates.waiting_for_category)
