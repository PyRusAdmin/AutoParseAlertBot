# -*- coding: utf-8 -*-
import os

from aiogram import Bot, Dispatcher, Router
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
api_id = os.getenv("ID")
api_hash = os.getenv("HASH")

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()

dp = Dispatcher(storage=storage)

# ID администраторов бота с особыми привилегиями
ADMIN_USER_ID = (535185511, 7181118530)

router = Router()
dp.include_router(router)
