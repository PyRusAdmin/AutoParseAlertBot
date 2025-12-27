# -*- coding: utf-8 -*-
from datetime import datetime

from peewee import *

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
    """
    Динамически создаёт модель Peewee для хранения чатов конкретного пользователя.

    Модель используется для отслеживания списка Telegram-групп и каналов,
    добавленных пользователем для мониторинга. Создаётся отдельная таблица
    для каждого пользователя по шаблону 'groups_<user_id>'.

    Args:
        user_id (int): Уникальный идентификатор пользователя Telegram.

    Returns:
        peewee.Model: Класс модели Peewee с полем `username_chat_channel`.

    Model Fields:
        username_chat_channel (CharField):
            Уникальное имя чата (канала) в формате @username или название.
    """
    class Groups(Model):
        username_chat_channel = CharField(unique=True)  # Поле для хранения имени канала

        class Meta:
            database = db  # Указываем, что модель использует базу данных
            table_name = f"groups_{user_id}"  # Имя таблицы

    return Groups  # Возвращаем класс модели


def create_keywords_model(user_id):
    """
    Динамически создаёт модель Peewee для хранения ключевых слов конкретного пользователя.

    Модель используется для отслеживания слов или фраз, по которым пользователь
    хочет фильтровать сообщения в группах. Создаётся отдельная таблица
    для каждого пользователя по шаблону 'keywords_<user_id>'.

    Args:
        user_id (int): Уникальный идентификатор пользователя Telegram.

    Returns:
        peewee.Model: Класс модели Peewee с полями `id` и `user_keyword`.

    Model Fields:
        id (AutoField):
            Автоинкрементный первичный ключ.
        user_keyword (CharField):
            Уникальное ключевое слово для поиска в сообщениях.
    """
    class Keywords(Model):
        id = AutoField()  # <-- добавляем первичный ключ (иначе всё пишется в одну строку)
        user_keyword = CharField(unique=True)  # Поле для хранения ключевого слова

        class Meta:
            database = db  # Указываем, что модель использует базу данных
            table_name = f"keywords_{user_id}"  # Имя таблицы

    return Keywords  # Возвращаем класс модели


def create_group_model(user_id):
    """
    Динамически создаёт модель Peewee для хранения технической группы пользователя.

    Модель используется для сохранения одного Telegram-чата (группы или канала),
    куда бот будет пересылать найденные сообщения, содержащие ключевые слова.
    Создаётся отдельная таблица для каждого пользователя по шаблону 'group_<user_id>'.

    Args:
        user_id (int): Уникальный идентификатор пользователя Telegram.

    Returns:
        peewee.Model: Класс модели Peewee с полями `id` и `user_group`.

    Model Fields:
        id (AutoField):
            Автоинкрементный первичный ключ.
        user_group (CharField):
            Уникальное имя технической группы (например, @my_alerts_channel).
    """
    class Group(Model):
        id = AutoField()  # <-- добавляем первичный ключ (иначе всё пишется в одну строку)
        user_group = CharField(unique=True)  # Поле для хранения технической группы

        class Meta:
            database = db  # Указываем, что модель использует базу данных
            table_name = f"group_{user_id}"  # Имя таблицы

    return Group  # Возвращаем класс модели


class BaseModel(Model):
    class Meta:
        database = db


class TelegramGroup(BaseModel):
    """
    Модель для хранения данных о найденных Telegram-группах и каналах.

    Используется для централизованного хранения информации о группах,
    обнаруженных с помощью AI-поиска (через Groq). Позволяет избежать
    повторного поиска и дублирования. Таблица общая для всех пользователей.

    Attributes:
        group_hash (CharField): Уникальный хеш или ID группы, используется как ключ.
        name (CharField): Отображаемое название группы или канала.
        username (CharField, optional): Юзернейм (@username), может отсутствовать.
        description (TextField, optional): Описание группы из Telegram.
        participants (IntegerField): Количество участников, по умолчанию 0.
        category (CharField, optional): Категория, определённая ИИ (например, 'технологии').
        group_type (CharField): Тип чата — 'group', 'channel' или 'link'.
        link (CharField): Прямая ссылка на чат (https://t.me/...).
        date_added (DateTimeField): Дата и время добавления записи, по умолчанию — текущее время.

    Meta:
        table_name (str): Имя таблицы в базе данных — 'telegram_groups'.
    """
    group_hash = CharField(unique=True, index=True)  # ID группы или хеш username
    name = CharField()  # Название группы
    username = CharField(null=True)  # @username если есть
    description = TextField(null=True)  # Описание
    participants = IntegerField(default=0)  # Количество участников
    category = CharField(null=True)  # Категория (определяется AI)
    group_type = CharField()  # 'group', 'channel', 'link'
    link = CharField()  # Ссылка на группу
    date_added = DateTimeField(default=datetime.now)  # Дата добавления

    class Meta:
        table_name = 'telegram_groups'


# Создаём таблицы при первом запуске
def init_db():
    """
    Инициализирует базу данных приложения.

    Подключается к SQLite-базе данных ('bot.db'), создаёт таблицу `telegram_groups`,
    если она ещё не существует, и закрывает соединение.

    Вызывается один раз при запуске бота в функции `main()`.

    Note:
        Используется параметр `safe=True` для безопасного создания таблиц
        (не вызывает ошибку, если таблица уже существует).
    """
    db.connect()
    db.create_tables([TelegramGroup], safe=True)
    db.close()
