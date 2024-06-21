import os
import time


def make_dilution(
    device, vial, pump1_volume=0, pump2_volume=0, pump3_volume=0, extra_vacuum=5
):
    assert 0 <= pump1_volume <= 20
    assert 0 <= pump2_volume <= 20
    assert 0 <= pump1_volume + pump2_volume <= 25
    assert 0 <= pump3_volume <= 20
    assert 0 <= extra_vacuum <= 20

    vial_lock_acquired = device.locks_vials[vial].acquire(timeout=10)
    if not vial_lock_acquired:
        raise Exception("Could not acquire lock for vial %d at time %s" % (vial, time.ctime()))

    lock_pumps_acquired = device.lock_pumps.acquire(timeout=10)
    if not lock_pumps_acquired:
        device.locks_vials[vial].release()
        raise Exception("Could not acquire lock for pumps at time %s" % time.ctime())

    try:
        assert not device.is_pumping(), "pumping in progress"
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