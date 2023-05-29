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
        device.stirrers.set_speed(vial=vial, speed="high")
        time.sleep(0.2)
        device.valves.open(vial)

        if pump1_volume > 0:
            device.pump1.pump(pump1_volume)
        if pump2_volume > 0:
            device.pump2.pump(pump2_volume)
        if pump3_volume > 0:
            device.pump3.pump(pump3_volume)

        while device.is_pumping():
            time.sleep(0.5)
            assert not device.hard_stop_trigger

        device.stirrers.set_speed(vial=vial, speed="low")

        dilution_volume = pump1_volume + pump2_volume + pump3_volume
        waste_volume = dilution_volume + extra_vacuum
        device.pump4.pump(waste_volume)
        vacuum_time_0 = time.time()
        stirrer_stopped = False
        while device.pump4.is_busy():
            time.sleep(0.5)
            if time.time() - vacuum_time_0 > 3 and not stirrer_stopped:
                device.stirrers.set_speed(vial=vial, speed="stopped")
                stirrer_stopped = True
            assert not device.hard_stop_trigger
        device.stirrers.set_speed(vial=vial, speed="high")
        assert not device.is_pumping()  # make sure before closing valves
        time.sleep(2)
        device.valves.close(valve=vial)
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
