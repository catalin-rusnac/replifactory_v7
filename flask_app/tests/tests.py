# tests.py
import sys

sys.path.insert(0, "..")
sys.path.insert(0, "../experiment")
import unittest
from flask_app.experiment.models import ExperimentModel, Culture
from flask_app.server import create_app, db


class ModelTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        # self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        # self.app.config['TESTING'] = True
        with self.app.app_context():
            db.create_all()
            print(self.app.config['SQLALCHEMY_DATABASE_URI'])

    def tearDown(self):
        with self.app.app_context():
            # db.session.remove()
            # db.drop_all()
            db.session.commit()
            pass

    def create_model(self, model, **kwargs):
        with self.app.app_context():
            instance = model(**kwargs)
            db.session.add(instance)
            db.session.commit()
            return instance.id

    def test_create_experiment(self):
        experiment_id = self.create_model(ExperimentModel, name="Exp22",
                                          parameters={'stock1_volume': 2000, 'stock2_volume': 1000})

        # Query for the Experiment instance in the database
        with self.app.app_context():
            experiment = db.session.get(ExperimentModel, experiment_id)

        self.assertEqual(experiment.name, "Exp22")
        self.assertEqual(experiment.parameters, {'stock1_volume': 2000, 'stock2_volume': 1000})

    def test_create_culture(self):
        experiment_id = self.create_model(ExperimentModel, name="Exp22",
                                          parameters={'stock1_volume': 2000, 'stock2_volume': 1000})
        culture_id = self.create_model(Culture, name="Culture1", experiment_id=experiment_id,
                                       parameters={}, active_parameters={})
        # Query for the Culture instance in the database
        with self.app.app_context():
            culture = db.session.get(Culture, culture_id)
        self.assertEqual(culture.name, "Culture1")

if __name__ == '__main__':
    unittest.main()
