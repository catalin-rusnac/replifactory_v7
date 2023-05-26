import numpy as np
from ipywidgets import interact

from replifactory.culture.culture_functions import dilute_adjust_drug1
from replifactory.culture.turbidostat import TurbidostatCulture


class StressRampCulture(TurbidostatCulture):
    """
    Class for subjecting the culture to a constantly increasing stress level (e.g. 5% per generation)
    """

    pumps = (1, 2, 4)

    def __init__(
        self,
        directory: str = None,
        vial_number: int = None,
        name: str = "Species 1",
        description: str = "Strain 1",
        default_dilution_volume: float = 10,
        dead_volume: float = 15,
        od_max_limit: float = 0.3,
        stress_increase_per_generation: float = 1.05,
        initial_generations: float = 3,
    ):
        self.initial_generations = initial_generations
        self.initial_stress = 3
        self.stress_increase_per_generation = stress_increase_per_generation
        super().__init__(
            directory=directory,
            vial_number=vial_number,
            name=name,
            description=description,
            default_dilution_volume=default_dilution_volume,
            dead_volume=dead_volume,
            od_max_limit=od_max_limit,
        )
        self.active_pumps = (1, 2, 4)

    def update(self):
        if not self.is_active():
            return

        if self.diluting_like_crazy:
            return

        if self.od < self.od_max_limit:
            return

        if self._log2_dilution_coefficient < self.initial_generations:
            self.dilute_lower_od()
            return
        if self.medium2_concentration < self.initial_stress:
            self.set_stress(self.initial_stress)
            return
        else:
            self.increase_stress()
            return

    #
    # def update(self):
    #     if self.is_active():
    #         if self.od > self.od_max_limit:
    #             if not self.diluting_like_crazy:
    #                 if self._log2_dilution_coefficient > self.initial_generations:
    #                     if self.medium2_concentration < self.initial_stress:
    #                         self.set_stress(self.initial_stress)
    #                     else:
    #                         self.increase_stress()
    #
    #                 else:
    #                     self.lower_od()

    def set_stress(self, stress_level):
        dilute_adjust_drug1(culture=self, target_concentration=stress_level)

    def check(self):
        super(StressRampCulture, self).check()
        dilution_factor = (
            self.dead_volume + self.default_dilution_volume
        ) / self.dead_volume
        assert self.stress_increase_per_generation < dilution_factor

    def increase_stress(self):
        dilution_factor = (
            self.dead_volume + self.default_dilution_volume
        ) / self.dead_volume
        generations_per_dilution = np.log2(dilution_factor)
        stress_increase_per_dilution = (
            generations_per_dilution * (self.stress_increase_per_generation - 1) + 1
        )
        dilute_adjust_drug1(
            culture=self, stress_increase_factor=stress_increase_per_dilution
        )

    @staticmethod
    def interactive_demo():
        @interact(
            doubling_time=(0, 12, 0.1),
            initial_dose=(0, 0.5, 0.01),
            factor=(1, 1.5, 0.01),
            MIC=(0.1, 15, 0.1),
        )
        def interactive_function(t_doubling=3, initial_dose=0.25, factor=1.1, MIC=5):
            generations_per_day = 24 / t_doubling
            factor_per_day = factor**generations_per_day

            print("         Doubling time: %.1f hours" % t_doubling)
            print("                   MIC: %.1f" % MIC + "% " + "ethanol")
            print("          Initial dose: %.2f of MIC" % initial_dose)
            print(
                "Stress increase factor: %.2f per generation," % factor,
                "%.3f per day" % factor_per_day,
            )

            # generations_to_mic = np.log(1 / initial_dose) / np.log(factor)
            # print("MIC reached in %.1f generations" % generations_to_mic)
            for ngen in [10, 20, 30, 40, 50]:
                dose_gen = initial_dose * factor**ngen
                n_days = t_doubling * ngen / 24
                print(
                    "    Generation %d" % ngen,
                    "dose: %.2f x MIC" % dose_gen,
                    "(%.1f days)" % n_days,
                )

            print("\nExample:")
            print(
                "Dose at every generation:\n",
                ", ".join(
                    str(x)
                    for x in np.round(MIC * initial_dose * factor ** np.arange(21), 2)
                ),
            )
