import sys
import logging
import argparse
import select
import threading
import logs.server_log_config
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from common.variables import ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, RESPONSE_200, RESPONSE_400, \
    MESSAGE, DESTINATION, EXIT, MESSAGE_TEXT, ERROR, DEFAULT_PORT, SENDER
from common.utils import get_message, send_message
from decorators import log
from metaclasses import ServerVerifier
from descriptors import Port
from server_database import ServerStorage

# Инициализация логирования сервера:
SERVER_LOGGER = logging.getLogger('server')


@log
def arg_parser():
    """Парсер аргументов командной строки."""
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-a', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p

    return listen_address, listen_port


# Основной класс сервера.
class Server(threading.Thread, metaclass=ServerVerifier):
    port = Port()

    def __init__(self, listen_address, listen_port, database):
        # Параметры подключения
        self.sock = None
        self.addr = listen_address
        self.port = listen_port

        # База данных сервера
        self.database = database

        # Список подключённых клиентов.
        self.clients = []

        # Список сообщений на отправку.
        self.messages = []

        # Словарь содержащий сопоставленные имена и соответствующие им сокеты.
        self.names = dict()

        # Конструктор предка
        super().__init__()

    def init_socket(self):
        SERVER_LOGGER.info(f'Запущен сервер. Порт для подключений: {self.port}, '
                           f'адрес, с которого принимаются подключения: {self.addr}. '
                           f'Если адрес не указан, то принимаются соединения с любых адресов.')

        # Готовим сокет.
        transport = socket(AF_INET, SOCK_STREAM)
        transport.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        transport.bind((self.addr, self.port))
        transport.settimeout(1)

        # Начинаем слушать сокет.
        self.sock = transport
        self.sock.listen()

    # Обработчик сообщений от клиентов, принимает словарь - сообщение от клиента,
    # проверяет корректность, отправляет словарь-ответ в случае необходимости.
    def process_client_message(self, message, client):
        SERVER_LOGGER.debug(f'Разбор сообщения от клиента: {message}.')
        # Если это сообщение о присутствии, принимаем и отвечаем.
        if ACTION in message and message[ACTION] == PRESENCE and TIME in message \
                and USER in message:
            # Если такой пользователь еще не зарегистрирован,
            # то регистрируем, иначе отправляем ответ и завершаем соединение.
            if message[USER][ACCOUNT_NAME] not in self.names.keys():
                self.names[message[USER][ACCOUNT_NAME]] = client
                client_ip, client_port = client.getpeername()
                self.database.user_login(message[USER][ACCOUNT_NAME], client_ip, client_port)
                send_message(client, RESPONSE_200)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Имя пользователя уже занято.'
                send_message(client, response)
                self.clients.remove(client)
                client.close()
            return
        # Если это сообщение, то добавляем его в очередь сообщений. Ответ не требуется.
        elif ACTION in message and message[ACTION] == MESSAGE and DESTINATION in message and TIME in message \
                and SENDER in message and MESSAGE_TEXT in message:
            self.messages.append(message)
            return
        # Если клиент выходит:
        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message:
            self.database.user_logout(message[ACCOUNT_NAME])
            self.clients.remove(self.names[message[ACCOUNT_NAME]])
            self.names[message[ACCOUNT_NAME]].close()
            del self.names[message[ACCOUNT_NAME]]
            return
        # Иначе отдаём Bad request
        else:
            response = RESPONSE_400
            response[ERROR] = 'Запрос некорректен.'
            send_message(client, response)
            return

    # Функция адресной отправки сообщения определённому клиенту.
    # Принимает словарь сообщение, список зарегистрированных
    # пользователей и слушающие сокеты. Ничего не возвращает.
    def process_message(self, message, listen_socks):
        if message[DESTINATION] in self.names and self.names[message[DESTINATION]] in listen_socks:
            send_message(self.names[message[DESTINATION]], message)
            SERVER_LOGGER.info(f'Отправлено сообщение пользователю {message[DESTINATION]} '
                               f'от пользователя {message[SENDER]}.')
        elif message[DESTINATION] in self.names and self.names[message[DESTINATION]] not in listen_socks:
            raise ConnectionError
        else:
            SERVER_LOGGER.error(f'Пользователь {message[DESTINATION]} не зарегистрирован на сервере. '
                                f'Отправка сообщения невозможна.')

    def run(self):
        # Инициализация Сокета
        self.init_socket()

        # Основной цикл программы:
        while True:
            # Ждём подключения, если таймаут вышел, ловим исключение.
            try:
                client, client_address = self.sock.accept()
            except OSError:
                pass
            else:
                SERVER_LOGGER.info(f'Установлено соединение с ПК {client_address}.')
                self.clients.append(client)

            recv_data_list = []
            send_data_list = []
            err_list = []

            # Проверяем на наличие ждущих клиентов.
            try:
                if self.clients:
                    recv_data_list, send_data_list, err_list = select.select(self.clients, self.clients, [], 0)
            except OSError:
                pass

            # Принимаем сообщения и еcли они есть, то кладем в словарь. В случае ошибки исключаем клиента.
            if recv_data_list:
                for client_with_message in recv_data_list:
                    try:
                        self.process_client_message(get_message(client_with_message), client_with_message)
                    except:
                        SERVER_LOGGER.info(f'Клиент {client_with_message.getpeername()} отключился от сервера.')
                        self.clients.remove(client_with_message)
            # Если есть сообщения, то обрабатываем каждое.
            for message in self.messages:
                try:
                    self.process_message(message, send_data_list)
                except Exception as e:
                    SERVER_LOGGER.info(f'Связь с клиентом с именем {message[DESTINATION]} была потеряна, ошибка {e}.')
                    self.clients.remove(self.names[message[DESTINATION]])
                    del self.names[message[DESTINATION]]
            self.messages.clear()


def print_help():
    print('Поддерживаемые комманды:')
    print('users - список известных пользователей')
    print('connected - список подключённых пользователей')
    print('loghist - история входов пользователя')
    print('exit - завершение работы сервера.')
    print('help - вывод справки по поддерживаемым командам')


def main():
    # Загрузка параметров командной строки, если нет параметров, то задаём значения по умолчанию.
    listen_address, listen_port = arg_parser()

    # Инициализация базы данных
    database = ServerStorage()

    # Создание экземпляра класса - сервера.
    server = Server(listen_address, listen_port, database)
    server.daemon = True
    server.start()

    # Печатаем справку:
    print_help()

    # Основной цикл сервера:
    while True:
        command = input('Введите команду: ')
        if command == 'help':
            print_help()
        elif command == 'exit':
            break
        elif command == 'users':
            for user in sorted(database.users_list()):
                print(f'Пользователь {user[0]}, последний вход: {user[1]}')
        elif command == 'connected':
            for user in sorted(database.active_users_list()):
                print(f'Пользователь {user[0]}, подключен: {user[1]}:{user[2]}, время установки соединения: {user[3]}')
        elif command == 'loghist':
            name = input('Введите имя пользователя для просмотра истории. '
                         'Для вывода всей истории, просто нажмите Enter: ')
            for user in sorted(database.login_history(name)):
                print(f'Пользователь: {user[0]} время входа: {user[1]}. Вход с: {user[2]}:{user[3]}')
        else:
            print('Команда не распознана.')


if __name__ == '__main__':
    main()
