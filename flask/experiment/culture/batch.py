import os

import numpy as np

from replifactory.culture.blank import BlankCulture


class BatchCulture(BlankCulture):
    """Batch culture, measures OD every minute. Pumps deactivated."""

    pumps = []

    def __init__(
        self,
        directory: str = None,
        vial_number: int = None,
        name: str = "Species 1",
        description: str = "Strain 1",
    ):
        # Running parameters
        self._mu = None
        self._mu_error = None
        self._t_doubling = None
        self._t_doubling_error = None
        self._inoculation_time = None
        self._samples_collected = {}
        self._is_active = False
        self._mu_max_measured = 0
        self._t_doubling_min_measured = np.inf
        super().__init__(
            directory=directory,
            vial_number=vial_number,
            name=name,
            description=description,
        )
        del self.dead_volume

    def description_text(self):
        t = """
Batch culture, measures OD every minute. Pumps deactivated.
        """
        return t

    def update(self):
        pass

    def check(self):
        assert self.device.is_connected()
        assert self.vial_number in [1, 2, 3, 4, 5, 6, 7]
        assert os.path.exists(self.directory)
        self.device.stirrers.check_calibration(self.vial_number)
        assert callable(self.device.od_sensors[self.vial_number].calibration_function)
        assert -0.3 < self.od_blank < 0.3
