from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import mapper, sessionmaker
import datetime
from pprint import pprint
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

    # Класс - отображение таблицы контактов пользователей:
    class UsersContacts:
        def __init__(self, user, contact):
            self.id = None
            self.user = user
            self.contact = contact

    # Класс отображение таблицы истории действий
    class UsersHistory:
        def __init__(self, user):
            self.id = None
            self.user = user
            self.sent = 0
            self.accepted = 0

    def __init__(self, path):
        # Создаём движок базы данных.
        print(path)
        self.database_engine = create_engine(f'sqlite:///{path}', echo=False, pool_recycle=7200,
                                             connect_args={'check_same_thread': False})

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

        # Создаём таблицу контактов пользователей
        contacts = Table('Contacts', self.metadata,
                         Column('id', Integer, primary_key=True),
                         Column('user', ForeignKey('Users.id')),
                         Column('contact', ForeignKey('Users.id'))
                         )

        # Создаём таблицу истории пользователей
        users_history_table = Table('History', self.metadata,
                                    Column('id', Integer, primary_key=True),
                                    Column('user', ForeignKey('Users.id')),
                                    Column('sent', Integer),
                                    Column('accepted', Integer)
                                    )

        # Создаём таблицы
        self.metadata.create_all(self.database_engine)

        # Создаём отображения.
        # Связываем класс в ORM с таблицей
        mapper(self.AllUsers, users_table)
        mapper(self.ActiveUsers, active_users_table)
        mapper(self.LoginHistory, user_login_history)
        mapper(self.UsersContacts, contacts)
        mapper(self.UsersHistory, users_history_table)

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
            user_in_history = self.UsersHistory(user.id)
            self.session.add(user_in_history)

        # Теперь можно создать запись в таблицу активных пользователей о факте входа.
        # Создаём экземпляр класса self.ActiveUsers, через который передаём данные в таблицу
        new_active_user = self.ActiveUsers(user.id, ip_address, port, datetime.datetime.now())
        self.session.add(new_active_user)

        # Создаём экземпляр класса self.LoginHistory, через который передаём данные в таблицу
        history = self.LoginHistory(user.id, datetime.datetime.now(), ip_address, port)
        self.session.add(history)

        # Сохраняем изменения
        self.session.commit()

    # Функция, фиксирующая отключение пользователя
    def user_logout(self, username):
        # Запрашиваем пользователя, который отключается.
        # Получаем запись из таблицы self.AllUsers
        user = self.session.query(self.AllUsers).filter_by(name=username).first()

        # Удаляем его из таблицы активных пользователей.
        # Удаляем запись из таблицы self.ActiveUsers
        self.session.query(self.ActiveUsers).filter_by(user=user.id).delete()

        # Применяем изменения
        self.session.commit()

    # Функция возвращает список известных пользователей со временем последнего входа.
    def users_list(self):
        # Запрос строк таблицы пользователей.
        query = self.session.query(
            self.AllUsers.name,
            self.AllUsers.last_login
        )
        # Возвращаем список кортежей
        return query.all()

    # Функция возвращает список активных пользователей
    def active_users_list(self):
        # Запрашиваем соединение таблиц и собираем кортежи имя, адрес, порт, время.
        query = self.session.query(
            self.AllUsers.name,
            self.ActiveUsers.ip_address,
            self.ActiveUsers.port,
            self.ActiveUsers.login_time
        ).join(self.AllUsers)
        # Возвращаем список кортежей
        return query.all()

    # Функция, возвращающая историю входов по пользователю или всем пользователям
    def login_history(self, username=None):
        # Запрашиваем историю входа
        query = self.session.query(self.AllUsers.name,
                                   self.LoginHistory.date_time,
                                   self.LoginHistory.ip,
                                   self.LoginHistory.port
                                   ).join(self.AllUsers)
        # Если было указано имя пользователя, то фильтруем по этому имени
        if username:
            query = query.filter(self.AllUsers.name == username)
        # Возвращаем список кортежей
        return query.all()

    # Функция возвращает список контактов пользователя.
    def get_contacts(self, username):
        # Запрашиваем указанного пользователя
        user = self.session.query(self.AllUsers).filter_by(name=username).one()

        # Запрашиваем его список контактов
        query = self.session.query(self.UsersContacts, self.AllUsers.name). \
            filter_by(user=user.id). \
            join(self.AllUsers, self.UsersContacts.contact == self.AllUsers.id)

        # выбираем только имена пользователей и возвращаем их.
        return [contact[1] for contact in query.all()]

    # Функция добавляет контакт для пользователя.
    def add_contact(self, user, contact):
        # Получаем ID пользователей
        user = self.session.query(self.AllUsers).filter_by(name=user).first()
        contact = self.session.query(self.AllUsers).filter_by(name=contact).first()

        # Проверяем что не дубль и что контакт может существовать (полю пользователь мы доверяем)
        if not contact or self.session.query(self.UsersContacts).filter_by(user=user.id, contact=contact.id).count():
            return

        # Создаём объект и заносим его в базу
        contact_row = self.UsersContacts(user.id, contact.id)
        self.session.add(contact_row)
        self.session.commit()

    # Функция удаляет контакт из базы данных
    def remove_contact(self, user, contact):
        # Получаем ID пользователей
        user = self.session.query(self.AllUsers).filter_by(name=user).first()
        contact = self.session.query(self.AllUsers).filter_by(name=contact).first()

        # Проверяем что контакт может существовать (полю пользователь мы доверяем)
        if not contact:
            return

        # Удаляем требуемое
        print(self.session.query(self.UsersContacts).filter(
            self.UsersContacts.user == user.id,
            self.UsersContacts.contact == contact.id
        ).delete())
        self.session.commit()

    # Функция фиксирует передачу сообщения и делает соответствующие отметки в БД
    def process_message(self, sender, recipient):
        # Получаем ID отправителя и получателя
        sender = self.session.query(self.AllUsers).filter_by(name=sender).first().id
        recipient = self.session.query(self.AllUsers).filter_by(name=recipient).first().id
        # Запрашиваем строки из истории и увеличиваем счётчики
        sender_row = self.session.query(self.UsersHistory).filter_by(user=sender).first()
        sender_row.sent += 1
        recipient_row = self.session.query(self.UsersHistory).filter_by(user=recipient).first()
        recipient_row.accepted += 1

        self.session.commit()

    # Функция возвращает количество переданных и полученных сообщений
    def message_history(self):
        query = self.session.query(
            self.AllUsers.name,
            self.AllUsers.last_login,
            self.UsersHistory.sent,
            self.UsersHistory.accepted
        ).join(self.AllUsers)
        # Возвращаем список кортежей
        return query.all()


# Отладка
if __name__ == '__main__':
    test_db = ServerStorage('server_base.db3')

    # Выполняем "подключение" пользователя
    test_db.user_login('client_1', '192.168.1.120', 8080)
    test_db.user_login('client_2', '192.168.1.121', 7777)

    # Выводим список кортежей - активных пользователей
    print(' ---- test_db.active_users_list() ----')
    pprint(test_db.active_users_list())

    # Выполняем "отключение" пользователя
    test_db.user_logout('client_1')
    # И выводим список активных пользователей
    print(' ---- test_db.active_users_list() after logout client_1 ----')
    pprint(test_db.active_users_list())

    # Запрашиваем историю входов по пользователю
    print(' ---- test_db.login_history(client_1) ----')
    pprint(test_db.login_history('client_1'))

    # и выводим список известных пользователей
    print(' ---- test_db.users_list() ----')
    pprint(test_db.users_list())

    # Добавляем контакт
    test_db.add_contact('client_2', 'client_1')

    # Удаляем контакт
    test_db.remove_contact('client_2', 'client_1')

    # Проверка фиксации обмена сообщениями в истории сообщений.
    test_db.process_message('client_2', 'client_1')
    pprint(test_db.message_history())
