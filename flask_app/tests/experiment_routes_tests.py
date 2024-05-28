# tests.py
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

    def test_create_experiment(self):
        name = 'Exp'+str(time.ctime())
        data = {
            'name': name,
            'parameters': {'stock_volume_main': 2000, 'stock_volume_drug': 1000, 'stock_volume_waste': 5000,
                           'stock_concentration_drug': 0.1}
        }
        response = self.client.post('/experiments', data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        response = self.client.get('/experiments').get_json()
        assert name in [exp["name"] for exp in response]

    def test_get_experiment(self):
        response = self.client.get(f'/experiments/1')
        self.assertEqual(response.status_code, 200)

    def test_get_current_experiment(self):
        response1 = self.client.get(f'/experiments/1')
        self.assertEqual(response1.status_code, 200)
        response = self.client.get(f'/experiments/current').get_json()
        self.assertEqual(response["id"], 1)

    def test_direct_update(self):
        with self.app.app_context():
            response = self.client.get(f'/experiments/1')
            parameters = self.app.experiment.parameters
            rand = random.randint(10, 50)/100
            parameters['cultures']["1"]['od_threshold'] = rand
            self.app.experiment.parameters = parameters
            assert self.app.experiment.parameters['cultures']["1"]['od_threshold'] == rand
            assert self.app.experiment.model.parameters['cultures']["1"]['od_threshold'] == rand
            exp = self.client.get(f'/experiments/1').get_json()
            print(rand, exp)
            assert exp['parameters']['cultures']["1"]['od_threshold'] == rand

    def test_update_experiment_parameters(self):
        with self.app.app_context():
            # First, create an experiment
            response = self.client.get(f'/experiments/8')
            self.assertEqual(response.status_code, 200)
            id = response.get_json()["id"]
            parameters = response.get_json()["parameters"]

            rand = random.randint(10, 50)/100
            parameters['cultures']["1"]['od_threshold'] = rand


            response = self.client.put(f'/experiments/current/parameters', data=json.dumps({'parameters': parameters}), content_type='application/json')
            self.assertEqual(response.status_code, 200)
            response = self.client.get(f'/experiments/current')
            parameters = response.get_json()["parameters"]
            self.assertEqual(rand, parameters['cultures']["1"]['od_threshold'])
            # self.app.experiment.cultures[1].get_latest_data_from_db()
            self.assertEqual(rand, self.app.experiment.cultures[1].parameters['od_threshold'])
            self.assertEqual(rand, self.app.experiment.parameters["cultures"]["1"]['od_threshold'])

    def test_start_stop(self):
        response = self.client.get(f'/experiments/1')
        response = self.client.put(f'/experiments/current/status', data=json.dumps({'status': 'running'}),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f'/experiments/current')
        self.assertEqual(response.get_json()["status"], 'running')
        self.client.put(f'/experiments/current/status', data=json.dumps({'status': 'stopped'}),
                        content_type='application/json')

    def test_update_experiment_parameters2(self):
        with self.app.app_context():
            self.client.get(f'/experiments/1')

            response = self.client.get(f'/experiments/current')
            stv = response.get_json()["parameters"]["stock_volume_drug"]
            print(stv, "stock_volume_drug before")
            parameters = self.app.experiment.parameters
            parameters["stock_volume_drug"] = stv - 10
            self.app.experiment.parameters = parameters
            response = self.client.get(f'/experiments/current')
            stv = response.get_json()["parameters"]["stock_volume_drug"]
            print(stv, "stock_volume_drug after")

            response = self.client.get(f'/experiments/current')
            stv = response.get_json()["parameters"]["stock_volume_drug"]
            print(stv, "stock_volume_drug before")
            parameters = self.app.experiment.parameters
            parameters["stock_volume_drug"] = stv - 10
            self.app.experiment.parameters = parameters
            response = self.client.get(f'/experiments/current')
            stv = response.get_json()["parameters"]["stock_volume_drug"]
            print(stv, "stock_volume_drug after")

            response = self.client.get(f'/experiments/current')
            stv = response.get_json()["parameters"]["stock_volume_drug"]
            print(stv, "stock_volume_drug before")
            parameters = self.app.experiment.parameters
            parameters["stock_volume_drug"] = stv - 10
            self.app.experiment.parameters = parameters
            response = self.client.get(f'/experiments/current')
            stv = response.get_json()["parameters"]["stock_volume_drug"]
            print(stv, "stock_volume_drug after")

        def test_update_experiment_parameters3(self):
            response = self.client.get(f'/experiments/current')
            stv = response.get_json()["parameters"]["stock_volume_drug"]
            print(stv, "stock_volume_drug before")
            parameters = self.app.experiment.parameters
            parameters["stock_volume_drug"] = stv - 10
            self.app.experiment.parameters = parameters
            response = self.client.get(f'/experiments/current')
            stv = response.get_json()["parameters"]["stock_volume_drug"]
            print(stv, "stock_volume_drug after")

if __name__ == '__main__':
    unittest.main()
