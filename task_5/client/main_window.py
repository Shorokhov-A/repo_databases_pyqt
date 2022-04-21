from PyQt5.QtWidgets import QMainWindow, qApp, QMessageBox, QApplication
from PyQt5.QtCore import Qt
import sys
import logging

sys.path.append('../')
from logs import client_log_config
from client.main_window_conv import Ui_MainClientWindow

CLIENT_LOGGER = logging.getLogger('client')


# Класс основного окна
class ClientMainWindow(QMainWindow):
    def __init__(self, database, transport):
        super().__init__()
        # основные переменные
        self.database = database
        self.transport = transport

        # Загружаем конфигурацию окна из дизайнера
        self.ui = Ui_MainClientWindow()
        self.ui.setupUi(self)

        # Кнопка "Выход"
        self.ui.menu_exit.triggered.connect(qApp.exit)

        self.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    from database import ClientDatabase
    database = ClientDatabase('test1')
    from transport import ClientTransport
    transport = ClientTransport(7777, '127.0.0.1', database, 'test1')
    window = ClientMainWindow(database, transport)
    sys.exit(app.exec_())
