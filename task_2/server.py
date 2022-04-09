import sys
import json
import logging
import argparse
import select
import time
import logs.server_log_config
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from common.variables import ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, RESPONSE_200, RESPONSE_400, RESPONSE, \
    MESSAGE, DESTINATION, EXIT, MESSAGE_TEXT, ERROR, DEFAULT_PORT, MAX_CONNECTIONS, SENDER
from common.utils import get_message, send_message
from decorators import log

# Инициализация логирования сервера:
SERVER_LOGGER = logging.getLogger('server')


@log
def process_client_message(message, messages_list, client, clients, names):
    """
    Обработчик сообщений от клиентов.
    Функция принимает словарь-сообщение от клиента, проверяет корректность, возвращает словарь-ответ для клиента.
    :param message:
    :param messages_list:
    :param client:
    :param clients:
    :param names:
    :return:
    """
    SERVER_LOGGER.debug(f'Разбор сообщения от клиента: {message}.')
    # Если это сообщение о присутствии, принимаем и отвечаем.
    if ACTION in message and message[ACTION] == PRESENCE and TIME in message \
            and USER in message:
        # Если такой пользователь еще не зарегистрирован,
        # то регистрируем, иначе отправляем ответ и завершаем соединение.
        if message[USER][ACCOUNT_NAME] not in names.keys():
            names[message[USER][ACCOUNT_NAME]] = client
            send_message(client, RESPONSE_200)
        else:
            response = RESPONSE_400
            response[ERROR] = 'Имя пользователя уже занято.'
            send_message(client, response)
            clients.remove(client)
            client.close()
        return
    # Если это сообщение, то добавляем его в очередь сообщений. Ответ не требуется.
    elif ACTION in message and message[ACTION] == MESSAGE and DESTINATION in message and TIME in message \
            and SENDER in message and MESSAGE_TEXT in message:
        messages_list.append(message)
        return
    # Если клиент выходит:
    elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message:
        clients.remove(names[message[ACCOUNT_NAME]])
        names[message[ACCOUNT_NAME]].close()
        del names[message[ACCOUNT_NAME]]
        return
    else:
        response = RESPONSE_400
        response[ERROR] = 'Запрос некорректен.'
        send_message(client, response)
        return


@log
def arg_parser():
    """Парсер аргументов командной строки."""
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-a', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p

    # Проверка получения корректного номера порта для работы сервера.
    if not 1023 < listen_port < 65535:
        SERVER_LOGGER.critical(
            f'Попытка запуска сервера с неподходящим номером порта: {listen_port}.'
            f' Допустимые адреса с 1024 до 65535. Клиент завершается.'
        )
        sys.exit(1)

    return listen_address, listen_port


@log
def process_message(message, names, listen_socks):
    """
    Функция адресной отправки сообщения определённому клиенту. Принимает словарь-сообщение,
    список зарегистрированых пользователей и слушающие сокеты. Ничего не возвращает.
    :param message:
    :param names:
    :param listen_socks:
    :return:
    """
    if message[DESTINATION] in names and names[message[DESTINATION]] in listen_socks:
        send_message(names[message[DESTINATION]], message)
        SERVER_LOGGER.info(f'Отправлено сообщение пользователю {message[DESTINATION]} '
                           f'от пользователя {message[SENDER]}.')
    elif message[DESTINATION] in names and names[message[DESTINATION]] not in listen_socks:
        raise ConnectionError
    else:
        SERVER_LOGGER.error(f'Пользователь {message[DESTINATION]} не зарегистрирован на сервере. '
                            f'Отправка сообщения невозможна.')


def main():
    """
    Загрузка параметров командной строки.
    Если нет параметров, то задаем значения по умолчанию.
    :return:
    """
    listen_address, listen_port = arg_parser()

    SERVER_LOGGER.info(f'Запущен сервер. Порт для подключений: {listen_port}, '
                       f'адрес, с которого принимаются подключения: {listen_address}. '
                       f'Если адрес не указан, то принимаются соединения с любых адресов.')

    # Готовим сокет.
    transport = socket(AF_INET, SOCK_STREAM)
    transport.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    transport.bind((listen_address, listen_port))
    transport.settimeout(1)

    # Список клиентов, очередь сообщений.
    clients = []
    messages = []

    # Словарь, содержащий имена пользователей и соответствующие им сокеты.
    names = dict()  # {client_name: client_socket}

    # Слушаем порт.
    transport.listen(MAX_CONNECTIONS)

    while True:
        # Ждём подключения, если таймаут вышел, ловим исключение.
        try:
            client, client_address = transport.accept()
        except OSError:
            pass
        else:
            SERVER_LOGGER.info(f'Установлено соединение с ПК {client_address}.')
            clients.append(client)

        recv_data_list = []
        send_data_list = []
        err_list = []

        # Проверяем на наличие ждущих клиентов.
        try:
            if clients:
                recv_data_list, send_data_list, err_list = select.select(clients, clients, [], 0)
        except OSError:
            pass

        # Принимаем сообщения и еcли они есть, то кладем в словарь. В случае ошибки исключаем клиента.
        if recv_data_list:
            for client_with_message in recv_data_list:
                try:
                    process_client_message(get_message(client_with_message),
                                           messages, client_with_message, clients, names)
                except Exception:
                    SERVER_LOGGER.info(f'Клиент {client_with_message.getpeername()} отключился от сервера.')
                    clients.remove(client_with_message)
        # Если есть сообщения, то обрабатываем каждое.
        for i in messages:
            try:
                process_message(i, names, send_data_list)
            except Exception:
                SERVER_LOGGER.info(f'Связь с клиентом с именем {i[DESTINATION]} была потеряна')
                clients.remove(names[i[DESTINATION]])
                del names[i[DESTINATION]]
        messages.clear()


if __name__ == '__main__':
    main()
