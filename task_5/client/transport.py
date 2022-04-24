from socket import socket, AF_INET, SOCK_STREAM
import time
import sys
import json
import logging
import threading
from PyQt5.QtCore import pyqtSignal, QObject

sys.path.append('../')
from common.variables import *
from common.utils import send_message, get_message
from common.errors import ServerError
from logs import client_log_config

# Инициализация клиентского логгера:
CLIENT_LOGGER = logging.getLogger('client')

# Объект блокировки сокета и работы с базой данных
SOCKET_LOCK = threading.Lock()


# Класс - Транспорт, отвечает за взаимодействие с сервером
class ClientTransport(threading.Thread, QObject):
    # Сигналы новое сообщение и потеря соединения
    new_message = pyqtSignal(str)
    connection_lost = pyqtSignal()

    def __init__(self, port, ip_address, database, username):
        # Вызываем конструктор предка
        threading.Thread.__init__(self)
        QObject.__init__(self)

        # Класс База данных - работа с базой
        self.database = database
        # Имя пользователя
        self.username = username
        # Сокет для работы с сервером
        self.transport = None
        # Устанавливаем соединение:
        self.connection_init(port, ip_address)
        # Обновляем таблицы известных пользователей и контактов
        try:
            self.user_list_update()
            self.contacts_list_update()
        except OSError as err:
            if err.errno:
                CLIENT_LOGGER.critical(f'Потеряно соединение с сервером.')
                raise ServerError('Потеряно соединение с сервером!')
            CLIENT_LOGGER.error('Timeout соединения при обновлении списков пользователей.')
        except json.JSONDecodeError:
            CLIENT_LOGGER.critical(f'Потеряно соединение с сервером.')
            raise ServerError('Потеряно соединение с сервером!')
            # Флаг продолжения работы транспорта.
        self.running = True

    # Функция инициализации соединения с сервером
    def connection_init(self, port, ip):
        # Инициализация сокета и сообщение серверу о нашем появлении.
        self.transport = socket(AF_INET, SOCK_STREAM)

        # Таймаут 1 секунда, необходим для освобождения сокета.
        self.transport.settimeout(5)

        # Соединяемся, 5 попыток соединения, флаг успеха ставим в True если удалось
        connected = False
        for i in range(5):
            CLIENT_LOGGER.info(f'Попытка подключения №{i + 1}')
            try:
                self.transport.connect((ip, port))
            except (OSError, ConnectionRefusedError):
                pass
            else:
                connected = True
                break
            time.sleep(1)

        # Если соединится не удалось - исключение
        if not connected:
            CLIENT_LOGGER.critical('Не удалось установить соединение с сервером')
            raise ServerError('Не удалось установить соединение с сервером')

        CLIENT_LOGGER.debug('Установлено соединение с сервером')

        # Посылаем серверу приветственное сообщение и получаем ответ,
        # что всё нормально или ловим исключение.
        try:
            with SOCKET_LOCK:
                send_message(self.transport, self.create_presence())
                self.process_server_ans(get_message(self.transport))
        except (OSError, json.JSONDecodeError):
            CLIENT_LOGGER.critical('Потеряно соединение с сервером!')
            raise ServerError('Потеряно соединение с сервером!')

        # Если всё хорошо, сообщение об установке соединения.
        CLIENT_LOGGER.info('Соединение с сервером успешно установлено.')

    # Функция, генерирующая приветственное сообщение для сервера
    def create_presence(self):
        out = {
            ACTION: PRESENCE,
            TIME: time.time(),
            USER: {
                ACCOUNT_NAME: self.username,
            }
        }
        CLIENT_LOGGER.debug(f'Сформировано {PRESENCE} сообщение для пользователя {self.username}')
        return out

    # Функция, обрабатывающая сообщения от сервера. Ничего не возвращает.
    # Генерирует исключение при ошибке.
    def process_server_ans(self, message):
        CLIENT_LOGGER.debug(f'Разбор сообщения от сервера: {message}.')
        # Если это подтверждение чего-либо
        if RESPONSE in message:
            if message[RESPONSE] == 200:
                return
            elif message[RESPONSE] == 400:
                raise ServerError(f'{message[ERROR]}')
            else:
                CLIENT_LOGGER.debug(f'Принят неизвестный код подтверждения {message[RESPONSE]}')

        # Если это сообщение от пользователя добавляем в базу, даём сигнал о новом сообщении
        elif ACTION in message \
                and message[ACTION] == MESSAGE \
                and SENDER in message \
                and DESTINATION in message \
                and MESSAGE_TEXT in message \
                and message[DESTINATION] == self.username:
            CLIENT_LOGGER.debug(f'Получено сообщение от пользователя {message[SENDER]}:'
                         f'{message[MESSAGE_TEXT]}')
            self.database.save_message(message[SENDER], 'in', message[MESSAGE_TEXT])
            self.new_message.emit(message[SENDER])

    # Функция, обновляющая контакт - лист с сервера
    def contacts_list_update(self):
        CLIENT_LOGGER.debug(f'Запрос списка контактов для пользователя {self.name}')
        request_to_server = {
            ACTION: GET_CONTACTS,
            TIME: time.time(),
            USER: self.username
        }
        CLIENT_LOGGER.debug(f'Сформирован запрос {request_to_server}')
        with SOCKET_LOCK:
            send_message(self.transport, request_to_server)
            server_answer = get_message(self.transport)
        CLIENT_LOGGER.debug(f'Получен ответ {server_answer}')
        if RESPONSE in server_answer and server_answer[RESPONSE] == 202:
            for contact in server_answer[LIST_INFO]:
                self.database.add_contact(contact)
        else:
            CLIENT_LOGGER.error('Не удалось обновить список контактов.')

    # Функция обновления таблицы известных пользователей.
    def user_list_update(self):
        CLIENT_LOGGER.debug(f'Запрос списка известных пользователей {self.username}')
        request_to_server = {
            ACTION: USERS_REQUEST,
            TIME: time.time(),
            ACCOUNT_NAME: self.username
        }
        with SOCKET_LOCK:
            send_message(self.transport, request_to_server)
            server_answer = get_message(self.transport)
        if RESPONSE in server_answer and server_answer[RESPONSE] == 202:
            self.database.add_users(server_answer[LIST_INFO])
        else:
            CLIENT_LOGGER.error('Не удалось обновить список известных пользователей.')

    # Функция сообщающая на сервер о добавлении нового контакта
    def add_contact(self, contact):
        CLIENT_LOGGER.debug(f'Создание контакта {contact}')
        request_to_server = {
            ACTION: ADD_CONTACT,
            TIME: time.time(),
            USER: self.username,
            ACCOUNT_NAME: contact
        }
        with SOCKET_LOCK:
            send_message(self.transport, request_to_server)
            self.process_server_ans(get_message(self.transport))

    # Функция удаления клиента на сервере
    def remove_contact(self, contact):
        CLIENT_LOGGER.debug(f'Удаление контакта {contact}')
        request_to_server = {
            ACTION: REMOVE_CONTACT,
            TIME: time.time(),
            USER: self.username,
            ACCOUNT_NAME: contact
        }
        with SOCKET_LOCK:
            send_message(self.transport, request_to_server)
            self.process_server_ans(get_message(self.transport))

    # Функция закрытия соединения, отправляет сообщение о выходе.
    def transport_shutdown(self):
        self.running = False
        message = {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: self.username
        }
        with SOCKET_LOCK:
            try:
                send_message(self.transport, message)
            except OSError:
                pass
        CLIENT_LOGGER.debug('Транспорт завершает работу.')
        time.sleep(0.5)

    # Функция отправки сообщения на сервер
    def send_message(self, to, message):
        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.username,
            DESTINATION: to,
            TIME: time.time(),
            MESSAGE_TEXT: message
        }
        CLIENT_LOGGER.debug(f'Сформирован словарь сообщения: {message_dict}')

        # Необходимо дождаться освобождения сокета для отправки сообщения
        with SOCKET_LOCK:
            send_message(self.transport, message_dict)
            self.process_server_ans(get_message(self.transport))
            CLIENT_LOGGER.info(f'Отправлено сообщение для пользователя {to}')

    def run(self):
        CLIENT_LOGGER.debug('Запущен процесс - приёмник сообщений с сервера.')
        while self.running:
            # Отдыхаем секунду и снова пробуем захватить сокет. Если не сделать тут задержку,
            # то отправка может достаточно долго ждать освобождения сокета.
            time.sleep(1)
            with SOCKET_LOCK:
                try:
                    self.transport.settimeout(0.5)
                    message = get_message(self.transport)
                except OSError as err:
                    if err.errno:
                        # выход по таймауту вернёт номер ошибки err.errno равный None
                        # поэтому, при выходе по таймауту мы сюда не попадём
                        CLIENT_LOGGER.critical(f'Потеряно соединение с сервером.')
                        self.running = False
                        self.connection_lost.emit()
                # Проблемы с соединением
                except (ConnectionError, ConnectionAbortedError,
                        ConnectionResetError, json.JSONDecodeError, TypeError):
                    CLIENT_LOGGER.debug(f'Потеряно соединение с сервером.')
                    self.running = False
                    self.connection_lost.emit()
                # Если сообщение получено, то вызываем функцию обработчик:
                else:
                    CLIENT_LOGGER.debug(f'Принято сообщение с сервера: {message}')
                    self.process_server_ans(message)
                finally:
                    self.transport.settimeout(5)
