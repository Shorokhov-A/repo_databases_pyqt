import sys
import os
from unittest import TestCase
from unittest.mock import patch
sys.path.append(os.path.join(os.getcwd(), '..'))
from server import process_client_message, get_port, get_address
from common.variables import RESPONSE, ERROR, ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME


class TestServer(TestCase):
    error_dict = {
        RESPONSE: 400,
        ERROR: 'Bad request',
    }
    ok_dict = {RESPONSE: 200}

    def test_ok_check(self):
        self.assertEqual(
            process_client_message({ACTION: PRESENCE, TIME: 1.1, USER: {ACCOUNT_NAME: 'Guest'}}),
            self.ok_dict
        )

    def test_no_action(self):
        self.assertEqual(process_client_message({TIME: 1.1, USER: {ACCOUNT_NAME: 'Guest'}}), self.error_dict)

    def test_wrong_action(self):
        self.assertEqual(
            process_client_message({ACTION: 'Wrong', TIME: 1.1, USER: {ACCOUNT_NAME: 'Guest'}}),
            self.error_dict
        )

    def test_no_time(self):
        self.assertEqual(process_client_message({ACTION: PRESENCE, USER: {ACCOUNT_NAME: 'Guest'}}), self.error_dict)

    def test_no_user(self):
        self.assertEqual(process_client_message({ACTION: PRESENCE, TIME: 1.1}), self.error_dict)

    def test_unknown_user(self):
        self.assertEqual(
            process_client_message({ACTION: PRESENCE, TIME: 1.1, USER: {ACCOUNT_NAME: 'USER'}}),
            self.error_dict
        )

    @patch.object(sys, 'argv', ['server.py', '-p', 8888])
    def test_get_port_ok(self):
        self.assertEqual(get_port(), 8888)

    @patch.object(sys, 'argv', ['server.py', '-p'])
    def test_get_port_no_port(self):
        self.assertRaises(IndexError, get_port)

    @patch.object(sys, 'argv', ['server.py', '-p', 959])
    def test_get_port_wrong_port(self):
        self.assertRaises(ValueError, get_port)

    @patch.object(sys, 'argv', ['server.py', '-a', '127.0.0.1'])
    def test_get_address_ok(self):
        self.assertEqual(get_address(), '127.0.0.1')

    @patch.object(sys, 'argv', ['server.py', '-a'])
    def test_get_address_no_address(self):
        self.assertRaises(IndexError, get_address)
