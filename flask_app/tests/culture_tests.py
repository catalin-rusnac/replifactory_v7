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
        response1 = self.client.get(f'/experiments/1')
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

    def test_new_update(self):
        from experiment.ModelBasedCulture.morbidostat_updater import MorbidostatUpdater
        from experiment.ModelBasedCulture.real_culture_wrapper import RealCultureWrapper

        updater = MorbidostatUpdater(
            od_dilution_threshold=0.3,  # OD at which dilution occurs
            dilution_factor=1.5,  # Factor by which the population is reduced during dilution
            dilution_number_initial_dose=1,  # Number of dilutions before adding the drug
            dose_initial_added=6.2,  # Initial dose added to the culture
            dose_increase_factor=1.3,  # Factor by which the dose is increased at stress increases after the initial one
            threshold_growth_rate_increase_stress=0.15,  # Min growth rate threshold for stress increase
            threshold_growth_rate_decrease_stress=0.005,  # Max growth rate threshold for stress decrease
            delay_dilution_max_hours=6,  # Maximum time between dilutions
            delay_stress_increase_min_generations=3,  # Minimum generations between stress increases
            volume_vial=12,  # Volume of the vial
            pump1_stock_drug_concentration=0,  # Concentration of the drug in the pump 1 stock
            pump2_stock_drug_concentration=300)

        response1 = self.client.get(f'/experiments/8')
        print(response1.get_json())
        culture=self.app.experiment.cultures[3]
        print(culture.__dict__)
        with self.app.app_context():
            culture.get_latest_data_from_db()
            adapted_culture = RealCultureWrapper(culture)
            for i in range(3):
                updater.update(adapted_culture)
        pprint(culture.__dict__)

    def test_plot_model(self):
        response1 = self.client.get(f'/experiments/8')
        print(response1.get_json())
        culture=self.app.experiment.cultures[3]
        print(culture.__dict__)
        with self.app.app_context():
            culture.get_latest_data_from_db()
        fig=culture.plot_predicted()
        import plotly.io as pio
        pio.show(fig)
if __name__ == '__main__':
    unittest.main()
