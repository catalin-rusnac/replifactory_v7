from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from minimal_device.base_device import BaseDevice
import io
import matplotlib.pyplot as plt
from experiment.experiment_manager import experiment_manager
from logger.logger import logger
import time
router = APIRouter()

def get_device() -> BaseDevice: 
    device = experiment_manager.device
    if device is None:
        raise HTTPException(status_code=500, detail="Device not initialized") 
    return device

@router.post("/connect-device")
def connect_device():
    device = experiment_manager.device
    try:
        device.connect()
        device.hello()
        return {"success": True, "device_states": device.device_data}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/set-led-color")
def set_led_color(payload: dict, device: BaseDevice = Depends(get_device)):
    vial = payload['vial']
    red = payload['red']
    green = payload['green']
    blue = payload['blue']
    device.rgb_leds.set_led(vial, red, green, blue)

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
            # Set pump state back to 'stopped' when pumping is complete
            device.device_data['pumps']['states'][part_index] = 'stopped'
            # Optionally adjust stock volume if needed (implement adjust_stock_volume if required)
        elif new_state == 'stopped':
            if device.pumps[part_index].is_pumping():
                device.pumps[part_index].stop()
                print("Actively stopped pump", part_index)
    elif devicePart == 'stirrers':
        time.sleep(0.01)
        device.stirrers.set_speed(part_index, new_state)
    return {"success": True, "newState": new_state}

@router.post("/set-od-scaling-factor")
def set_od_scaling_factor(payload: dict, device: BaseDevice = Depends(get_device)):
    vial = payload['vial']
    scaling_factor = payload['scaling_factor']
    scaling_factor = float(scaling_factor)
    
    # Initialize default_scaling_factor if it doesn't exist
    if 'default_scaling_factor' not in device.device_data['ods']:
        device.device_data['ods']['default_scaling_factor'] = {}
    
    device.device_data['ods']['default_scaling_factor'][vial] = scaling_factor
    
    # Trigger calibration function fit to recalculate with new scaling factor
    device.od_sensors[vial].fit_calibration_function()
    
    device.eeprom.save_config_to_eeprom()
    logger.info(f"Set OD scaling factor for vial {vial} to {scaling_factor} and recalculated calibration")
    
    return {"success": True, "scaling_factor": scaling_factor}

@router.post("/update-od-calibration-value")
def update_od_calibration_value(payload: dict, device: BaseDevice = Depends(get_device)):
    od = payload['od']
    vial = payload['vial']
    newValue = payload['newValue']
    if newValue is None:
        del device.device_data['ods']['calibration'][vial][od]
        logger.info(f"removed od calibration value for vial {vial} and od {od}")
        device.od_sensors[vial].fit_calibration_function()
        return {"success": True, "device_states": device.device_data}
    try:
        old_value = device.device_data['ods']['calibration'][vial][od]
    except KeyError:
        old_value = None
    device.device_data['ods']['calibration'][vial][od] = newValue
    device.od_sensors[vial].fit_calibration_function()
    # logger.info(f"updated od calibration value for vial {vial} to from {old_value} to {newValue}")
    return {"success": True, "device_states": device.device_data}


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
    oldCalibration = device.device_data[devicePart]['calibration'][partIndex]
    device.device_data[devicePart]['calibration'][partIndex] = newCalibration
    logger.info(f"Set {devicePart} {partIndex} calibration to {newCalibration}")
    
    if devicePart == 'ods':
        old_values = {k: v for k, v in oldCalibration.items() if v is not None}
        new_values = {k: v for k, v in newCalibration.items() if v is not None}
        # check if entire dictionary of non-null values is different
        if old_values != new_values:
            logger.info(f"Recalculating ods {partIndex} calibration because of change in non-null values")
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

@router.post("/start-pump-calibration-sequence")
def start_pump_calibration_sequence(payload: dict, device: BaseDevice = Depends(get_device)):
    pumpId = payload['pumpId']
    rotations = payload['rotations']
    iterations = payload['iterations']
    logger.info(f"Starting pump {pumpId} calibration sequence with {rotations} rotations and {iterations} iterations")
    if device.valves.all_closed():
        return {"success": False, "error": "All valves are closed"}
    device.device_data['pumps']['states'][pumpId] = 'running'
    for i in range(iterations):
        if device.device_data['pumps']['states'][pumpId] == 'stopped':
            break
        device.pumps[pumpId].move(rotations)
        while device.pumps[pumpId].is_pumping():
            time.sleep(0.1)
        time.sleep(0.5)
    device.device_data['pumps']['states'][pumpId] = 'stopped'
    return {"success": True}


