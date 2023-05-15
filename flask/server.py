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
from minimal_device.device_data import device_data
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
    the_input=None
    device_data[devicePart]['states'][part_index] = new_state
    if "input" in request.json:
        the_input = request.json['input']
    if devicePart == 'valves':
        time.sleep(0.5)
        print(f'Toggled  222 valve {part_index} to {new_state} and slept')
        if new_state=='open':
            dev.valves.open(part_index)
        elif new_state=='closed':
            dev.valves.close(part_index)

    elif devicePart == 'pumps':
        time.sleep(0.5)
        print(f'Toggled pump {part_index} to {new_state} and slept')
        if the_input:
            print(the_input)

    elif devicePart == 'stirrers':
        time.sleep(0.01)
        print(f'Toggled stirrer {part_index} to {new_state} and slept')

    return jsonify({'success': True, 'newState': new_state})


@app.route('/measure-<string:devicePart>', methods=['POST'])
def measure_device_part(devicePart):
    partIndex = int(request.json['partIndex'])
    if devicePart == 'ods':
        print(f'Measuring OD {partIndex} and sleeping')
        od_value = dev.od_sensors[partIndex].measure_od()
        # od_value = random.randint(0, 100)
        device_data[devicePart]['states'][partIndex] = od_value

    elif devicePart == 'temperature':
        device_data[devicePart][partIndex] = random.randint(0, 100)
    elif devicePart == 'pumps':
        device_data[devicePart]['volume'][partIndex] = random.randint(0, 100)
    elif devicePart == 'stirrers':
        device_data[devicePart]['states'][partIndex] = random.randint(0, 100)
    elif devicePart == 'valves':
        device_data[devicePart]['states'][partIndex] = random.randint(0, 100)
    return jsonify({'success': True, 'device_states': device_data})


@app.route('/get-all-device-data', methods=['GET'])
def get_all_device_states():
    print("Getting all device data")
    for k in device_data["ods"].keys():
        jsonify(device_data["ods"][k])
    return jsonify({
        'success': True,
        'device_states': device_data,
    })


@app.route('/set-<string:devicePart>-calibration', methods=['POST'])
def set_part_calibration(devicePart):
    data = request.get_json()
    partIndex = data.get('partIndex')
    newCalibration = data.get('newCalibration')

    # implement logic to update the device part calibration based on `devicePart`, `partIndex`, and `newCalibration`
    print(f'Set {devicePart} {partIndex} calibration to {newCalibration}')
    device_data[devicePart]['calibration'][partIndex] = newCalibration
    return jsonify(success=True, newCalibration=newCalibration)


@app.route('/connect-device', methods=['POST'])
def connect_device():
    global dev
    dev = BaseDevice(connect=True)
    dev.hello()
    if dev.is_connected():
        return jsonify({'success': True, 'device_states': device_data})
    else:
        return jsonify({'success': False})


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