# tests.py
import datetime
import random
import sys
import time
import unittest
import json
from pprint import pprint
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

    def test_get_current_experiment(self):
        response1 = self.client.get(f'/experiments/8')
        self.assertEqual(response1.status_code, 200)
        response = self.client.get(f'/experiments/current').get_json()
        self.assertEqual(response["id"], 1)

    def test_culture(self):
        response1 = self.client.get(f'/experiments/1')
        c=self.app.experiment.cultures[3]
        with self.app.app_context():
            c.get_latest_data_from_db()
            # "2023-06-11 06:36:38.958148"
            # parse
            # timepoint = datetime.datetime.strptime("2023-06-12 0:38:38.958148", "%Y-%m-%d %H:%M:%S.%f")
            # c.get_data_at_timepoint(timepoint)
        pprint(c.__dict__)
        pprint(c.get_info())


if __name__ == '__main__':
    unittest.main()
