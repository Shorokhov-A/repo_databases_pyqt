from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import mapper, sessionmaker
import datetime


# Класс - база данных сервера.
class ClientDatabase:
    # Класс - отображение списка контактов
    class Contacts:
        def __init__(self, contact):
            self.id = None
            self.name = contact

    # Класс - отображение таблицы истории сообщений
    class MessageHistory:
        def __init__(self, from_user, to_user, message):
            self.id = None
            self.from_user = from_user
            self.to_user = to_user
            self.message = message
            self.date = datetime.datetime.now()

    # Конструктор класса:
    def __init__(self, name):
        # Создаём движок базы данных, поскольку разрешено несколько клиентов одновременно,
        # каждый должен иметь свою БД.
        # Поскольку клиент мультипоточный, то необходимо отключить проверки на подключения
        # с разных потоков, иначе sqlite3.ProgrammingError
        self.database_engine = create_engine(f'sqlite:///client_{name}.db3',
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
                        Column('from_user', String),
                        Column('to_user', String),
                        Column('message', Text),
                        Column('date', DateTime)
                        )

        # Создаём таблицы
        self.metadata.create_all(self.database_engine)

        # Создаём отображения
        mapper(self.Contacts, contacts)
        mapper(self.MessageHistory, history)

        # Создаём сессию
        Session = sessionmaker(bind=self.database_engine)
        self.session = Session()

        # Необходимо очистить таблицу контактов, т.к. при запуске они подгружаются с сервера.
        self.session.query(self.Contacts).delete()
        self.session.commit()
