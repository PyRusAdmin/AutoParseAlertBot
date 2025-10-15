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
        """
        Модель для хранения групп / каналов для отслеживания.
        """

        username_chat_channel = CharField(unique=True, primary_key=True)  # Получаем username группы

        class Meta:
            database = db  # Указываем, что данная модель будет использовать базу данных
            table_name = f"groups_{user_id}"  # динамическое имя таблицы

    return Groups


# Создаём таблицы при первом запуске
db.connect()
db.create_tables([User], safe=True)
