"""Конфиг серверного логгера"""
import logging
import os
import sys
import logging.handlers
sys.path.append(os.path.join(os.getcwd(), '..'))
from common.variables import ENCODING, LOGGING_LEVEL

# Создаем объект форматирования:
SERVER_FORMATTER = logging.Formatter('%(asctime)s %(levelname)-8s %(filename)-13s %(message)s')

# Подготовка имени файла для логирования:
PATH = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(PATH, 'server.log')

# Создаем файловый обработчик логирования:
LOG_FILE = logging.handlers.TimedRotatingFileHandler(PATH, when='D', interval=1, encoding=ENCODING)
LOG_FILE.setFormatter(SERVER_FORMATTER)

# Создаем регистратор и настраиваем его:
LOGGER = logging.getLogger('server')
LOGGER.addHandler(LOG_FILE)
LOGGER.setLevel(LOGGING_LEVEL)

if __name__ == '__main__':
    LOGGER.critical('Критическоя ошибка')
    LOGGER.error('Ошибка')
    LOGGER.debug('Отладочная информация')
    LOGGER.info('Информационное сообщение')
