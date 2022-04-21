"""Утилиты"""
import json
import sys
import os
from common.variables import MAX_PACKAGE_LENGTH, ENCODING

sys.path.append(os.path.join(os.getcwd(), '..'))
from common.decorators import log
from common.errors import IncorrectDataReceivedError, NoDictInputError


@log
def get_message(client):
    """
    Утилита приема и декодирования сообщения.
    Принимает байты и выдает словарь. Если принято что-то другое, то отдает ошибку значения.
    :param client:
    :return:
    """
    encoded_response = client.recv(MAX_PACKAGE_LENGTH)
    if isinstance(encoded_response, bytes):
        json_response = encoded_response.decode(ENCODING)
        response = json.loads(json_response)
        if isinstance(response, dict):
            return response
        raise IncorrectDataReceivedError
    raise IncorrectDataReceivedError


@log
def send_message(sock, message):
    """
    Утилита кодирования и отправки сообщения.
    Принимает словарь и отправляет его.
    :param sock:
    :param message:
    :return:
    """
    if not isinstance(message, dict):
        raise NoDictInputError
    json_message = json.dumps(message)
    encoded_message = json_message.encode(ENCODING)
    sock.send(encoded_message)
