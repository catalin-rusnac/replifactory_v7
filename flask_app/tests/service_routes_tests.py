# tests.py
import datetime
import random
import sys
import time
import unittest
import json

sys.path.insert(0, "..")
sys.path.insert(0, "../experiment")

from flask_app.server import create_app, db


class RoutesTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        # self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # Use in-memory SQLite database for testing
        # self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            # db.session.remove()
            # db.drop_all()
            db.session.commit()

    def test_capture(self):
        response1 = self.client.get(f'/capture')
        print(response1.get_json())

    def test_update(self):
        response1 = self.client.get(f'/update_software')
        print(response1.get_json())

    def test_update_log(self):
        response1 = self.client.get(f'/update_log')
        print(response1.get_json())

if __name__ == '__main__':
    unittest.main()
