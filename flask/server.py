import logging
import random
import time

from waitress import serve
from flask import Flask, request, jsonify, render_template, make_response, current_app
# cors
from flask_cors import CORS, cross_origin
import logging
import os
import signal
from minimal_device.device_data import device_data as sample_device_data
from minimal_device.base_device import BaseDevice


# setup logging to file, create file if it doesn't exist
if not os.path.exists('data'):
    os.makedirs('data')
if not os.path.exists('data/flask.log'):
    with open('data/flask.log', 'w') as f:
        f.write('')
logging.basicConfig(filename='data/flask.log', level=logging.INFO, format='%(asctime)s %(message)s')


app = Flask(__name__)
CORS(app)
global dev

# try:
#     dev = BaseDevice(connect=True)
#     dev.hello()
# except Exception as e:
#     print(e)
#     print("Could not connect to device")
#     dev = None

pid = os.getpid()
with open("data/flask_app.pid", "w") as pid_file:
    pid_file.write(str(pid))


@app.route('/')
def index():
    return render_template('public/index.html')


@app.route('/set-<string:devicePart>-state', methods=['POST'])
def set_device_state(devicePart):
    part_index = request.json['partIndex']
    new_state = request.json['newState']
    dev.device_data[devicePart]['states'][part_index] = new_state
    if devicePart == 'valves':
        print(f'Toggled valve {part_index} to {new_state} and slept')
        if new_state=='open':
            dev.valves.open(part_index)
        elif new_state=='closed':
            dev.valves.close(part_index)

    elif devicePart == 'pumps':
        print(f'Toggled pump {part_index} to {new_state} and slept')
        print(request.json)
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
        print(f'Toggled stirrer {part_index} to {new_state} and slept')
        dev.stirrers.set_speed(part_index, new_state)

    if devicePart == 'valves':
        dev.eeprom.save_config_to_eeprom()

    return jsonify({'success': True, 'newState': new_state})

# @app.route('/pump-<string:pumpId>', methods=['POST'])
# def pump(pumpId):
#     volume = request.json['volume']
#     print(f'Pumping {volume} from pump {pumpId}')
#     dev.pumps[int(pumpId)].pump(volume)
#     return jsonify({'success': True})

@app.route('/measure-<string:devicePart>', methods=['POST'])
def measure_device_part(devicePart):
    partIndex = int(request.json['partIndex'])
    if devicePart == 'ods':
        print(f'Measuring OD {partIndex} and sleeping')
        od, signal = dev.od_sensors[partIndex].measure_od()
        # od_value = random.randint(0, 100)
        dev.device_data[devicePart]['states'][partIndex] = od
        dev.device_data[devicePart]['odsignals'][partIndex] = signal

    # elif devicePart == 'temperature':
    #     device_data[devicePart][partIndex] = random.randint(0, 100)
    # elif devicePart == 'pumps':
    #     device_data[devicePart]['volume'][partIndex] = random.randint(0, 100)
    # elif devicePart == 'stirrers':
    #     device_data[devicePart]['states'][partIndex] = random.randint(0, 100)
    # elif devicePart == 'valves':
    #     device_data[devicePart]['states'][partIndex] = random.randint(0, 100)
    return jsonify({'success': True, 'device_states': dev.device_data})


@app.route('/get-all-device-data', methods=['GET'])
def get_all_device_states():
    print("Getting all device data")
    print(dev.device_data)

    return jsonify({
        'success': True,
        'device_states': dev.device_data,
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


@app.route('/set-<string:devicePart>-calibration', methods=['POST'])
def set_part_calibration(devicePart):
    data = request.get_json()
    partIndex = int(data.get('partIndex'))
    newCalibration = data.get('newCalibration')
    # implement logic to update the device part calibration based on `devicePart`, `partIndex`, and `newCalibration`
    print(f'Set {devicePart} {partIndex} calibration to {newCalibration}')
    if devicePart == 'ods':
        newCalibration = fix_dict_keys_from_javascript(newCalibration)
    dev.device_data[devicePart]['calibration'][partIndex] = newCalibration
    if devicePart == 'stirrers':
        speed = dev.device_data['stirrers']['states'][partIndex]
        dev.stirrers.set_speed(partIndex, speed, accelerate=False)
        print("Calibrated and set stirrer speed to", speed)

    if not (devicePart == 'ods' and partIndex < 7):
        dev.eeprom.save_config_to_eeprom()
    else:
        print("Not saving to EEPROM because it's an OD sensor<7")
    return jsonify(success=True, newCalibration=newCalibration)


@app.route('/measure-od-calibration', methods=['POST'])
def measure_od_calibration():
    data = request.get_json()
    odValue = data.get('odValue')
    print(odValue,type(odValue))
    odValue = float(odValue)
    print(f'Measuring OD calibration with {odValue}')
    for v in range(1,8):
        dev.od_sensors[v].measure_od_calibration(odValue)
    dev.eeprom.save_config_to_eeprom()
    return jsonify(success=True, odValue=odValue)

@app.route('/start-pump-calibration-sequence', methods=['POST'])
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


@app.route('/connect-device', methods=['POST'])
def connect_device():
    global dev
    try:
        if dev.is_connected():
            return jsonify({'success': True, 'device_states': dev.device_data})
    except:
        pass
    try:
        BaseDevice().disconnect_all()
        dev = BaseDevice(connect=True)
        dev.hello()
        # dev.device_data = sample_device_data
        # print("sample device data", sample_device_data)
        dev.eeprom.save_config_to_eeprom()
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    return jsonify({'success': True, 'device_states': dev.device_data})

def shutdown_server():
    with open("data/flask_app.pid", "r") as pid_file:
        pid = int(pid_file.read())
    try:
        dev.disconnect_all()
    except:
        pass
    os.kill(pid, signal.SIGTERM)


@app.get('/shutdown')
def shutdown():
    print("Shutting down server...")
    shutdown_server()


if __name__ == '__main__':
    logging.info("Starting server...")
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)
    # serve(app, host="0.0.0.0", port=5000, threads=1)