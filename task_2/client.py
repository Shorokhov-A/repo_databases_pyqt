from socket import socket, AF_INET, SOCK_STREAM
import time
import sys
import json
import logging
import argparse
import threading
from logs import client_log_config
from errors import ReqFieldMissingError, ServerError, IncorrectDataReceivedError
from common.variables import MESSAGE, SENDER, DESTINATION, MESSAGE_TEXT, DEFAULT_IP_ADDRESS, DEFAULT_PORT, ACTION, \
    PRESENCE, TIME, USER, ACCOUNT_NAME, RESPONSE, ERROR, EXIT
from common.utils import send_message, get_message
from decorators import log

# Инициализация клиентского логгера:
CLIENT_LOGGER = logging.getLogger('client')


@log
def create_message(sock, account_name='Guest'):
    """
    Функция запрашивает кому отправить сообщение и само сообщение,
    и отправляет полученные данные на сервер.
    :param sock:
    :param account_name:
    :return:
    """
    to_user = input('Укажите получателя сообщения: ')
    message = input('Введите сообщение для отправки: ')
    message_dict = {
        ACTION: MESSAGE,
        SENDER: account_name,
        DESTINATION: to_user,
        TIME: time.time(),
        MESSAGE_TEXT: message
    }
    CLIENT_LOGGER.debug(f'Сформирован словарь сообщения: {message_dict}')
    try:
        send_message(sock, message_dict)
        CLIENT_LOGGER.info(f'Щтправлено сообщение для пользователя {to_user}')
    except Exception as e:
        print(e)
        CLIENT_LOGGER.critical('Потеряно соединение с сервером.')
        sys.exit(1)


