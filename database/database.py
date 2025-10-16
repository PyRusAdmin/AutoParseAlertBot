# -*- coding: utf-8 -*-
from peewee import Model, SqliteDatabase, IntegerField, CharField

db = SqliteDatabase('bot.db')


class User(Model):
    user_id = IntegerField(unique=True)
    username = CharField(null=True)
    first_name = CharField(null=True)
    last_name = CharField(null=True)
    language = CharField(default="ru")  # "ru" или "en"

    class Meta:
        database = db


def create_groups_model(user_id):
    class Groups(Model):
        """Модель для хранения чатов пользователя"""
        username_chat_channel = CharField(unique=True)  # Поле для хранения имени канала

        class Meta:
            database = db  # Указываем, что модель использует базу данных
            table_name = f"groups_{user_id}"  # Имя таблицы

    return Groups  # Возвращаем класс модели


def create_keywords_model(user_id):
    class Keywords(Model):
        """Модель для хранения ключевых слов"""
        user_keyword = CharField(unique=True)  # Поле для хранения ключевого слова

        class Meta:
            database = db  # Указываем, что модель использует базу данных
            table_name = f"keywords_{user_id}"  # Имя таблицы

    return Keywords  # Возвращаем класс модели


# Создаём таблицы при первом запуске
db.connect()
db.create_tables([User], safe=True)
