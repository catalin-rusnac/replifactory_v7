from flask import Blueprint, request, jsonify, current_app
import time
import sys
sys.path.insert(0, '..')
from minimal_device.device_data import default_device_data
from minimal_device.base_device import BaseDevice

device_routes = Blueprint('device_routes', __name__)

@device_routes.route('/set-<string:devicePart>-state', methods=['POST'])
def set_device_state(devicePart):
    part_index = request.json['partIndex']
    new_state = request.json['newState']
    dev.device_data[devicePart]['states'][part_index] = new_state
    if devicePart == 'valves':
        print(f'Toggled valve {part_index} to {new_state}')
        if new_state=='open':
            dev.valves.open(part_index)
        elif new_state=='closed':
            dev.valves.close(part_index)

    elif devicePart == 'pumps':
        print(f'Toggled pump {part_index} to {new_state}')
        # print(request.json)
        if new_state=='running':
            if 'volume' in request.json['input']:
                volume = float(request.json['input']['volume'])
                dev.pumps[part_index].pump(volume)
            elif 'rotations' in request.json['input']:
                rotations = float(request.json['input']['rotations'])
                dev.pumps[part_index].move(rotations)
            while dev.pumps[part_index].is_pumping():
                time.sleep(0.2)
        elif new_state=='stopped':
            if dev.pumps[part_index].is_pumping():
                dev.pumps[part_index].stop()
                print("Actively stopped pump", part_index)
        # volume = request.json['input']
        # dev.pumps[part_index].pump(volume)

    elif devicePart == 'stirrers':
        time.sleep(0.01)
        # print(f'Toggled stirrer {part_index} to {new_state}')
        dev.stirrers.set_speed(part_index, new_state)

    if devicePart == 'valves':
        dev.eeprom.save_config_to_eeprom()

    return jsonify({'success': True, 'newState': new_state})

@device_routes.route('/measure-<string:devicePart>', methods=['POST'])
def measure_device_part(devicePart):
    partIndex = int(request.json['partIndex'])
    if devicePart == 'ods':
        # print(f'Measuring OD {partIndex}')
        od, signal = dev.od_sensors[partIndex].measure_od()
        # od_value = random.randint(0, 100)
        dev.device_data[devicePart]['states'][partIndex] = od
        dev.device_data[devicePart]['odsignals'][partIndex] = signal
    elif devicePart == 'thermometers':
        t_vials, t_board = dev.thermometers.measure_temperature()
        dev.device_data[devicePart]['states'] = {1: t_vials, 2: t_board}
    return jsonify({'success': True, 'device_states': dev.device_data})


@device_routes.route('/get-all-device-data', methods=['GET'])
def get_all_device_states():
    print("Getting all device data")
    try:
        return jsonify({
        'success': True,
        'device_states': dev.device_data,
    })
    except:
        return jsonify({
        'success': False,
        'device_states': default_device_data,
    })


def fix_dict_keys_from_javascript(dict):
    new_dict = {}
    if dict is None:
        return None
    for key in dict:
        try:
            new_dict[float(key)] = dict[key]
        except:
            pass

    return new_dict


@device_routes.route('/set-<string:devicePart>-calibration', methods=['POST'])
def set_part_calibration(devicePart):
    data = request.get_json()
    partIndex = int(data.get('partIndex'))
    newCalibration = data.get('newCalibration')
    # implement logic to update the device part calibration based on `devicePart`, `partIndex`, and `newCalibration`
    # print(f'Set {devicePart} {partIndex} calibration to {newCalibration}')
    if devicePart == 'ods':
        newCalibration = fix_dict_keys_from_javascript(newCalibration)
    dev.device_data[devicePart]['calibration'][partIndex] = newCalibration
    if devicePart == 'ods':
        dev.od_sensors[partIndex].fit_calibration_function()
    if devicePart == 'stirrers':
        speed = dev.device_data['stirrers']['states'][partIndex]
        dev.stirrers.set_speed(partIndex, speed, accelerate=False)
        print("Calibrated and set stirrer speed to", speed)
        dev.eeprom.save_config_to_eeprom()

    response = jsonify(success=True, newCalibration=newCalibration)
    if devicePart == 'ods':
        response = jsonify(success=True, newCalibration=newCalibration, coefs=dev.device_data['ods']['calibration_coefs'][partIndex])
    return response


@device_routes.route('/measure-od-calibration', methods=['POST'])
def measure_od_calibration():
    data = request.get_json()
    odValue = data.get('odValue')
    odValue = float(odValue)
    print(f'Measuring OD calibration with OD {odValue}')
    for v in range(1,8):
        dev.od_sensors[v].measure_od_calibration(odValue)
    for v in range(1,8):
        dev.od_sensors[v].fit_calibration_function()
    dev.eeprom.save_config_to_eeprom()
    return jsonify(success=True, odValue=odValue)


@device_routes.route('/start-pump-calibration-sequence', methods=['POST'])
def start_pump_calibration_sequence():
    data = request.get_json()
    print(data)
    pumpId = data.get('pumpId')
    rotations = data.get('rotations')
    iterations = data.get('iterations')
    print(f'Starting pump {pumpId} calibration sequence with {rotations} rotations and {iterations} iterations')

    if dev.valves.all_closed():
        return jsonify(success=False, error="All valves are closed")
    dev.device_data['pumps']['states'][pumpId] = 'running'
    for i in range(iterations):
        if dev.device_data['pumps']['states'][pumpId] == 'stopped':
            break
        dev.pumps[pumpId].move(rotations)
        while dev.pumps[pumpId].is_pumping():
            time.sleep(0.1)
        time.sleep(0.5)
    return jsonify(success=True)


@device_routes.route('/force-connect-device', methods=['POST', 'GET'])
def force_connect_device():
    print("Force connecting device")
    global dev
    try:
        if dev.is_connected():
            dev.disconnect_all()
            dev.connect()
            dev.hello()
            return jsonify({'success': True, 'device_states': dev.device_data})
    except:
        print("Device not connected")
        pass

    try:
        print("Connecting device")
        dev = BaseDevice(connect=True)
        try:
            dev.hello()
        except Exception as e:
            print("Device connection failed, trying again", e)
            dev.connect() # try again
            dev.hello()
        current_app.dev = dev
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    return

@device_routes.route('/connect-device', methods=['POST', 'GET'])
def connect_device():
    global dev
    current_app.dev = None
    try:
        if dev.is_connected():
            return jsonify({'success': True, 'device_states': dev.device_data})
        elif dev.is_connected() == False:
            dev.disconnect_all()
    except:
        print("Device not connected")
        pass
    try:
        print("Connecting device")

        dev = BaseDevice(connect=True)
        try:
            dev.hello()
        except Exception as e:
            print("Device connection failed, trying again", e)
            dev.connect()  # try again
            dev.hello()
        current_app.dev = dev

        # dev.device_data = default_device_data
        # print("sample device data", default_device_data)
        # for v in range(1,8):
        #     dev.od_sensors[v].fit_calibration_function()
        # dev.eeprom.save_config_to_eeprom()
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    return jsonify({'success': True, 'device_states': dev.device_data})
