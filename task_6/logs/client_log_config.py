"""Конфиг клиентского логгера"""
import logging
import os
import sys
sys.path.append(os.path.join(os.getcwd(), '..'))
from common.variables import ENCODING, LOGGING_LEVEL

# Создаем объект форматирования:
CLIENT_FORMATTER = logging.Formatter('%(asctime)s %(levelname)-8s %(filename)-13s %(message)s')

# Подготовка имени файла для логирования:
PATH = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(PATH, 'client.log')

# Создаем файловый обработчик логирования:
LOG_FILE = logging.FileHandler(PATH, encoding=ENCODING)
LOG_FILE.setFormatter(CLIENT_FORMATTER)

# Создаем регистратор и настраиваем его:
LOGGER = logging.getLogger('client')
LOGGER.addHandler(LOG_FILE)
LOGGER.setLevel(LOGGING_LEVEL)

if __name__ == '__main__':
    LOGGER.critical('Критическоя ошибка')
    LOGGER.error('Ошибка')
    LOGGER.debug('Отладочная информация')
    LOGGER.info('Информационное сообщение')
