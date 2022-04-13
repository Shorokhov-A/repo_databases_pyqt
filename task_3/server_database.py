from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime
from sqlalchemy.orm import mapper, sessionmaker
import datetime
from common.variables import *


# Класс - серверная база данных:
class ServerStorage:
    # Класс - отображение таблицы всех пользователей
    # Экземпляр этого класса - запись в таблице AllUsers
    class AllUsers:
        def __init__(self, username):
            self.name = username
            self.last_login = datetime.datetime.now()
            self.id = None

    def __init__(self):
        # Создаём движок базы данных.
        # SERVER_DATABASE - sqlite:///server_base.db3
        # echo=False - отключает вывод на экран sql-запросов.
        # pool_recycle - по умолчанию соединение с БД через 8 часов простоя обрывается.
        # Чтобы этого не случилось необходимо добавить pool_recycle=7200 (переустановка соединения через каждые 2 часа)
        self.database_engine = create_engine(SERVER_DATABASE, echo=False, pool_recycle=7200)

        # Создаём объект MetaData
        self.metadata = MetaData()

        # Создаём таблицу пользователей
        users_table = Table('Users', self.metadata,
                            Column('id', Integer, primary_key=True),
                            Column('name', String, unique=True),
                            Column('last_login', DateTime)
                            )

        # Создаём таблицы
        self.metadata.create_all(self.database_engine)

        # Создаём отображения
        # Связываем класс в ORM с таблицей
        mapper(self.AllUsers, users_table)

        # Создаём сессию
        Session = sessionmaker(bind=self.database_engine)
        self.session = Session()
        self.session.commit()
