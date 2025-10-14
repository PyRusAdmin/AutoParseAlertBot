import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router
from aiogram.fsm.storage.memory import MemoryStorage

# Загружаем переменные окружения
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
api_id = os.getenv("ID")
api_hash = os.getenv("HASH")

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

ADMIN_USER_ID = (535185511, 301634256)

router = Router()
dp.include_router(router)
