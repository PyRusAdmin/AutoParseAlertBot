# -*- coding: utf-8 -*-

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, BufferedInputFile
from loguru import logger

from system.dispatcher import router


@router.message(F.text == "Инструкция по использованию")
async def handle_post_doc_user(message: Message, state: FSMContext):
    """Отправка пользователю документации по использованию проекта"""
    await state.clear()

    id_user = message.from_user.id
    logger.info(f"Пользователь с id {id_user} запросил документацию")

    file_path = "doc/doc.md"
    filename = "doc.md"

    try:
        # Читаем содержимое файла
        with open(file_path, "r", encoding="utf-8") as file:
            md_content = file.read()

        # Создаём BufferedInputFile из текста
        md_file = BufferedInputFile(
            md_content.encode("utf-8"),
            filename=filename
        )

        # Отправляем файл
        await message.answer_document(
            document=md_file,
            caption="Инструкция по использованию бота",
            parse_mode="HTML"
        )

    except FileNotFoundError:
        logger.error(f"Файл {file_path} не найден")
        await message.answer("К сожалению, инструкция сейчас недоступна. Попробуйте позже.")

    except Exception as e:
        logger.error(f"Ошибка при отправке файла: {e}")
        await message.answer("Произошла ошибка при отправке инструкции.")
