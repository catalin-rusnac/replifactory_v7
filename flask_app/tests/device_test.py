import sys
from logging import critical

sys.path.append('./flask_app/')
from minimal_device.base_device import BaseDevice
import numpy as np
import time
dev = BaseDevice()
dev.connect()
#%%
for i in range(10000):
    dev.valves.open(1)
    dev.valves.close(1)
    # dev.valves.open(2)
    # dev.valves.close(2)
#%%
dev.valves.set_valves_to_memory_positions()
#%%
dev.valves.open(4)
#%%
dev.valves.close(4)
 #%%
for p in [dev.pump1]:
    p.soft_hiz()

#%%


#%%
def test_motor_control(device):
    p = device.pump1
    p.stop()
    print(p.get_status_command())

    import plotly.graph_objs as go

    supply_voltage = 12
    current_range = np.arange(317.5*1, 317.5*1.8, 31.75) # mA
    voltage_range = np.arange(1.4, 1.9, 0.1) # Volts
    critical_current = 500
    critical_voltage = 1.65
    flow = "free-flow"
    # flow = "blocked-flow"
    test_speed_rps = 0.4  # rps
    rot_seconds = 1/test_speed_rps
    wait_time = 0.1

    for iteration in range(1):
        fig = go.Figure()
        fig.update_layout(
            yaxis=dict(range=[100, 800], title="mA"),
            xaxis=dict(range=[1.2, 4], title="voltage"),
            title=f"{test_speed_rps} rps {flow}")
        fig.update_layout(showlegend=False)
        p.reset_speeds()
        voltage = max(voltage_range)
        p.kval_run = voltage / supply_voltage
        p.kval_acc = voltage / supply_voltage
        p.kval_dec = voltage / supply_voltage
        p.set_ocd_threshold_ma(0)
        p.run(speed=3)
        time.sleep(2)
        p.run(speed=test_speed_rps)
        time.sleep(2)
        assert p.max_speed_rps >= test_speed_rps
        for i in range(10):
            for current in current_range:
                p.set_stall_threshold_ma(current)
                for voltage in voltage_range:
                    p.kval_run = voltage / supply_voltage

                    p.run(speed=test_speed_rps)
                    time.sleep(wait_time)

                    stall_a, stall_b, ocd = p.detect_stall_and_ocd()
                    stall = stall_a or stall_b
                    if not stall:
                        print(f"Running at %.2f V, %d mA, \t\t%.2f W {ocd}"%(voltage, current, voltage*current/1000))
                        fig.add_trace(go.Scatter(
                            y=[current],
                            x=[voltage],
                            mode='markers',
                            # opacity=0.5,
                            opacity=0.1,
                            marker=dict(color='green', size=20)))
                    else:
                        fig.add_trace(go.Scatter(
                            y=[current],
                            x=[voltage],
                            mode='markers',
                            opacity=0.3,
                            marker=dict(color='red', size=20)
                        ))
                        print(f"Stalled at %.2f V, %d mA, %.2f W {ocd}"%(voltage, current, voltage*current/1000))
                    p.get_status_command() # clear the stall flag
        fig.update_traces()
        p.soft_hiz()
        test_time = time.strftime("%Y%m%d-%H%M%S")
        # pio.write_html(fig, file=f'pump_data/Stall_Detect_{flow}_{wait_time}s_{iteration}rep_{test_time}.html')
        fig.show()
test_motor_control(dev)
#%%import plotly.graph_objects as go
fig = go.Figure()
for stirrer in data:
    d = data[stirrer]
    x = list(d.keys())
    x = sorted(x)
    y = [np.mean(d[k]) for k in x]
    yerr = [np.std(d[k]) for k in x]
    fig.add_trace(go.Scatter(x=x, y=y, mode='markers+lines', name=f'Stirrer {stirrer}',
                             error_y=dict(type='data', array=yerr)))
fig.update_layout(title='Stirrer calibration curves', xaxis_title='Duty cycle', yaxis_title='RPM')
fig.show()
#%%
vial=1
data = {}  # Dictionary to hold all measurements for this vial

# Ensure the photodiode for this vial is selected
dev.photodiodes.switch_to_vial(vial)

# ---------------------------
# 1. Background Measurement
# ---------------------------
# Turn off LED and laser
dev.rgb_leds.set_led(led_number=vial, red=0, green=0, blue=0)
dev.lasers.switch_off(vial=vial)
time.sleep(0.1)  # Allow hardware to settle

