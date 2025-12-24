# -*- coding: utf-8 -*-
import hashlib
import re
import csv
import io
from datetime import datetime

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, BufferedInputFile
from loguru import logger

from ai.ai import get_groq_response, search_groups_in_telegram
from database.database import User, TelegramGroup
from keyboards.keyboards import back_keyboard
from locales.locales import get_text
from states.states import MyStates
from system.dispatcher import router


def clean_group_name(name):
    """Очищаем название группы от номеров, символов и т.д."""
    cleaned = re.sub(r'^[\d\.\-\*\s\)\(\[\]]+', '', name).strip()
    return cleaned


def generate_group_hash(username=None, name=None, link=None):
    """Генерируем уникальный хеш для группы"""
    if username:
        return hashlib.md5(username.encode()).hexdigest()
    elif link:
        return hashlib.md5(link.encode()).hexdigest()
    else:
        return hashlib.md5(name.encode()).hexdigest()


def determine_group_type(group_data):
    """Определяем тип: group, channel или link"""
    if 'is_channel' in group_data and group_data['is_channel']:
        return 'channel'
    elif 'username' in group_data and group_data['username']:
        return 'group'
    else:
        return 'link'


def save_group_to_db(group_data, category=None):
    """Сохраняем группу в базу данных"""
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
    """Создаём CSV файл с результатами поиска"""
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
    """Форматируем краткое сообщение с результатами"""
    message = f"✅ <b>Поиск завершён!</b>\n\n"
    message += f"📊 Найдено и сохранено: <b>{groups_count}</b> групп/каналов\n"
    message += f"📁 Результаты отправлены в CSV файле"
    return message


@router.message(F.text == "Поиск групп / каналов")
async def handle_enter_keyword_menu(message: Message, state: FSMContext):
    """Ввод ключевого слова для поиска групп и каналов с помощью AI"""
    await state.clear()

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
    """Обработка введенного ключевого слова для поиска групп и каналов"""

    telegram_user = message.from_user
    # user = User.get(User.user_id == telegram_user.id)

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

    await state.clear()


def register_handlers_pars_ai():
    """Регистрация обработчиков"""
    router.message.register(handle_enter_keyword_menu)
    router.message.register(handle_enter_keyword)