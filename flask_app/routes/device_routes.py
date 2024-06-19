import traceback

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
    current_app.device.device_data[devicePart]['states'][part_index] = new_state
    if devicePart == 'valves':
        print(f'Toggled valve {part_index} to {new_state}')
        if new_state=='open':
            current_app.device.valves.open(part_index)
        elif new_state=='closed':
            current_app.device.valves.close(part_index)

    elif devicePart == 'pumps':
        print(f'Toggled pump {part_index} to {new_state}')
        # print(request.json)

        if new_state=='running':
            volume = None
            if 'volume' in request.json['input']:
                volume = float(request.json['input']['volume'])
                current_app.device.pumps[part_index].pump(volume)
            elif 'rotations' in request.json['input']:
                rotations = float(request.json['input']['rotations'])
                current_app.device.pumps[part_index].move(rotations)
            while current_app.device.pumps[part_index].is_pumping():
                time.sleep(0.2)
            if volume:
                adjust_stock_volume(pump_index=part_index, volume=volume)

        elif new_state=='stopped':
            if current_app.device.pumps[part_index].is_pumping():
                current_app.device.pumps[part_index].stop()
                print("Actively stopped pump", part_index)
        # volume = request.json['input']
        # current_app.device.pumps[part_index].pump(volume)

    elif devicePart == 'stirrers':
        time.sleep(0.01)
        # print(f'Toggled stirrer {part_index} to {new_state}')
        current_app.device.stirrers.set_speed(part_index, new_state)
    if devicePart == 'valves':
        current_app.device.eeprom.save_config_to_eeprom()
    return jsonify({'success': True, 'newState': new_state})


@device_routes.route('/stock_adjust?pump_index=<int:pump_index>?volume=<int:volume>', methods=['POST'])
def adjust_stock_volume(pump_index, volume):
    if pump_index == 1:
        stock_volume = "stock_volume_main"
    elif pump_index == 2:
        stock_volume = "stock_volume_drug"
    elif pump_index == 4:
        stock_volume = "stock_volume_waste"
    if hasattr(current_app, 'experiment'):
        parameters = current_app.experiment.parameters
        parameters[stock_volume] = float(parameters[stock_volume]) - volume
        current_app.experiment.parameters = parameters


@device_routes.route('/measure-<string:devicePart>', methods=['POST'])
def measure_device_part(devicePart):
    partIndex = int(request.json['partIndex'])
    if devicePart == 'ods':
        # print(f'Measuring OD {partIndex}')
        od, signal = current_app.device.od_sensors[partIndex].measure_od()
        # od_value = random.randint(0, 100)
        current_app.device.device_data[devicePart]['states'][partIndex] = od
        current_app.device.device_data[devicePart]['odsignals'][partIndex] = signal
    elif devicePart == 'thermometers':
        t_vials, t_board = current_app.device.thermometers.measure_temperature()
        current_app.device.device_data[devicePart]['states'] = {1: t_vials, 2: t_board}
    return jsonify({'success': True, 'device_states': current_app.device.device_data})

@device_routes.route('/get-stirrer-speeds', methods=['GET'])
def get_stirrer_speed():
    speeds = current_app.device.stirrers.measure_all_rpms()
    from flask import send_file
    import matplotlib.pyplot as plt
    from io import BytesIO

    plt.close()
    plt.bar(speeds.keys(), speeds.values())
    plt.ylim(0, max(max(speeds.values())*1.1, 5000))
    plt.ylabel('RPM')
    plt.xlabel('Vial')

    # Save the plot to a BytesIO object
    img = BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)  # Rewind the buffer to the beginning
    plt.close()
    # Send the image as a response
    return send_file(img, mimetype='image/png',as_attachment=False)


@device_routes.route('/get-stirrer-calibration-curve/<int:vial_number>', defaults={'n_points': 10, 'time_sleep': 2}, methods=['GET'])
@device_routes.route('/get-stirrer-calibration-curve/<int:vial_number>/<int:n_points>/<int:time_sleep>', methods=['GET'])
def get_stirrer_calibration_curve(vial_number, n_points, time_sleep):
    from flask import send_file
    import matplotlib.pyplot as plt
    from io import BytesIO

    rpm_dc = current_app.device.stirrers.get_calibration_curve(vial_number, n_points, time_sleep)
    plt.clf()
    plt.plot(list(rpm_dc.keys()), list(rpm_dc.values()), "ro-")
    plt.title("Vial %d RPM vs Duty Cycle" % vial_number)
    plt.xlabel("Duty Cycle")
    plt.ylabel("RPM")
    # plt.ylim(0, 5000)
    plt.xlim(0, 1.05)
    img = BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)  # Rewind the buffer to the beginning
    plt.close()
    # Send the image as a response
    return send_file(img, mimetype='image/png', as_attachment=False)


