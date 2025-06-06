from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from minimal_device.base_device import BaseDevice
import io
import matplotlib.pyplot as plt
from experiment.experiment_manager import experiment_manager
import time
router = APIRouter()

def get_device() -> BaseDevice:
    device = experiment_manager.get_device()    
    if device is None:
        raise HTTPException(status_code=500, detail="Device not initialized") 
    return device

@router.post("/connect-device")
def connect_device():
    device = experiment_manager.get_device()
    try:
        if device.is_connected():
            device.hello()
            return {"success": True, "device_states": device.device_data}
    except Exception:
        pass
    try:
        device.connect()
        device.hello()
        return {"success": True, "device_states": device.device_data}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/get-all-device-data")
def get_all_device_states(device: BaseDevice = Depends(get_device)):
    try:
        return {"success": True, "device_states": device.device_data}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/rerun-tests")
def rerun_tests(device: BaseDevice = Depends(get_device)):
    device.device_data["ods"]["max_signal"] = {}
    device.device_data["stirrers"]["speed_profiles"] = {}
    device.pump1.test_stepper_drivers(device)
    device.pump1.visual_test_pumps(device)
    r, g, b, l = device.od_sensors[1].measure_optical_signal_max()
    device.od_sensors[1].plot_optical_signals(r, g, b, l)
    [device.rgb_leds.set_led(led_number=v, red=1, green=1, blue=0) for v in range(1, 8)]
    device.stirrers.get_all_calibration_curves()
    device.stirrers.plot_stirrer_calibration_curves(device.device_data["stirrers"]["speed_profiles"])
    [device.rgb_leds.set_led(led_number=v, red=0, green=1, blue=0) for v in range(1, 8)]
    # Camera code omitted for brevity
    return {"success": True}

@router.get("/run-ods-test")
def ods_test(device: BaseDevice = Depends(get_device)):
    max_signals = device.od_sensors[1].measure_optical_signal_max()
    return {"success": True, "max_signals": max_signals}

@router.get("/run-stirrer-test")
def stirrer_test(device: BaseDevice = Depends(get_device)):
    data = device.stirrers.get_all_calibration_curves()
    return data

@router.post("/set-{devicePart}-state")
def set_device_state(devicePart: str, payload: dict, device: BaseDevice = Depends(get_device)):
    part_index = payload['partIndex']
    new_state = payload['newState']
    device.device_data[devicePart]['states'][part_index] = new_state
    if devicePart == 'valves':
        print(f'Toggled valve {part_index} to {new_state}')
        if new_state == 'open':
            device.valves.open(part_index)
        elif new_state == 'closed':
            device.valves.close(part_index)
        device.eeprom.save_config_to_eeprom()
    elif devicePart == 'pumps':
        print(f'Toggled pump {part_index} to {new_state}')
        volume = None
        if new_state == 'running':
            if 'input' in payload and 'volume' in payload['input']:
                volume = float(payload['input']['volume'])
                device.pumps[part_index].pump(volume)
            elif 'input' in payload and 'rotations' in payload['input']:
                rotations = float(payload['input']['rotations'])
                device.pumps[part_index].move(rotations)
            while device.pumps[part_index].is_pumping():
                time.sleep(0.2)
            # Optionally adjust stock volume if needed (implement adjust_stock_volume if required)
        elif new_state == 'stopped':
            if device.pumps[part_index].is_pumping():
                device.pumps[part_index].stop()
                print("Actively stopped pump", part_index)
    elif devicePart == 'stirrers':
        time.sleep(0.01)
        device.stirrers.set_speed(part_index, new_state)
    return {"success": True, "newState": new_state}

@router.post("/measure-{devicePart}")
def measure_device_part(devicePart: str, payload: dict, device: BaseDevice = Depends(get_device)):
    partIndex = int(payload['partIndex'])
    if devicePart == 'ods':
        od, signal = device.od_sensors[partIndex].measure_od()
        device.device_data[devicePart]['states'][partIndex] = od
        device.device_data[devicePart]['odsignals'][partIndex] = signal
    elif devicePart == 'thermometers':
        t_vials, t_board = device.thermometers.measure_temperature()
        device.device_data[devicePart]['states'] = {1: t_vials, 2: t_board}
    return {"success": True, "device_states": device.device_data}

@router.get("/get-stirrer-speeds")
def get_stirrer_speed(device: BaseDevice = Depends(get_device)):
    speeds = device.stirrers.measure_all_rpms()
    plt.close()
    plt.bar(speeds.keys(), speeds.values())
    plt.ylim(0, max(max(speeds.values())*1.1, 5000))
    plt.ylabel('RPM')
    plt.xlabel('Vial')
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close()
    return StreamingResponse(img, media_type="image/png")

@router.post("/set-{devicePart}-calibration")
def set_part_calibration(devicePart: str, payload: dict, device: BaseDevice = Depends(get_device)):
    partIndex = int(payload.get('partIndex'))
    newCalibration = payload.get('newCalibration')
    # implement logic to update the device part calibration based on `devicePart`, `partIndex`, and `newCalibration`
    # print(f'Set {devicePart} {partIndex} calibration to {newCalibration}')
    if devicePart == 'ods':
        # If you have a fix_dict_keys_from_javascript function, use it here
        # newCalibration = fix_dict_keys_from_javascript(newCalibration)
        pass
    device.device_data[devicePart]['calibration'][partIndex] = newCalibration
    if devicePart == 'ods':
        device.od_sensors[partIndex].fit_calibration_function()
    if devicePart == 'stirrers':
        speed = device.device_data['stirrers']['states'][partIndex]
        device.stirrers.set_speed(partIndex, speed, accelerate=False)
        print("Calibrated and set stirrer speed to", speed)
        device.eeprom.save_config_to_eeprom()

    response = {"success": True, "newCalibration": newCalibration}
    if devicePart == 'ods':
        response["coefs"] = device.device_data['ods']['calibration_coefs'][partIndex]
    return response

# Add more routes as needed, following the same pattern.