background = dev.photodiodes.measure()
data['background'] = background
print(f"Vial {vial} - Background signal: {background}")

# ---------------------------
# 2. Laser Measurement
# ---------------------------
dev.lasers.switch_on(vial=vial)
time.sleep(0.1)  # Wait for the laser to stabilize
laser_signal = dev.photodiodes.measure()
data['laser'] = laser_signal
print(f"Vial {vial} - Laser signal: {laser_signal}")
dev.lasers.switch_off(vial=vial)
time.sleep(0.1)

# ---------------------------
# 3. LED Measurements (one color at a time)
# ---------------------------
led_measurements = {}
for color in ['red', 'green', 'blue']:
    measurements = []  # List to hold tuples of (intensity, signal)
    # Generate 10 steps from 0 to 1 for intensity
    for intensity in np.linspace(0, 1, 10):
        # Set only the current color channel; the other two remain off.
        if color == 'red':
            r, g, b = intensity, 0, 0
        elif color == 'green':
            r, g, b = 0, intensity, 0
        elif color == 'blue':
            r, g, b = 0, 0, intensity

        dev.rgb_leds.set_led(led_number=vial, red=r, green=g, blue=b)
        time.sleep(0.05)  # Allow LED to reach the target intensity
        signal = dev.photodiodes.measure()
        measurements.append((intensity, signal))
        print(f"Vial {vial} - LED {color} intensity {intensity:.2f} -> Signal: {signal}")

    led_measurements[color] = measurements

data['led'] = led_measurements

# Turn off the LED after the measurement sequence
dev.rgb_leds.set_led(led_number=vial, red=0, green=0, blue=0)

#%%
dev.stirrers.set_speed_all("stopped")
    #%%
