<template>
  <div className="single-chart-container">
    <Scatter :data="chartData" :options="chartOptions"/>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useDeviceStore } from '@/client/stores/device'
import {Scatter} from 'vue-chartjs';
import {
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip
} from 'chart.js';

ChartJS.register(Title, Tooltip, Legend, LineElement, CategoryScale, LinearScale, PointElement);

const props = defineProps({
  partId: {
    type: Number,
    required: true
  }
})

const deviceStore = useDeviceStore()
const { ods } = storeToRefs(deviceStore)

const calibrationData = computed(() => ods.value?.calibration?.[props.partId])
const calibrationCoefs = computed(() => ods.value?.calibration_coefs?.[props.partId])
const currentOD = computed(() => ({od:ods.value?.states?.[props.partId], signal:ods.value?.odsignals?.[props.partId]}))

// function odCalibrationFunction(x, a, b, c, d, g) {
//   return d + ((a - d) / Math.pow((1 + Math.pow((x / c), b)), g));
// }

function beerLambertScaled(sig, blank, scaling) {
  return -Math.log10(sig / blank) * scaling;
}

const chartData = computed(() => {
  if (calibrationData.value && typeof calibrationData.value === 'object' && calibrationCoefs.value) {
    const dataPoints = Object.entries(calibrationData.value).map(([key, value]) => ({x: Number(value), y: Number(key)})).sort((a, b) => a.x - b.x);

    let min_x = Math.min(...dataPoints.map(point => point.x));
    let max_x = Math.max(...dataPoints.map(point => point.x));
    const calibrationDataPoints = [];
    if (min_x === max_x) {
      min_x = 0;
      max_x = 50;
    }
    for(let x = min_x; x <= max_x; x += 0.1) {
      const y = beerLambertScaled(x, ...calibrationCoefs.value);
      calibrationDataPoints.push({x, y});
    }

    return {
      datasets: [
        {
          label: `Vial ${props.partId} Calibration OD`,
          data: dataPoints,
          borderColor: '#607ecb',
          backgroundColor: 'rgba(83,158,255,0.64)',
        },
        {
          label: `Vial ${props.partId} Current OD`,
          data: [{x: currentOD.value.signal, y: currentOD.value.od}],
          pointRadius: 5,
          backgroundColor: 'rgba(255,1,60,0.64)',
        },
        {
          label: `Vial ${props.partId} Fit`,
          data: calibrationDataPoints,
          pointRadius: 0,
          borderColor: 'rgba(0,70,220,0.38)',
          //line width
          borderWidth: 2,
          showLine: true,
          fill: false,
          borderDash: [2, 2]
        },
      ],
    };
  }
  return {};
})

const chartOptions = computed(() => ({
  devicePixelRatio: 4,
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false,
    },
    title: {
      display: true,
      text: `Vial ${props.partId}` + (calibrationCoefs.value ? `\nblank: ${calibrationCoefs.value[0]?.toFixed(2)}, scaling: ${calibrationCoefs.value[1]?.toFixed(2)}` : ''),
    },
  },
  scales: {
    x: {
      title: {
        display: true,
        text: 'Signal (mV)',
      },
      // suggestedMax: 50,
      suggestedMin: 0,
    },
    y: {
      title: {
        display: true,
        text: 'OD',
      },
      suggestedMax: 1.5,
      suggestedMin: 0,
    },
  },
}))
</script>
