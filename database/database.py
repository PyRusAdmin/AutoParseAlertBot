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


class Groups(Model):
    """
    Модель для хранения групп / каналов для отслеживания.
    """

    username_chat_channel = CharField(unique=True)  # Получаем username группы

    class Meta:
        database = db  # Указываем, что данная модель будет использовать базу данных
        table_name = "groups"  # Имя таблицы
        primary_key = (
            False  # Для запрета автоматически создающегося поля id (как первичный ключ)
        )


# Создаём таблицы при первом запуске
db.connect()
db.create_tables([User], safe=True)
db.create_tables([Groups], safe=True)  # Создаём таблицу для групп
