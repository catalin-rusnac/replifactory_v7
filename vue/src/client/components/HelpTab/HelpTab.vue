<template>
  <div class="DeviceApp">
    <h2>Device Setup</h2>
    <h3>Remote access</h3>
    <p>
      Ngrok is used to expose the device to the internet. To set up Ngrok, follow these steps:
      <ol>
        <li>Sign up for an Ngrok account at <a href="https://ngrok.com" target="_blank">https://ngrok.com</a>.</li>
        <li>Obtain your Ngrok authentication token from the Ngrok dashboard.</li>
        <li>In the remote tab, enter your Ngrok authentication token and click connect.</li>
        <li>Ngrok will now create a tunnel to your device, providing a public URL to access it remotely.</li>
      </ol>
    </p>

    <h2>Calibration</h2>
    <h5>Enable calibration mode in the device tab</h5>

    <h3>OD Sensors Calibration</h3>
    <p>
      To calibrate OD sensors, follow these steps:
      <ol>
        <li>Prepare probes of known OD transparencies using different pieces of paper or other materials.</li>
          <li>Label each probe with a unique ID.</li>
        <li>Place each probe in the device and measure the signal it produces.</li>
        <li>Prepare a culture with a known OD value.</li>
        <li>Dilute the culture until it produces the same signal as the probe.</li>
        <li>Measure the OD of the diluted culture and label the probe with this OD value.</li>
      </ol>
    </p>

    <h3>Stirrers Calibration</h3>
    <p>
      To calibrate stirrers, follow these steps:
      <ul>
        <li>Set the stirrer to high speed. Drag the slider until you observe a deep vortex without the stirrer detaching and rattling.</li>
        <li>Set the stirrer to low speed.  Drag the slider until the stirrer is spinning slowly without getting stuck.</li>
      </ul>
    </p>

    <h3>Pumps Calibration</h3>
    <p>
      To calibrate pumps, follow these steps:
      <ol>
        <li>Measure the pumped volume per rotation at different total amounts of rotations.</li>
        <li>Perform multiple iterations for small amounts of rotations:</li>
        <ul>
          <li>1 rotation - 50 iterations</li>
          <li>5 rotations - 10 iterations</li>
          <li>10 rotations - 5 iterations</li>
          <li>50 rotations - 1 iteration</li>
        </ul>
        <li>The measured values should decrease from approximately 0.2ml/rot to around 0.17ml/rot.</li>
      </ol>
    </p>
  </div>
</template>

<script>
export default {
  name: 'DeviceApp',
};
</script>

<style scoped>
h2 {
  margin-top: 20px;
}

h3 {
  margin-top: 15px;
}

p {
  margin-bottom: 10px;
}

ol,
ul {
  margin-bottom: 10px;
  margin-left: 20px;
}

a {
  color: #007bff;
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}
</style>