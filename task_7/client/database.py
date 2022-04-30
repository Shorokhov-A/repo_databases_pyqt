from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import mapper, sessionmaker
import datetime
import os


# Класс - база данных сервера.
class ClientDatabase:
    """
    Класс - оболочка для работы с базой данных клиента.
    Использует SQLite базу данных, реализован с помощью
    SQLAlchemy ORM и используется классический подход.
    """
    class Contacts:
        """
        Класс - отображение для таблицы контактов.
        """
        def __init__(self, contact):
            self.id = None
            self.name = contact

    class MessageStat:
        """
        Класс - отображение для таблицы статистики переданных сообщений.
        """
        def __init__(self, contact, direction, message):
            self.id = None
            self.contact = contact
            self.direction = direction
            self.message = message
            self.date = datetime.datetime.now()

    class KnownUsers:
        """
        Класс - отображение для таблицы всех пользователей.
        """
        def __init__(self, user):
            self.id = None
            self.username = user

    # Конструктор класса:
    def __init__(self, name):
        # Создаём движок базы данных, поскольку разрешено несколько клиентов одновременно,
        # каждый должен иметь свою БД.
        # Поскольку клиент мультипоточный, то необходимо отключить проверки на подключения
        # с разных потоков, иначе sqlite3.ProgrammingError
        path = os.path.dirname(os.path.realpath(__file__))
        filename = f'client_{name}.db3'
        self.database_engine = create_engine(f'sqlite:///{os.path.join(path, filename)}',
                                             echo=False,
                                             pool_recycle=7200,
                                             connect_args={'check_same_thread': False})

        # Создаём объект MetaData
        self.metadata = MetaData()

        # Создаём таблицу контактов
        contacts = Table('contacts', self.metadata,
                         Column('id', Integer, primary_key=True),
                         Column('name', String, unique=True)
                         )

        # Создаём таблицу истории сообщений
        history = Table('message_history', self.metadata,
                        Column('id', Integer, primary_key=True),
                        Column('contact', String),
                        Column('direction', String),
                        Column('message', Text),
                        Column('date', DateTime)
                        )

        # Создаём таблицу известных пользователей
        users = Table('known_users', self.metadata,
                      Column('id', Integer, primary_key=True),
                      Column('username', String)
                      )

        # Создаём таблицы
        self.metadata.create_all(self.database_engine)

        # Создаём отображения
        mapper(self.Contacts, contacts)
        mapper(self.MessageStat, history)
        mapper(self.KnownUsers, users)

        # Создаём сессию
        Session = sessionmaker(bind=self.database_engine)
        self.session = Session()

        # Необходимо очистить таблицу контактов, т.к. при запуске они подгружаются с сервера.
        self.session.query(self.Contacts).delete()
        self.session.commit()

    def add_users(self, users_list):
        """
        Метод, заполняющий таблицу известных пользователей.
        :param users_list: список пользователей
        :return: ничего не возвращает
        """
        self.session.query(self.KnownUsers).delete()
        for user in users_list:
            user_row = self.KnownUsers(user)
            self.session.add(user_row)
        self.session.commit()

    def add_contact(self, contact):
        """
        Метод добавляющий контакт в базу данных.
        :param contact: добавляемый контакт
        :return: ничего не возвращает
        """
        if not self.session.query(self.Contacts).filter_by(name=contact).count():
            contact_row = self.Contacts(contact)
            self.session.add(contact_row)
            self.session.commit()

    def contacts_clear(self):
        """
        Метод, очищающий таблицу со списком контактов.
        :return: ничего не возвращает
        """
        self.session.query(self.Contacts).delete()
        self.session.commit()

    def del_contact(self, contact):
        """
        Метод, удаляющий определённый контакт.
        :param contact: удаляемый контакт
        :return: ничего не возвращает
        """
        self.session.query(self.Contacts).filter_by(name=contact).delete()
        self.session.commit()

    def check_user(self, user):
        """
        Метод, проверяющий существует ли пользователь.
        :param user: проверяемый пользователь
        :return: True или False
        """
        if self.session.query(self.KnownUsers).filter_by(username=user).count():
            return True
        else:
            return False

    def get_contacts(self):
        """
        Метод, возвращающий список всех контактов.
        :return: список всех контактов
        """
        return [contact[0] for contact in self.session.query(self.Contacts.name).all()]

    def get_users(self):
        """
        Метод возвращающий список всех известных пользователей.
        :return: список всех известных пользователей
        """
        return [user[0] for user in self.session.query(self.KnownUsers.username).all()]

    def check_contact(self, contact):
        """
        Метод, проверяющий существует ли контакт.
        :param contact: проверяемый контакт
        :return: True или False
        """
        if self.session.query(self.Contacts).filter_by(name=contact).count():
            return True
        else:
            return False

    def get_history(self, contact):
        """
        Метод, возвращающий историю сообщений с определённым пользователем.
        :param contact: пользователь
        :return: история сообщений с определённым пользователем
        """
        query = self.session.query(self.MessageStat).filter_by(contact=contact)
        return [(history_row.contact, history_row.direction,
                 history_row.message, history_row.date)
                for history_row in query.all()]

    def save_message(self, contact, direction, message):
        """
        Метод, сохраняющий сообщение в базе данных.
        :param contact: пользователь
        :param direction: направление
        :param message: текст сообщения
        :return: ничего не возвращает
        """
        message_row = self.MessageStat(contact, direction, message)
        self.session.add(message_row)
        self.session.commit()


# отладка
if __name__ == '__main__':
    test_db = ClientDatabase('test1')
    for i in ['test3', 'test4', 'test5']:
        test_db.add_contact(i)
    test_db.add_contact('test4')
    test_db.add_users(['test1', 'test2', 'test3', 'test4', 'test5'])
    print(test_db.check_user('test1'))
    print(test_db.check_user('test10'))
    print(test_db.get_contacts())
    print(test_db.get_users())
    print(test_db.check_contact('test3'))
    print(test_db.check_contact('test10'))
    test_db.del_contact('test3')
    print(test_db.check_contact('test3'))
    test_db.save_message('test1', 'out',
                         f'Тестовое сообщение от пользователя test1 от {datetime.datetime.now()}!')
    test_db.save_message('test1', 'in',
                         f'Тестовое сообщение от пользователя test2 от {datetime.datetime.now()}!')
    print(test_db.get_history('test1'))
    print(test_db.get_history('test3'))
