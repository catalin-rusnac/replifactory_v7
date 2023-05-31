import time

from replifactory.culture.culture_functions import dilute_adjust_drug1
from replifactory.culture.turbidostat import TurbidostatCulture


class PatientCulture(TurbidostatCulture):
    """
    class that simulates a patient taking antibiotics
    """

    active_pumps = (1, 2, 4)

    def __init__(
        self,
        directory: str = None,
        vial_number: int = None,
        name: str = "Patient",
        description: str = "Patient description",
        default_dilution_volume: float = 10,
        dead_volume: float = 15,
    ):
        super().__init__(
            directory=directory,
            vial_number=vial_number,
            name=name,
            description=description,
            default_dilution_volume=default_dilution_volume,
            dead_volume=dead_volume,
        )
        self._treatment_started = False
        self._treatment_start_time = None
        self._treatment_stop_time = None
        self._current_drug_dose = 0
        self.od_threshold_treatment_start = 1.0
        self.od_threshold_dose_increase = 0
        self.dilution_period_hrs = 1.0
        self.treatment_dose = 40
        self.treatment_duration_hrs = 24
        self.treatment_dose_increase_delay_hrs = 0

        if hasattr(self, "od_max_limit"):
            del self.od_max_limit

        # self.text = "Every 1 hours the 15 ml vial is diluted by adding 10ml and removing 10ml of clean medium." \
        #             "If OD>1, treatment begins, the drug concentration in the vial is set to 40mM and " \
        #             "maintained for 24h. After the treatment ends the dilutions are made with clean medium and " \
        #             "the drug concentration in the vial lowers with every dilution"

    def update(self):
        if self.is_active():
            if not bool(self._treatment_started):
                if (
                    self.od > self.od_threshold_treatment_start
                ):  # trigger treatment start
                    self._treatment_started = True
                    self._current_drug_dose = self.treatment_dose
                    self._treatment_start_time = time.time()
                    self._treatment_stop_time = (
                        self._treatment_start_time + 3600 * self.treatment_duration_hrs
                    )
                    self.make_patient_dilution()

            else:
                if time.time() > self._treatment_stop_time:  # stop treatment, zero dose
                    self._current_drug_dose = 0
                if self.treatment_dose_increase_delay_hrs > 0:
                    # new dose
                    if (
                        time.time() - self.treatment_dose_increase_delay_hrs * 3600
                        > self._treatment_start_time
                    ):
                        if self.od > self.od_threshold_dose_increase:
                            self._current_drug_dose *= 2
                            self._treatment_start_time = time.time()
                            self._treatment_stop_time = (
                                self._treatment_start_time
                                + 3600 * self.treatment_duration_hrs
                            )
            if self.minutes_since_last_dilution > 60 * self.dilution_period_hrs:
                self.make_patient_dilution()

    def make_patient_dilution(self):
        dilute_adjust_drug1(culture=self, target_concentration=self._current_drug_dose)

    def check(self):
        super(TurbidostatCulture, self).check()
        assert self.treatment_dose <= self.device.pump2.stock_concentration
