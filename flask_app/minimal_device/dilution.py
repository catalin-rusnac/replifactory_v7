import os
import time


def make_dilution(
    device, vial, pump1_volume=0, pump2_volume=0, pump3_volume=0, extra_vacuum=5
):
    assert 0 <= pump1_volume <= 15
    assert 0 <= pump2_volume <= 15
    assert 0 <= pump3_volume <= 15
    assert 0 <= extra_vacuum <= 15
    assert device.locks_vials[vial].acquire(timeout=60)
    assert device.lock_pumps.acquire(timeout=60)
    # must have been checked before releasing the pump_number lock
    assert not device.is_pumping(), "pumping in progress"
    # assert not device.hard_stop_trigger
    try:
        device.stirrers.set_speed(vial=vial, speed=2)
        time.sleep(1)
        device.valves.open(
            vial
        )  # valve number might be different for e.g. a lagoon setup

        if pump1_volume > 0:
            device.pump1.pump(pump1_volume)
            device.pump1.stock_volume -= pump1_volume
            device.cultures[vial]._time_last_dilution[1] = int(time.time())
        if pump2_volume > 0:
            device.pump2.pump(pump2_volume)
            device.pump2.stock_volume -= pump2_volume
            device.cultures[vial]._time_last_dilution[2] = int(time.time())

        if pump3_volume > 0:
            device.pump3.pump(pump3_volume)
            device.pump3.stock_volume -= pump3_volume
            device.cultures[vial]._time_last_dilution[3] = int(time.time())
        log_dilution(
            device=device,
            vial_number=vial,
            pump1_volume=pump1_volume,
            pump2_volume=pump2_volume,
            pump3_volume=pump3_volume,
        )
        while device.is_pumping():
            time.sleep(0.5)
            assert not device.hard_stop_trigger
        device.stirrers.set_speed(vial=vial, speed=1)
        dilution_volume = pump1_volume + pump2_volume + pump3_volume
        waste_volume = dilution_volume + extra_vacuum
        waste_volume = round(waste_volume, 2)

        device.pump4.pump(waste_volume)
        device.pump4.stock_volume -= dilution_volume
        device.cultures[vial]._time_last_dilution[4] = int(time.time())

        while device.pump4.is_busy():
            time.sleep(0.5)
            assert not device.hard_stop_trigger
        device.stirrers.set_speed(vial=vial, speed=2)
        assert not device.is_pumping()  # make sure before closing valves
        time.sleep(2)
        device.valves.close(valve=vial)

        log_dilution(device=device, vial_number=vial, pump4_volume=waste_volume)

    finally:
        device.locks_vials[vial].release()
        device.lock_pumps.release()
    return 0


def log_dilution(
    device, vial_number, pump1_volume=0, pump2_volume=0, pump3_volume=0, pump4_volume=0
):
    directory = os.path.join(device.directory, "vial_%d" % vial_number)
    if not os.path.exists(directory):
        os.mkdir(directory)
    filepath = os.path.join(directory, "dilutions.csv")
    if not os.path.exists(filepath):
        with open(filepath, "w+") as f:
            f.write("time,pump1_volume,pump2_volume,pump3_volume,pump4_volume\n")
    with open(filepath, "a") as f:
        data_string = str(int(time.time()))
        for vol in [pump1_volume, pump2_volume, pump3_volume, pump4_volume]:
            if vol == 0:
                vol_str = ""
            else:
                vol_str = str(vol)
            data_string += "," + vol_str
        data_string += "\n"
        f.write(data_string)
