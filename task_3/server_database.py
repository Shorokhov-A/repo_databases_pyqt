from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import mapper, sessionmaker
import datetime
from common.variables import *


# Класс - серверная база данных:
class ServerStorage:
    # Класс - отображение таблицы всех пользователей:
    # Экземпляр этого класса - запись в таблице AllUsers.
    class AllUsers:
        def __init__(self, username):
            self.name = username
            self.last_login = datetime.datetime.now()
            self.id = None

    # Класс - отображение таблицы активных пользователей:
    # Экземпляр этого класса - запись в таблице ActiveUsers.
    class ActiveUsers:
        def __init__(self, user_id, ip_address, port, login_time):
            self.user = user_id
            self.ip_address = ip_address
            self.port = port
            self.login_time = login_time
            self.id = None

    # Класс - отображение таблицы истории входов:
    # Экземпляр этого класса - запись в таблице LoginHistory.
    class LoginHistory:
        def __init__(self, name, date, ip, port):
            self.id = None
            self.name = name
            self.date_time = date
            self.ip = ip
            self.port = port

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

        # Создаём таблицу активных пользователей
        active_users_table = Table('Active_users', self.metadata,
                                   Column('id', Integer, primary_key=True),
                                   Column('user', ForeignKey('Users.id'), unique=True),
                                   Column('ip_address', String),
                                   Column('port', Integer),
                                   Column('login_time', DateTime)
                                   )

        # Создаём таблицу истории входов
        user_login_history = Table('Login_history', self.metadata,
                                   Column('id', Integer, primary_key=True),
                                   Column('name', ForeignKey('Users.id')),
                                   Column('date_time', DateTime),
                                   Column('ip', String),
                                   Column('port', String)
                                   )

        # Создаём таблицы
        self.metadata.create_all(self.database_engine)

        # Создаём отображения.
        # Связываем класс в ORM с таблицей
        mapper(self.AllUsers, users_table)
        mapper(self.ActiveUsers, active_users_table)
        mapper(self.LoginHistory, user_login_history)

        # Создаём сессию
        Session = sessionmaker(bind=self.database_engine)
        self.session = Session()

        # Если в таблице активных пользователей есть записи, то их необходимо удалить.
        # Когда устанавливаем соединение, очищаем таблицу активных пользователей.
        self.session.query(self.ActiveUsers).delete()
        self.session.commit()

    # Функция выполняющаяся при входе пользователя, записывает в базу факт входа.
    def user_login(self, username, ip_address, port):
        print(username, ip_address, port)
        # Запрос в таблицу пользователей на наличие там пользователя с таким именем
        result = self.session.query(self.AllUsers).filter_by(name=username)

        # Если имя пользователя уже присутствует в таблице, то обновляем время последнего входа
        if result.count():
            user = result.first()
            user.last_login = datetime.datetime.now()
        # Если нет, то создаём нового пользователя
        else:
            # Создаём экземпляр класса self.AllUsers, через который передаём данные в таблицу
            user = self.AllUsers(username)
            self.session.add(user)
            # Коммит здесь нужен для того, чтобы создать нового пользователя,
            # id которого будет использовано для добавления в таблицу активных пользователей
            self.session.commit()

        # Теперь можно создать запись в таблицу активных пользователей о факте входа.
        # Создаём экземпляр класса self.ActiveUsers, через который передаём данные в таблицу
        new_active_user = self.ActiveUsers(user.id, ip_address, port, datetime.datetime.now())
        self.session.add(new_active_user)

        # Создаём экземпляр класса self.LoginHistory, через который передаём данные в таблицу
        history = self.LoginHistory(user.id, datetime.datetime.now(), ip_address, port)
        self.session.add(history)

        # Сохраняем изменения
        self.session.commit()


# Отладка
if __name__ == '__main__':
    test_db = ServerStorage()

    # Выполняем "подключение" пользователя
    test_db.user_login('client_1', '192.168.1.120', 8080)
    test_db.user_login('client_2', '192.168.1.121', 7777)