@log
def message_from_server(sock, my_username):
    """Функция-обработчик сообщений других пользователей, поступающих с сервера."""
    while True:
        try:
            message = get_message(sock)
            if ACTION in message and message[ACTION] == MESSAGE and SENDER in message and DESTINATION in message \
                    and MESSAGE_TEXT in message and message[DESTINATION] == my_username:
                print(f'Получено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                CLIENT_LOGGER.info(f'Получено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
            else:
                CLIENT_LOGGER.error(f'Получено некорректное сообщение с сервера: {message}')
        except IncorrectDataReceivedError:
            CLIENT_LOGGER.error('Не удалось декодировать полученное сообщение.')
        except (OSError, ConnectionError, ConnectionAbortedError, ConnectionResetError, json.JSONDecodeError):
            CLIENT_LOGGER.critical('Потеряно соединение с сервером.')
            break


@log
def create_presence(account_name):
    """
    Функция генерирует запрос о присутствии клиента.
    :param account_name:
    :return:
    """
    out = {
        ACTION: PRESENCE,
        TIME: time.time(),
        USER: {
            ACCOUNT_NAME: account_name,
        }
    }
    CLIENT_LOGGER.debug(f'Сформировано {PRESENCE} сообщение для пользователя {account_name}')
    return out


@log
def process_response_ans(message):
    """
    Функция разбирает ответ сервера.
    :param message:
    :return:
    """
    CLIENT_LOGGER.debug(f'Разбор сообщения от сервера: {message}.')
    if RESPONSE in message:
        if message[RESPONSE] == 200:
            return '200 : OK'
        elif message[RESPONSE] == 400:
            raise ServerError(f'400: {message[ERROR]}')
    raise ReqFieldMissingError(RESPONSE)


@log
def arg_parser():
    """
    Функция-парсер аргументов командной строки.
    :return:
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('address', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.address
    server_port = namespace.port
    client_name = namespace.name

    # Проверяем корректность номера порта.
    if not 1023 < server_port < 65536:
        CLIENT_LOGGER.critical(
            f'Попытка запуска клиента с неподходящим номером порта: {server_port}. '
            f'Допустимы адреса с 1024 до 65535. Клиент завершается.')
        sys.exit(1)

    return server_address, server_port, client_name


def print_help():
    """Функция, выводящая справку по использованию."""
    print('Поддерживаемые команды:')
    print('message - отправить сообщение. Кому и текст будет запрошены отдельно.')
    print('help - вывести подсказки по командам')
    print('exit - выход из программы')


@log
def create_exit_message(account_name):
    """
    Функция создаёт словарь с сообщением о выходе.
    :account_name:
    :return:
    """
    return {
        ACTION: EXIT,
        TIME: time.time(),
        ACCOUNT_NAME: account_name
    }


@log
def user_interactive(sock, username):
    """
    Функция взаимодействия с пользователем. Запрашивает команды, отправляет сообщения
    :param sock:
    :param username:
    :return:
    """
    print_help()
    while True:
        command = input('Введите команду: ')
        if command == 'message':
            create_message(sock, username)
        elif command == 'help':
            print_help()
        elif command == 'exit':
            send_message(sock, create_exit_message(username))
            print('Завершение соединения.')
            CLIENT_LOGGER.info('Завершение работы по команде пользователя.')
            # Задержка неоходима, чтобы успело уйти сообщение о выходе
            time.sleep(0.5)
            break
        else:
            print('Команда не распознана. Попробойте снова. help - вывести поддерживаемые команды.')


def main():
    # Загружаем параметры командной строки.
    server_address, server_port, client_name = arg_parser()

    # Сообщаем о запуске.
    print(f'Консольный мессенджер. Клиентский модуль. Имя пользователя: {client_name}')

    # Если имя пользователя не было задано, то его нужно запросить.
    if not client_name:
        client_name = input('Введите имя пользователя: ')

    CLIENT_LOGGER.info(
        f'Запущен клиент с параметрами:'
        f'адрес сервера: {server_address}, порт: {server_port}, имя пользователя: {client_name}'
    )

    # Инициализация сокета и сообщение серверу о нашем появлении.
    try:
        transport = socket(AF_INET, SOCK_STREAM)
        transport.connect((server_address, server_port))
        send_message(transport, create_presence(client_name))
        answer = process_response_ans(get_message(transport))
        CLIENT_LOGGER.info(f'Установлено соединение с сервером. Ответ сервера {answer}')
        print('Установлено соединение с сервером.')
    except json.JSONDecodeError:
        CLIENT_LOGGER.error('Не удалось декодировать полученную Json строку.')
        sys.exit(1)
    except ServerError as error:
        CLIENT_LOGGER.error(f'При установке соединения сервер вернул ошибку: {error.text}')
        sys.exit(1)
    except ReqFieldMissingError as missing_error:
        CLIENT_LOGGER.error(f'В ответе сервера отсутствует необходимое поле {missing_error.missing_field}')
        sys.exit(1)
    except (ConnectionRefusedError, ConnectionError):
        CLIENT_LOGGER.critical(f'Не удалось подключиться к серверу {server_address}:{server_port}.'
                               f'Конечный компьютер отверг запрос на подключение.')
        sys.exit(1)
    else:
        # Если соединение с сервером установлено корректно, то запускаем клиентский процесс приема сообщений.
        receiver = threading.Thread(target=message_from_server, args=(transport, client_name))
        receiver.daemon = True
        receiver.start()

        # Затем запускаем отправку сообщений и взаимодействие пользователей.
        user_interface = threading.Thread(target=user_interactive, args=(transport, client_name))
        user_interface.daemon = True
        user_interface.start()
        CLIENT_LOGGER.debug('Запущены процессы.')

        # Watchdog основной цикл. Если один из потоков завершен, то значит или потеряно соединение,
        # или пользователь ввел exit. Поскольку все события обрабатываются в потоках, достаточно просто завершить цикл.
        while True:
            time.sleep(1)
            if receiver.is_alive() and user_interface.is_alive():
                continue
            break


if __name__ == '__main__':
    main()
