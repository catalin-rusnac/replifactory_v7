
class Culture:
    def __int__(self, experiment,vial):
        self.experiment = experiment
        self.vial = vial
    def update(self):
        self.measure_od_and_store_to_db()
        self.calcualte_growth_rate_and_store_to_db()
        if self.current_od > self.experiment.model.cultures[self.vial]["od_threshold"]:
                self.make_dilution()
        if self.time_to_rescue and self.growing_too_slow:
            self.lower_od_decrease_stress()

    def make_dilution(self):
        if self.current_growth_rate > self.experiment.model.cultures[self.vial]["stress_increase_tdoubling_min_hrs"]:
        #     increase stress
            pass
        elif self.current_growth_rate < self.experiment.model.cultures[self.vial]["stress_decrease_tdoubling_max_hrs"]:
            # decrease stress
            pass
        else:
            # lower od, keep stress constant
            pass