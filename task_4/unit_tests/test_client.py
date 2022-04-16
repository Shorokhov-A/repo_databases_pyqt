import sys
import os
from unittest import TestCase
sys.path.append(os.path.join(os.getcwd(), '..'))
from client import create_presence, process_ans
from common.variables import TIME, ACTION, PRESENCE, USER, ACCOUNT_NAME, RESPONSE, ERROR
from errors import ReqFieldMissingError


class TestClient(TestCase):
    def test_create_presence(self):
        presence_test = create_presence()
        presence_test[TIME] = 1.1
        self.assertEqual(presence_test, {ACTION: PRESENCE, TIME: 1.1, USER: {ACCOUNT_NAME: 'Guest'}})

    def test_process_ans_200(self):
        self.assertEqual(process_ans({RESPONSE: 200}), '200 : OK')

    def test_process_ans_400(self):
        self.assertEqual(process_ans({RESPONSE: 400, ERROR: 'Bad request'}), '400 : Bad request')

    def test_no_response(self):
        self.assertRaises(ReqFieldMissingError, process_ans, {ERROR: 'Bad request'})