@router.post("/save-calibration")
def save_calibration(device: BaseDevice = Depends(get_device)):
    try:
        # Use the device's built-in save function
        device.save_timestamped_device_config()
        return {"success": True, "message": "Device calibration saved successfully"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@router.get("/list-device-configs")
def list_device_configs(device: BaseDevice = Depends(get_device)):
    return {"success": True, "configs": device.list_device_configs()}

@router.post("/load-device-config")
def load_device_config(payload: dict, device: BaseDevice = Depends(get_device)):
    filename = payload['filename']
    device.load_dev_config(filename)
    return {"success": True, "message": "Device config loaded successfully"}

@router.post("/run-ods-test")
def ods_test(device: BaseDevice = Depends(get_device)):
    device.od_sensors[1].measure_optical_signal_max() # measures all sensors
    max_signals = device.device_data["ods"]["max_signal"]
    return {"success": True, "max_signals": max_signals}

@router.post("/run-stirrer-test")
def stirrer_test(device: BaseDevice = Depends(get_device)):
    device.stirrers.get_all_calibration_curves()
    data = device.device_data["stirrers"]["speed_profiles"]
    return {"success": True, "speed_profiles": data}

@router.post("/set-valve-duty-cycle-open")
def set_valve_duty_cycle(payload: dict, device: BaseDevice = Depends(get_device)):
    valve = payload['valve']
    duty_cycle = payload['duty_cycle']
    device.valves.set_duty_cycle_open(valve, duty_cycle)
    return {"success": True}

@router.post("/set-valve-duty-cycle-closed")
def set_valve_duty_cycle_closed(payload: dict, device: BaseDevice = Depends(get_device)):
    valve = payload['valve']
    duty_cycle = payload['duty_cycle']
    device.valves.set_duty_cycle_closed(valve, duty_cycle)
    return {"success": True}

@router.put("/measure-stirrer-speeds")
def measure_stirrer_speeds(device: BaseDevice = Depends(get_device)):
    speeds = device.stirrers.measure_all_rpms()
    return {"success": True, "speeds": speeds}

@router.get("/supply-voltage")
def get_supply_voltage(device: BaseDevice = Depends(get_device)):
    """Get the motor driver supply voltage configuration"""
    supply_voltage = device.device_data.get('supply_voltage', 12.0)
    return {"success": True, "supply_voltage": supply_voltage}

@router.post("/supply-voltage")
def set_supply_voltage(payload: dict, device: BaseDevice = Depends(get_device)):
    """Set the motor driver supply voltage configuration"""
    try:
        supply_voltage = float(payload.get('supply_voltage'))
        if not 8 <= supply_voltage <= 45:  # L6470H valid range
            raise ValueError("Supply voltage must be between 8V and 45V (L6470H operating range)")
        
        device.device_data['supply_voltage'] = supply_voltage
        device.eeprom.save_config_to_eeprom()
        
        return {"success": True, "message": f"Supply voltage set to {supply_voltage}V"}
        
    except Exception as e:
        logger.error(f"Error setting supply voltage: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/pump/{pump_id}/stepper-params")
def get_pump_stepper_params(pump_id: int, device: BaseDevice = Depends(get_device)):
    """
    Get current stepper parameters for a specific pump
    Used by the frontend when Ctrl+Shift+clicking a pump button to show settings dialog
    """
    if pump_id not in [1, 2, 3, 4]:  # Only valid pump IDs
        raise HTTPException(status_code=400, detail="Invalid pump ID")
    
    pump = device.pumps[pump_id]
    # Get supply voltage from device configuration
    supply_voltage = device.device_data.get('supply_voltage', 12.0)
    
    # Convert stall_threshold from normalized value (0-1) back to amperes
    stall_threshold_ma = pump.stall_threshold * 4000  # Convert to milliamps
    stall_threshold_a = stall_threshold_ma / 1000     # Convert to amperes
    
    params = {
        "max_speed_rps": pump.max_speed_rps,
        "min_speed_rps": pump.min_speed_rps,
        "acceleration": pump.acceleration,
        "deceleration": pump.deceleration,
        "kval_run": pump._kval_run,
        "kval_acc": pump._kval_acc,
        "kval_dec": pump._kval_dec,
        "stall_threshold": stall_threshold_a,
        "supply_voltage": supply_voltage
    }
    return {"success": True, "params": params}

@router.post("/pump/{pump_id}/stepper-params")
def set_pump_stepper_params(pump_id: int, payload: dict, device: BaseDevice = Depends(get_device)):
    """Set temporary stepper parameters for a specific pump (in memory only)"""
    if pump_id not in [1, 2, 3, 4]:  # Only valid pump IDs
        raise HTTPException(status_code=400, detail="Invalid pump ID")
    
    pump = device.pumps[pump_id]
    params = payload.get('params', {})
    
    try:
        # Update parameters in memory and apply to hardware
        if 'max_speed_rps' in params:
            pump.max_speed_rps = float(params['max_speed_rps'])
            pump.set_max_speed(pump.max_speed_rps)
            
        if 'min_speed_rps' in params:
            pump.min_speed_rps = float(params['min_speed_rps'])
            pump.set_min_speed(pump.min_speed_rps)
            
        if 'acceleration' in params:
            pump.acceleration = float(params['acceleration'])
            pump.set_acceleration(pump.acceleration)
            
        if 'deceleration' in params:
            pump.deceleration = float(params['deceleration'])
            pump.set_deceleration(pump.deceleration)
            
        if 'kval_run' in params:
            pump._kval_run = float(params['kval_run'])
            pump.kval_run = pump._kval_run
            
        if 'kval_acc' in params:
            pump._kval_acc = float(params['kval_acc'])
            pump.kval_acc = pump._kval_acc
            
        if 'kval_dec' in params:
            pump._kval_dec = float(params['kval_dec'])
            pump.kval_dec = pump._kval_dec
            
        if 'stall_threshold' in params:
            # Convert from amperes to milliamperes for the L6470H driver
            current_ma = float(params['stall_threshold']) * 1000
            pump.set_stall_threshold_ma(current_ma)
            
        return {"success": True, "message": "Stepper parameters updated (temporary)"}
        
    except Exception as e:
        logger.error(f"Error setting pump {pump_id} stepper params: {str(e)}")
        return {"success": False, "error": str(e)}

@router.post("/pump/{pump_id}/continuous-run")
def toggle_pump_continuous_run(pump_id: int, payload: dict, device: BaseDevice = Depends(get_device)):
    """Start or stop continuous run of a specific pump"""
    if pump_id not in [1, 2, 3, 4]:  # Only valid pump IDs
        raise HTTPException(status_code=400, detail="Invalid pump ID")
    
    pump = device.pumps[pump_id]
    action = payload.get('action', 'start')  # 'start' or 'stop'
    
    try:
        if action == 'stop':
            # Stop the pump
            pump.stop()
            # Update device state to stopped
            device.device_data['pumps']['states'][pump_id] = 'stopped'
            logger.info(f"Stopped continuous run for pump {pump_id}")
            return {"success": True, "message": f"Pump {pump_id} continuous run stopped", "running": False}
        else:
            # Start continuous run
            speed = payload.get('speed', 1.0)  # Default to 1 RPS if not specified
            
            # Validate speed range
            if not (0.01 <= abs(speed) <= 10.0):
                raise ValueError("Speed must be between 0.01 and 10.0 RPS")
                
            # Start continuous run
            pump.run(speed=speed)
            # Update device state to running
            device.device_data['pumps']['states'][pump_id] = 'running'
            logger.info(f"Started continuous run for pump {pump_id} at {speed} RPS")
            return {"success": True, "message": f"Pump {pump_id} started continuous run at {speed} RPS", "running": True}
        
    except Exception as e:
        logger.error(f"Error toggling continuous run for pump {pump_id}: {str(e)}")
        return {"success": False, "error": str(e)}