import sys
import traceback
import logging

sys.path.append('../')
from logs import client_log_config, server_log_config

if sys.argv[0].find('server.py') == -1:
    LOGGER = logging.getLogger('client')
else:
    LOGGER = logging.getLogger('server')


def log(func):
    def decorated(*args, **kwargs):
        func_to_log = func(*args, **kwargs)
        LOGGER.debug(f'Функция {func.__name__}() вызвана из функции {traceback.format_stack()[0].strip().split()[-1]}')
        return func_to_log
    return decorated