data=dev.stirrers.get_all_calibration_curves()
dev.stirrers.plot_stirrer_calibration_curves(data)
# print(data)
data = {1: {np.float64(0.26): [np.float64(3631.9612590799034), np.float64(3740.648379052369), np.float64(3717.472118959108)], np.float64(0.3933333333333333): [np.float64(4566.2100456621), np.float64(4601.226993865031), np.float64(4587.155963302752)], np.float64(0.5266666666666666): [np.float64(5309.734513274337), np.float64(5366.7262969588555), np.float64(5338.078291814946)], np.float64(0.66): [np.float64(6726.457399103139), np.float64(6772.009029345372), np.float64(6802.721088435374)], np.float64(0.24): [np.float64(2343.75), np.float64(3370.7865168539324), np.float64(3537.735849056604)], np.float64(0.15999999999999998): [np.float64(3164.5569620253164), np.float64(2988.0478087649403), np.float64(2970.29702970297)], np.float64(0.07999999999999999): [np.float64(3000.0), np.float64(2757.3529411764707), np.float64(2808.9887640449438)], np.float64(0.0): [0, 0, 0]}, 2: {np.float64(0.26): [np.float64(3631.9612590799034), np.float64(3759.3984962406016), np.float64(3797.46835443038)], np.float64(0.4013333333333333): [np.float64(4702.194357366771), np.float64(4739.336492890995), np.float64(4716.981132075472)], np.float64(0.5426666666666666): [np.float64(5514.705882352941), np.float64(5524.861878453039), np.float64(5514.705882352941)], np.float64(0.6839999999999999): [np.float64(7092.198581560284), np.float64(7125.890736342043), np.float64(7109.004739336493)], np.float64(0.24): [np.float64(2588.4383088869718), np.float64(3464.203233256351), np.float64(3601.4405762304923)], np.float64(0.15999999999999998): [np.float64(3243.2432432432433), np.float64(3086.41975308642), np.float64(3024.1935483870966)], np.float64(0.07999999999999999): [np.float64(3083.247687564234), np.float64(2912.621359223301), np.float64(2941.176470588235)], np.float64(0.0): [0, 0, 0]}, 3: {np.float64(0.26): [np.float64(3623.1884057971015), np.float64(3750.0), np.float64(3750.0)], np.float64(0.36933333333333335): [np.float64(4504.504504504504), np.float64(4531.722054380664), np.float64(4511.278195488721)], np.float64(0.4786666666666667): [np.float64(5102.040816326531), np.float64(5102.040816326531), np.float64(5119.453924914676)], np.float64(0.588): [np.float64(5454.545454545455), np.float64(5434.782608695652), np.float64(6342.494714587738)], np.float64(0.24): [np.float64(2577.319587628866), np.float64(3436.426116838488), np.float64(3579.9522673031024)], np.float64(0.15999999999999998): [np.float64(3164.5569620253164), np.float64(3118.5031185031185), np.float64(3138.0753138075315)], np.float64(0.07999999999999999): [np.float64(2912.621359223301), np.float64(2851.71102661597), np.float64(2777.777777777778)], np.float64(0.0): [0, 0, 0]}, 4: {np.float64(0.26): [np.float64(3631.9612590799034), np.float64(3676.470588235294), np.float64(3750.0)], np.float64(0.3893333333333333): [np.float64(4518.0722891566265), np.float64(4518.0722891566265), np.float64(4573.170731707317)], np.float64(0.5186666666666666): [np.float64(5309.734513274337), np.float64(5263.1578947368425), np.float64(5281.69014084507)], np.float64(0.648): [np.float64(6681.5144766147), np.float64(6741.573033707865), np.float64(6756.756756756757)], np.float64(0.24): [np.float64(2645.5026455026455), np.float64(3456.221198156682), np.float64(3579.9522673031024)], np.float64(0.15999999999999998): [np.float64(3174.6031746031745), np.float64(3042.5963488843813), np.float64(3033.367037411527)], np.float64(0.07999999999999999): [np.float64(2846.2998102466795), np.float64(2808.9887640449438), np.float64(2892.9604628736743)], np.float64(0.0): [0, 0, 0]}, 5: {np.float64(0.26): [np.float64(3645.2004860267316), np.float64(3768.8442211055276), np.float64(3773.5849056603774)], np.float64(0.3853333333333333): [np.float64(4629.62962962963), np.float64(4658.385093167702), np.float64(4665.629860031104)], np.float64(0.5106666666666666): [np.float64(5424.9547920434), np.float64(5434.782608695652), np.float64(5454.545454545455)], np.float64(0.636): [np.float64(6122.448979591837), np.float64(6172.83950617284), np.float64(6250.0)], np.float64(0.24): [np.float64(2454.991816693944), np.float64(3416.8564920273348), np.float64(3537.735849056604)], np.float64(0.15999999999999998): [np.float64(2876.3183125599235), np.float64(2859.866539561487), np.float64(2819.5488721804513)], np.float64(0.07999999999999999): [np.float64(1443.6958614051973), np.float64(1483.679525222552), np.float64(2724.7956403269754)], np.float64(0.0): [0, 0, 0]}, 6: {np.float64(0.26): [np.float64(3778.337531486146), np.float64(3891.0505836575876), np.float64(3846.153846153846)], np.float64(0.3333333333333333): [np.float64(4304.16068866571), np.float64(4347.826086956522), np.float64(4379.56204379562)], np.float64(0.4066666666666666): [np.float64(4746.835443037975), np.float64(4838.709677419355), np.float64(4807.692307692308)], np.float64(0.48): [np.float64(5244.755244755244), np.float64(5208.333333333333), np.float64(5235.602094240838)], np.float64(0.24): [np.float64(2857.1428571428573), np.float64(3636.3636363636365), np.float64(3750.0)], np.float64(0.15999999999999998): [np.float64(3246.753246753247), np.float64(3205.128205128205), np.float64(3267.97385620915)], np.float64(0.07999999999999999): [np.float64(3054.989816700611), np.float64(3012.0481927710844), np.float64(3164.5569620253164)], np.float64(0.0): [0, 0, 0]}, 7: {np.float64(0.26): [np.float64(3546.099290780142), np.float64(3676.470588235294), np.float64(3731.3432835820895)], np.float64(0.36933333333333335): [np.float64(4398.826979472141), np.float64(4451.038575667656), np.float64(4470.938897168406)], np.float64(0.4786666666666667): [np.float64(5128.205128205128), np.float64(5190.311418685121), np.float64(5208.333333333333)], np.float64(0.588): [np.float64(5747.126436781609), np.float64(5769.2307692307695), np.float64(5747.126436781609)], np.float64(0.24): [np.float64(2838.2213812677387), np.float64(3448.2758620689656), np.float64(3488.3720930232557)], np.float64(0.15999999999999998): [np.float64(2890.173410404624), np.float64(2879.0786948176583), np.float64(2892.9604628736743)], np.float64(0.07999999999999999): [np.float64(1339.2857142857142), np.float64(1463.4146341463415), np.float64(2692.998204667864)], np.float64(0.0): [0, 0, 0]}}

#%%
dev.stirrers.plot_stirrer_calibration_curves(data)
#%%
