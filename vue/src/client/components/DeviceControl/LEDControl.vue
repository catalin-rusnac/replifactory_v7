<template>
  <div class="rgb-control-container">
    <div class="vial-container" v-for="vial in vials" :key="vial">
      <div class="color-selector">
        <label>{{ 'Vial ' + vial }}</label>
        <input
          type="color"
          v-model="ledColors[vial].color"
          @input="updateColor(vial)"
        />
      </div>
      <button class="set-color-button" @click="setLEDColor(vial, $event)">Set</button>
    </div>
  </div>
</template>

<script>
import { storeToRefs } from 'pinia'
import { useDeviceStore } from '../../stores/device'
import { onMounted } from 'vue'

const deviceStore = useDeviceStore()
const { leds } = storeToRefs(deviceStore)


onMounted(() => {
  if (!leds.value) {
    deviceStore.fetchDeviceData()
  }
})


export default {
  name: "SetLEDColor",
  data() {
    return {
      vials: [1,2,3,4,5,6,7],
      ledColors: {
        1: { red: 0, green: 0, blue: 0, color: "#000000" },
        2: { red: 0, green: 0, blue: 0, color: "#000000" },
        3: { red: 0, green: 0, blue: 0, color: "#000000" },
        4: { red: 0, green: 0, blue: 0, color: "#000000" },
        5: { red: 0, green: 0, blue: 0, color: "#000000" },
        6: { red: 0, green: 0, blue: 0, color: "#000000" },
        7: { red: 0, green: 0, blue: 0, color: "#000000"},
      },
    };
  },
  methods: {
    
    async setLEDColor(vial, event) {
      if (event.shiftKey) {
        // If Shift key is held, set the same color for all vials
        const { red, green, blue } = this.ledColors[vial];
        for (const vialKey of this.vials) {
          this.ledColors[vialKey].red = red;
          this.ledColors[vialKey].green = green;
          this.ledColors[vialKey].blue = blue;
          this.ledColors[vialKey].color = this.ledColors[vial].color;
          await this.setIndividualLEDColor(vialKey);
        }
      } else {
        // Otherwise, set the color for the individual vial
        await this.setIndividualLEDColor(vial);
      }
    },
    async setIndividualLEDColor(vial) {
      const { red, green, blue } = this.ledColors[vial];
      try {
        console.log("Setting color for vial", vial, "to", red, green, blue);
        await deviceStore.setLedColor(vial, red, green, blue);
      } catch (error) {
        console.error(`Failed to set color for vial ${vial}:`, error);
        alert(`Error setting color for vial ${vial}`);
      }
    },
    updateColor(vial) {
      const hexColor = this.ledColors[vial].color;
      const { r, g, b } = this.hexToRgb(hexColor);
      this.ledColors[vial].red = r / 255;
      this.ledColors[vial].green = g / 255;
      this.ledColors[vial].blue = b / 255;
    },
    hexToRgb(hex) {
      const bigint = parseInt(hex.slice(1), 16);
      return {
        r: (bigint >> 16) & 255,
        g: (bigint >> 8) & 255,
        b: bigint & 255,
      };
    },
  },
};
</script>

<style scoped>
.rgb-control-container {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  margin: 20px auto;
  width: 800px;
}

.vial-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  border: 1px solid #e3e3e3;
  border-radius: 10px;
  padding: 10px;
  margin: 10px;
  width: 90px;
}

.color-selector {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.set-color-button {
  background-color: rgba(0, 0, 0, 0.4);
  color: white;
  font-size: 14px;
  border: none;
  border-radius: 8px;
  padding: 5px 10px;
  cursor: pointer;
  transition: opacity 0.3s;
}

.set-color-button:hover {
  opacity: 0.8;
}
</style>
