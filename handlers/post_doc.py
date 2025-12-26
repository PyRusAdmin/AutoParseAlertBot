# -*- coding: utf-8 -*-
from aiogram import F
from aiogram.types import Message, FSInputFile

from system.dispatcher import router


@router.message(F.text == "Инструкция по использованию")
async def send_instruction(message: Message):
    """Отправляет пользователю файл с инструкцией"""

    file_path = "doc/doc.md"

    try:
        # Отправляем файл напрямую из файловой системы
        document = FSInputFile(file_path)

        await message.answer_document(
            document=document,
            caption="Вот инструкция по использованию бота, так же можно прочитать https://gitverse.ru/pyadminru/AutoParseAlertBot/content/master/doc/doc.md"
        )

    except FileNotFoundError:
        await message.answer("Файл инструкции не найден на сервере.")

    except Exception as e:
        await message.answer(f"Произошла ошибка при отправке файла: {e}")


def register_handlers_post_doc():
    """Регистрирует обработчики"""
    router.message.register(send_instruction)
