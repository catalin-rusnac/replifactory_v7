Calibration
===========

Enter calibration mode by toggling the switch in the corner of the page.

Pump Calibration
----------------

Turning the peristaltic pump by 1 rotation 50 times with pauses in between is not the same as running 50 rotations at once - at higher speeds the pumped volume per rotation is different.

To calibrate each pump, measure the volume pumped by the following sequences:

- 50x 1 rotations
- 10x 5 rotations
- 5x 10 rotations
- 1x 50 rotations

You can measure the volume by placing the first or last vial (closer to the edge) on a small scale near the device, opening the corresponding valve and pumping the calibration sequence. The app will calculate the mL/rotation coefficient for each point and use these values to accurately pump both small (~0.1mL) and large volumes (>10mL).

.. note:: When calibrating the pumps make sure that there is liquid in the entire section of the tubing - the scale cannot measure pumped air.

Stirrer Calibration
-------------------

Stirring at high speed is important to achieve good mixing - the vortex should be as deep as possible, but the stirrer bar should not detach and rattle. Spinning at low speeds is important during OD measurement - ideally the culture should be stirred gently, but there should be no vortex. If the “low” speed is too high it can form a vortex that reaches into the laser path. If the “low” speed is too low the stirrer will stop completely. If the “high” speed is too high, the stirrer bar may detach and rattle. If the “high” speed is too low the stirring of the culture is suboptimal.

.. tip:: Double click a buttons to toggle all stirrers at once.

OD Calibration
--------------

The OD sensors work by shining a laser through the culture onto a photodiode. The photodiode generates a small voltage that is measured by the device. Higher voltage means that more light passes through the culture, or the culture is less optically dense. To determine the exact relationship between photodiode signal and OD you must measure the voltage of a probe with known optical properties.

.. note:: Create OD probes using semi-transparent paper if they are not provided.

Follow these steps:

1. Insert a sheet of paper just in front of the photodiodes and measure the signal.
2. Measure the signal in one of the OD sensors.
3. Remove the sheet of paper and insert a vial of medium in the holder.
4. Slowly increase the turbidity (e.g. with milk) of the medium while measuring the signal in the sensor.
5. When the signal reaches the same value - measure the OD of the turbid medium with a spectrophotometer.
6. Label the sheet of paper with this OD value - now we know that inserting a paper in the sensor produces a signal equivalent to a culture with this OD.
7. Repeat the process with 2,3,4 papers - label all of the probes with increasing OD values, as measured by the spectrophotometer. You can use these probes to calibrate all OD sensors in all devices.

.. warning:: Cut the paper probes so they fit inside the device without bending at the edges near vial 1 and vial 7 - the paper has to be very close to the photodiode.

For every probe:

1. Insert the probe in front of the photodiode
2. Insert the probe OD value in the text field near the green “Measure new probe” button
3. Press the “Measure new probe” button. Watch how this affects the calibration curve.

.. tip:: You can edit and remove individual data points as well as entire rows.
