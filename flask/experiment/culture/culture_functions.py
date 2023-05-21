import time


def inoculate(culture, name=None, description=None):
    assert culture._inoculation_time is None, "Vial already inoculated"
    if name is not None:
        culture.name = name
    if description is not None:
        culture.description = description
    culture._inoculation_time = int(time.time())


# def is_active(culture):
#     return np.isfinite(np.float32(culture._inoculation_time)) and not culture._is_aborted


def dilute_adjust_drug1(
    culture,
    dilution_factor=None,
    stress_increase_factor=None,
    target_concentration=None,
):
    if dilution_factor is None:
        dilution_factor = (
            culture.dead_volume + culture.default_dilution_volume
        ) / culture.dead_volume
    total_volume = culture.dead_volume + culture.default_dilution_volume
    if target_concentration is None:
        if stress_increase_factor is None:
            stress_increase_factor = (dilution_factor + 1) / 2
        medium2_target_concentration = (
            culture.medium2_concentration * stress_increase_factor
        )
        if culture.medium2_concentration == 0:
            medium2_target_concentration = culture.device.pump2.stock_concentration / 50
    else:
        medium2_target_concentration = target_concentration

    # medium3_target_concentration = None

    drug1_total_amount = total_volume * medium2_target_concentration
    drug1_current_amount = culture.dead_volume * culture.medium2_concentration
    drug1_pumped_amount = drug1_total_amount - drug1_current_amount
    drug1_pumped_volume = drug1_pumped_amount / culture.device.pump2.stock_concentration
    drug1_pumped_volume = round(drug1_pumped_volume, 3)
    drug1_pumped_volume = min(
        culture.default_dilution_volume, max(0.1, drug1_pumped_volume)
    )
    if target_concentration == 0:
        drug1_pumped_volume = 0
    # drug2_pumped_volume = 0
    # if medium3_target_concentration:
    #     drug2_total_amount = total_volume * medium3_target_concentration
    #     drug2_current_amount = self.dead_volume * self.medium3_concentration
    #     drug2_pumped_amount = drug2_total_amount - drug2_current_amount
    #     drug2_pumped_volume = drug2_pumped_amount / self.device.pump3.stock_concentration
    #     drug2_pumped_volume = min(self.default_dilution_volume, max(0, drug2_pumped_volume))

    drugfree_medium_volume = (
        culture.default_dilution_volume - drug1_pumped_volume
    )  # - drug2_pumped_volume
    drugfree_medium_volume = min(
        culture.default_dilution_volume, max(0, drugfree_medium_volume)
    )
    culture._last_dilution_start_time = time.time()
    culture.dilute(
        pump1_volume=drugfree_medium_volume, pump2_volume=drug1_pumped_volume
    )

    # def lower_od(self):
    #     """
    #     makes a dilution, preserving the drug concentration in the vial
    #     :return:
    #     """
    #     medium2_target_concentration = self.medium2_concentration
    #     total_volume = self.dead_volume + self.default_dilution_volume
    #
    #     drug1_total_amount = total_volume * medium2_target_concentration
    #     drug1_current_amount = self.dead_volume * self.medium2_concentration
    #     drug1_pumped_amount = drug1_total_amount - drug1_current_amount
    #     drug1_pumped_volume = drug1_pumped_amount / self.device.pump2.stock_concentration
    #     drug1_pumped_volume = min(self.default_dilution_volume, max(0, drug1_pumped_volume))
    #     if drug1_pumped_volume < 0.05:
    #         drug1_pumped_volume = 0
    #
    #     drugfree_medium_volume = self.default_dilution_volume - drug1_pumped_volume  # - drug2_pumped_volume
    #     drugfree_medium_volume = min(self.default_dilution_volume, max(0, drugfree_medium_volume))
    #
    #     self.dilute(pump1_volume=drugfree_medium_volume,
    #                 pump2_volume=drug1_pumped_volume)
