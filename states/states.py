# -*- coding: utf-8 -*-
from aiogram.fsm.state import StatesGroup, State


class MyStates(StatesGroup):
    """Прием ссылки на группу / канал"""
    waiting_username_group = State()  # ожидание ввода имени группы в формате @username
    entering_keyword = State()  # ожидание ввода ключевого слова
    entering_group = State()  # ожидание ввода группы в формате @username (техническая)

    entering_keyword_ai_search = State()  # ожидание ввода ключевого слова для поиска в AI
