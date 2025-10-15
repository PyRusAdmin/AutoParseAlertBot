# -*- coding: utf-8 -*-
from aiogram.fsm.state import StatesGroup, State


class MyStates(StatesGroup):
    """Прием ссылки на группу / канал"""
    waiting_username_group = State()  # ожидание ввода имени группы в формате @username
