export const calibrationData = {
  date: '2023-05-06',
  optical_density_sensors: [
    {
      sensor_id: 1,
      calibration_coefficients: [
        { signal_mV: 0, OD: 0 },
        { signal_mV: 100, OD: 1 },
        { signal_mV: 200, OD: 2 },
        { signal_mV: 300, OD: 3 },
        { signal_mV: 400, OD: 4 }
      ]
    },
    // add calibration data for other optical density sensors here
  ],
  //stirrers 1-7
  stirrers: {1:{"low":0.2, "high":0.7},
              2:{"low":0.2, "high":0.97},
              3:{"low":0.2, "high":0.97},
              4:{"low":0.2, "high":0.7},
              5:{"low":0.2, "high":0.7},
              6:{"low":0.2, "high":0.7},
              7:{"low":0.2, "high":0.7}},

  pumps: [
    {
      pump_id: 1,
      calibration_data: [
        { total_volume_pumped_mL: 100, mL_per_rotation: 1.0 },
        { total_volume_pumped_mL: 200, mL_per_rotation: 0.9 },
        { total_volume_pumped_mL: 300, mL_per_rotation: 0.8 }
      ]
    },
    // add calibration data for other pumps here
  ]
}
