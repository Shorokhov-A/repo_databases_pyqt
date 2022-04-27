import logging
import logs.server_log_config
LOGGER = logging.getLogger('server')


class Port:
    """
     Класс - дескриптор для номера порта.
    Позволяет использовать только порты с 1023 по 65536.
    При попытке установить неподходящий номер порта генерирует исключение.
    """
    def __set__(self, instance, value):
        # Проверка получения корректного номера порта для работы сервера.
        if not 1023 < value < 65535:
            LOGGER.critical(
                f'Попытка запуска сервера с неподходящим номером порта: {value}.'
                f' Допустимые адреса с 1024 до 65535. Клиент завершается.'
            )
            exit(1)
        # Если порт прошёл проверку, добавляем его в список атрибутов экземпляра
        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name