@device_routes.route('/get-all-device-data', methods=['GET'])
def get_all_device_states():
    print("Getting all device data")
    try:
        return jsonify({
        'success': True,
        'device_states': current_app.device.device_data,
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
    current_app.device.device_data[devicePart]['calibration'][partIndex] = newCalibration
    if devicePart == 'ods':
        current_app.device.od_sensors[partIndex].fit_calibration_function()
    if devicePart == 'stirrers':
        speed = current_app.device.device_data['stirrers']['states'][partIndex]
        current_app.device.stirrers.set_speed(partIndex, speed, accelerate=False)
        print("Calibrated and set stirrer speed to", speed)
        current_app.device.eeprom.save_config_to_eeprom()

    response = jsonify(success=True, newCalibration=newCalibration)
    if devicePart == 'ods':
        response = jsonify(success=True, newCalibration=newCalibration, coefs=current_app.device.device_data['ods']['calibration_coefs'][partIndex])
    return response


@device_routes.route('/measure-od-calibration', methods=['POST'])
def measure_od_calibration():
    data = request.get_json()
    odValue = data.get('odValue')
    odValue = float(odValue)
    print(f'Measuring OD calibration with OD {odValue}')
    for v in range(1,8):
        current_app.device.od_sensors[v].measure_od_calibration(odValue)
    for v in range(1,8):
        current_app.device.od_sensors[v].fit_calibration_function()
    current_app.device.eeprom.save_config_to_eeprom()
    return jsonify(success=True, odValue=odValue)


@device_routes.route('/start-pump-calibration-sequence', methods=['POST'])
def start_pump_calibration_sequence():
    data = request.get_json()
    print(data)
    pumpId = data.get('pumpId')
    rotations = data.get('rotations')
    iterations = data.get('iterations')
    print(f'Starting pump {pumpId} calibration sequence with {rotations} rotations and {iterations} iterations')

    if current_app.device.valves.all_closed():
        return jsonify(success=False, error="All valves are closed")
    current_app.device.device_data['pumps']['states'][pumpId] = 'running'
    for i in range(iterations):
        if current_app.device.device_data['pumps']['states'][pumpId] == 'stopped':
            break
        current_app.device.pumps[pumpId].move(rotations)
        while current_app.device.pumps[pumpId].is_pumping():
            time.sleep(0.1)
        time.sleep(0.5)
    return jsonify(success=True)


@device_routes.route('/force-connect-device', methods=['POST', 'GET'])
def force_connect_device():
    print("Force connecting device")
    try:
        if current_app.device.is_connected():
            current_app.device.disconnect_all()
            current_app.device.connect()
            current_app.device.hello()
            return jsonify({'success': True, 'device_states': current_app.device.device_data})
    except:
        print("Device not connected")
        pass
    try:
        print("Connecting device")
        current_app.device = BaseDevice(connect=True)
        if hasattr(current_app, "experiment"):
            current_app.experiment.device = current_app.device
        try:
            current_app.device.hello()
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
        return jsonify({'success': True, 'device_states': current_app.device.device_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@device_routes.route('/reset-eeprom-memory', methods=['POST'])
def reset_eeprom_memory():
    current_app.device.eeprom.reset_memory()
    return jsonify({'success': True})


@device_routes.route('/connect-device', methods=['POST', 'GET'])
def connect_device():
    global dev
    try:
        if current_app.device.is_connected():
            print("Device already connected")
            if hasattr(current_app, "experiment"):
                if current_app.experiment.device is not current_app.device:
                    print("Setting device for experiment")
                    current_app.experiment.device = current_app.device
                    current_app.experiment.device.hello()
            return jsonify({'success': True, 'device_states': current_app.device.device_data})
    except:
        print("Device not connected yet")
        pass
    try:
        print("Connecting device")
        current_app.device = BaseDevice(connect=True)
        current_app.device.hello()
        if hasattr(current_app, "experiment"):
            current_app.experiment.device = current_app.device
        return jsonify({'success': True, 'device_states': current_app.device.device_data})
    except Exception as e:
        traceback.print_exc()
        current_app.device = None
        if hasattr(current_app, "experiment"):
            current_app.experiment.device = None
        return jsonify({'success': False, 'error': str(e)})

