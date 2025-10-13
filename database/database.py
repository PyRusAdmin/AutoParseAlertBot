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


# Создаём таблицы при первом запуске
db.connect()
db.create_tables([User], safe=True)
