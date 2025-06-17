<template>
    <div class="guide-overlay" @click.self="$emit('close')">
      <div class="guide-popup">
        <div class="guide-header">
          <span class="guide-title">OD Calibration Guide</span>
          <button class="guide-close" @click="$emit('close')">
            <v-icon>mdi-close</v-icon>
          </button>
        </div>
        <div class="guide-content">
          <div class="guide-section">
            <b class="section-title">What is Optical Density (OD)?</b><br>
            <span class="guide-text">
              Optical Density (OD) measures how much light is absorbed by a sample. The higher the OD, the more cells or particles are in the solution.
            </span>
          </div>
          <div class="guide-section">
            <b class="section-title">Beer-Lambert Law and Scaling Factor</b><br>
            <span class="guide-text">
              The Beer-Lambert Law relates OD to the transmitted light signal:
            </span><br>
            <span class="formula">
              OD = -log₁₀(signal / blank_signal)
            </span><br>
            <span class="guide-text">
              In our devices, the light path is not a standard 1cm cuvette. The curved shape of the vial and the sensor design affect how light travels through the sample. This is corrected using a scaling factor:
            </span><br>
            <span class="formula">
              OD = -log₁₀(signal / blank_signal) * scaling
            </span><br>
          </div>
          <div class="guide-section">
            <b class="section-title">Calibration Process</b>
            <div class="method-panel">
              <div class="method-heading">Step 1: Measure OD₀ (Blank Signal)</div>
              <div class="od-warning-box">
                <b>Important: OD₀ must be measured with a vial containing growth medium!</b>
                <div class="od-warning-details">
                  - Use the same growth medium that will be used in your experiment<br>
                  - The vial must be filled with liquid<br>
                  - A good blank signal should be above 20mV<br>
                  - If the signal is below 20mV, check for:<br>
                  &nbsp;&nbsp;• Proper vial alignment<br>
                  &nbsp;&nbsp;• Clean sensors and vials<br>
                  &nbsp;&nbsp;• No obstructions in the light path
                </div>
              </div>
            </div>
            <div class="method-panel">
              <div class="method-heading">Step 2 (Optional): Measure additional OD values to calibrate the scaling factor</div>
              <div class="option-container">
                <div class="option-box">
                  <div class="method-subheading">Option A: Using Liquid Samples (Recommended)</div>
                  <ol class="guide-ol">
                    <li>Prepare a vial with a known OD between 0.1 and 2.0:
                    </li>
                    <li>Insert this vial into each slot and measure its signal using the calibration table.</li>
                    <li>The scaling factor will be automatically calculated from these measurements.</li>
                    <i>Repeat with different OD values for increased accuracy.</i>
                  </ol>
                </div>
                <div class="option-box">
                  <div class="method-subheading">Option B: Using Semitransparent Sheets</div>
                  <ol class="guide-ol">
                    <li>Determine the equivalent OD of one or more semitransparent sheets (using a solution which creates the same signal as the sheet inserted in the sensor)</li>
                    <li>Place the sheet over all sensors at once</li>
                    <li>Measure the signals and the scaling factor will be calculated automatically</li>
                    <i>Note: This method is less accurate than using liquid samples</i>
                  </ol>
                </div>
              </div>
            </div>
            <div class="method-panel">
              <div class="method-heading">Step 3: Final Check</div>
              <div class="guide-text">
                Ideally, remeasure OD₀ just before starting the experiment. Small changes in the position of the vial and media composition can affect the signal.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </template>
  
  

<script setup>
// No need for useGuideDialog, use parent-provided visibility and emit('close')
</script>

<style scoped>
.guide-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.7);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}
.guide-popup {
  background: #181c20;
  color: #fff;
  border-radius: 18px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.45);
  min-width: 340px;
  max-width: 90vw;
  max-height: 80vh;
  padding: 0 0 18px 0;
  display: flex;
  flex-direction: column;
  animation: fadeIn 0.2s;
}
@keyframes fadeIn {
  from { opacity: 0; transform: scale(0.97); }
  to { opacity: 1; transform: scale(1); }
}
.guide-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px 8px 24px;
  border-bottom: 1.5px solid #222c33;
}
.guide-title {
  font-size: 1.4rem;
  font-weight: 700;
  letter-spacing: 0.01em;
}
.guide-close {
  background: none;
  border: none;
  color: #bbb;
  font-size: 1.5rem;
  cursor: pointer;
  transition: color 0.2s;
}
.guide-close:hover {
  color: #fff;
}
.guide-content {
  padding: 22px 28px 0 28px;
  overflow-y: auto;
  font-size: 1.13rem;
  line-height: 1.7;
}
.guide-section {
  margin-bottom: 20px;
}
.section-title {
  font-size: 1.13em;
  font-weight: 600;
  color: #ffe082;
}
.guide-text {
  font-size: 1em;
  color: #e0e0e0;
}
.formula {
  display: block;
  font-family: 'Fira Mono', 'Consolas', 'Menlo', monospace;
  font-size: 1.08em;
  color: #90caf9;
  margin: 8px 0 8px 0;
}
.guide-list {
  margin-left: 1.2em;
  margin-bottom: 0.5em;
}
.guide-ol {
  margin-left: 1.2em;
  margin-bottom: 0.5em;
}
.guide-tip {
  margin-left: 1.2em;
  color: #b3e5fc;
  font-size: 0.98em;
  margin-bottom: 0.5em;
}
.method-heading {
  font-size: 1.08em;
  font-weight: 700;
  color: #6ec6e6;
  margin-bottom: 2px;
  margin-top: 10px;
}
.guide-content i {
  color: #bdbdbd;
  font-style: italic;
}
.autofill-explanation {
  margin-left: 0;
  margin-top: 8px;
  background: rgba(200,200,200,0.08);
  border-radius: 6px;
  padding: 10px 14px 10px 14px;
}
.autofill-note {
  margin-left: 1.2em;
  margin-top: 4px;
  color: #bdbdbd;
  font-size: 1em;
}
.od-warning-box {
  background: #ffeaea;
  border: 1.5px solid #e57373;
  color: #b71c1c;
  border-radius: 7px;
  padding: 12px 16px 10px 16px;
  margin: 12px 0 18px 0;
  font-size: 16px;
  font-weight: 500;
  box-shadow: 0 2px 8px 0 rgba(231, 115, 115, 0.07);
}
.od-warning-box b {
  font-size: 17px;
  font-weight: bold;
  display: block;
  margin-bottom: 4px;
}
.od-warning-details {
  font-size: 15px;
  font-weight: 400;
  margin-top: 2px;
  color: #a94442;
}
.autofill-info-note {
  font-size: 13px;
  color: #555;
  margin-top: 6px;
  margin-bottom: 2px;
  font-style: italic;
}
.method-panel {
  background: #23272e;
  border-radius: 8px;
  padding: 14px 18px 12px 18px;
  margin-bottom: 14px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  border: 1.5px solid #2d323a;
  margin-left: 1.5em;
}
.method-subheading {
  font-size: 1.05em;
  font-weight: 600;
  color: #bdbdbd;
  margin-bottom: 2px;
  margin-top: 10px;
}
.option-container {
  margin-left: 1.5em;
  margin-top: 0.5em;
}
.option-box {
  background: #1e2228;
  border-radius: 6px;
  padding: 12px 16px;
  margin-bottom: 12px;
  border: 1px solid #2d323a;
}
</style>
