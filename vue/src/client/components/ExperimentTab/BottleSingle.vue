<!-- vue component of a single bottle showing assets/bottle.png. the bottle is filled with yellow liquid from bottom to top, using the bottle_mask.png from the same dir.  -->
 <!-- there are 2 text fields in the bottle, one on top for total volume, in gray, one on bottm for the current volume, in yellow. -->

<template>
  <div class="bottle-container">
    <div class="bottle">
      <div class="bottle-content">
        <img src="@/client/assets/bottle.png" alt="Bottle" class="bottle-image" :style="bottleImgStyle" ref="bottleImg" />
        <canvas ref="maskCanvas" class="mask-canvas" :width="canvasWidth" :height="canvasHeight"></canvas>
        <canvas ref="liquidCanvas" class="liquid-canvas" :width="canvasWidth" :height="canvasHeight"></canvas> 
      </div>
      <div class="volume-display">
        <div class="total-volume" 
             @dblclick="startEditing('total')"
             v-if="!editing.total"
             title="Max Volume">
          {{ totalVolume }}ml
        </div>
        <input v-else
               type="number"
               v-model.number="editingValue"
               @blur="finishEditing('total')"
               @keyup.enter="finishEditing('total')"
               @keyup.esc="cancelEditing"
               ref="volumeInput"
               class="volume-input"
               data-type="total"
               title="Max Volume"
        />
        <div class="current-volume"
             @dblclick="startEditing('current')"
             v-if="!editing.current"
             :title="`Current Volume: ${safeCurrentVolume}ml`">
          {{ safeCurrentVolume }}ml
        </div>
        <input v-else
               type="number"
               v-model.number="editingValue"
               @blur="finishEditing('current')"
               @keyup.enter="finishEditing('current')"
               @keyup.esc="cancelEditing"
               ref="volumeInput"
               class="volume-input"
               data-type="current"
               title="Current Volume"
        />
        <div v-if="showConcentration" class="concentration-container">
          <div v-if="!editing.concentration" 
               class="concentration"
               @dblclick="startEditing('concentration')"
               title="Drug Concentration">
            {{ concentration !== null && concentration !== undefined ? Number(concentration).toFixed(2) : '' }}
          </div>
          <input v-else
                 type="number"
                 v-model.number="editingValue"
                 @blur="finishEditing('concentration')"
                 @keyup.enter="finishEditing('concentration')"
                 @keyup.esc="cancelEditing"
                 ref="volumeInput"
                 class="volume-input"
                 data-type="concentration"
                 title="Drug Concentration"
          />
          <div v-if="!editing.units" 
               class="units"
               @dblclick="startEditing('units')"
               title="Concentration Units (for reference only)">
            {{ units }}
          </div>
          <input v-else
                 type="text"
                 v-model="editingValue"
                 @input="handleInput('units')"
                 @blur="finishEditing('units')"
                 @keyup.esc="cancelEditing"
                 ref="volumeInput"
                 class="volume-input"
                 data-type="units"
                 title="Concentration Units (for reference only)"
          />
        </div>
      </div>
      <div class="bottle-name">
        {{ bottleName }}
      </div>
      <div v-if="icon" class="bottle-icon" :class="{ 'waste-icon': bottleName === 'waste' }">
        <v-icon :icon="icon" :size="bottleName === 'waste' ? 36 : 48" />
      </div>
    </div>
  </div>
</template>

<script>
import bottleMask from '@/client/assets/bottle_mask.png'

export default {
  name: 'BottleSingle',
  props: {
    totalVolume: {
      type: Number,
      required: true
    },
    currentVolume: {
      type: Number,
      required: true
    },
    bottleName: {
      type: String,
      required: true,
      validator: (value) => ['main', 'drug', 'waste'].includes(value)
    },
    icon: {
      type: String,
      default: ''
    },
    liquidColor: {
      type: String,
      default: 'rgba(255, 215, 0, 0.6)'
    },
    concentration: {
      type: Number,
      default: null
    },
    units: {
      type: String,
      default: 'units'
    }
  },
  data() {
    return {
      maskImage: new Image(),
      maskLoaded: false,
      maskData: null,
      editing: {
        total: false,
        current: false,
        concentration: false,
        units: false
      },
      editingValue: 0,
      bottleNaturalWidth: 0,
      bottleNaturalHeight: 0,
      canvasWidth: 150,
      canvasHeight: 0,
      updateTimeout: null,
      isUpdating: false
    }
  },
  computed: {
    safeCurrentVolume() {
      if (typeof this.currentVolume === 'number' && !isNaN(this.currentVolume)) {
        return this.currentVolume.toFixed(1);
      }
      return '---';
    },
    showConcentration() {
      return this.bottleName === 'drug' && this.concentration !== null && this.bottleName !== 'waste'
    },
    bottleScale() {
      // Scale based on cube root of volume ratio compared to 1000ml, with min and max limits
      const effectiveVolume = Math.min(Math.max(this.totalVolume, 100), 5000)
      return Math.max(Math.pow(effectiveVolume / 1000, 1/3), 0.5)
    },
    bottleNameStyle() {
      return {
        transform: `translateX(-50%) scale(${1/this.bottleScale})`,
        fontSize: `${1.2 * this.bottleScale}rem`
      }
    },
    fillPercentage() {
      // Calculate effective fill percentage considering 10% head space
      const effectiveTotalVolume = this.totalVolume * 1.21 // 110% of total volume to account for head space
      // adjust this considering volumetric effects - the height difference is 1.1**2
      return Math.min((this.currentVolume / effectiveTotalVolume) * 100, 100)
    },
    bottleImgStyle() {
      const img = this.$refs.bottleImg
      const srcW = img?.naturalWidth || 100
      const srcH = img?.naturalHeight || 200
      const { drawW, drawH, offsetX, offsetY } = this.getImageDrawParams(srcW, srcH)
      return {
        width: drawW + 'px',
        height: drawH + 'px',
        left: offsetX + 'px',
        top: offsetY + 'px',
        position: 'absolute',
        background: 'transparent',
        zIndex: 1,
        transition: 'filter 0.3s',
        display: 'block',
        objectFit: 'fill',
      }
    },
    bottleContainerStyle() {
      const aspectRatio = this.bottleNaturalWidth / this.bottleNaturalHeight
      const width = 150
      const height = width / aspectRatio
      return {
        width: width + 'px',
        height: height + 'px'
      }
    }
  },
  methods: {
    getImageDrawParams(srcW, srcH) {
      const destW = this.canvasWidth
      const destH = this.canvasHeight
      const scale = Math.min(destW / srcW, destH / srcH)
      const drawW = srcW * scale
      const drawH = srcH * scale
      const offsetX = (destW - drawW) / 2
      const offsetY = (destH - drawH) / 2
      return { drawW, drawH, offsetX, offsetY, scale }
    },
    updateLiquid() {
      if (!this.maskLoaded || !this.maskData) return
      
      const canvas = this.$refs.liquidCanvas
      const ctx = canvas.getContext('2d')
      const { drawW, drawH, offsetX, offsetY, scale } = this.getImageDrawParams(this.maskImage.width, this.maskImage.height)
      
      // Clear the canvas
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      
      // Find the top and bottom boundaries of the mask
      let maskTop = canvas.height
      let maskBottom = 0
      
      for (let y = 0; y < canvas.height; y++) {
        for (let x = 0; x < canvas.width; x++) {
          const maskIdx = (y * canvas.width + x) * 4
          const isBlack = this.maskData[maskIdx] < 20 && 
                         this.maskData[maskIdx + 1] < 20 && 
                         this.maskData[maskIdx + 2] < 20 && 
                         this.maskData[maskIdx + 3] === 255
          
          if (isBlack) {
            maskTop = Math.min(maskTop, y)
            maskBottom = Math.max(maskBottom, y)
          }
        }
      }
      
      const maskHeight = maskBottom - maskTop
      const fillHeight = (this.fillPercentage / 100) * maskHeight
      const fillLine = maskBottom - fillHeight
      
      // Draw liquid only where mask is black and below the fill line
      for (let y = 0; y < canvas.height; y++) {
        for (let x = 0; x < canvas.width; x++) {
          const maskIdx = (y * canvas.width + x) * 4
          const isBlack = this.maskData[maskIdx] < 20 && 
                         this.maskData[maskIdx + 1] < 20 && 
                         this.maskData[maskIdx + 2] < 20 && 
                         this.maskData[maskIdx + 3] === 255
          
          if (y >= fillLine && isBlack) {
            ctx.fillStyle = this.liquidColor
            ctx.fillRect(x, y, 1, 1)
          }
        }
      }
    },
    startEditing(field) {
      console.log(`[BottleSingle] Starting edit for field: ${field}`)
      console.log(`[BottleSingle] Current props - totalVolume: ${this.totalVolume}, currentVolume: ${this.currentVolume}`)
      
      this.editing[field] = true
      // Round to 4 decimal places for numeric fields
      if (field === 'total' || field === 'current' || field === 'concentration') {
        this.editingValue = Number(Number(field === 'total' ? this.totalVolume : 
                                        field === 'current' ? this.currentVolume :
                                        this.concentration).toFixed(4))
      } else {
        this.editingValue = field === 'units' ? this.units : 0
      }
      
      console.log(`[BottleSingle] Set editingValue to: ${this.editingValue}`)
      
      this.$nextTick(() => {
        this.$refs.volumeInput.focus()
      })
    },
    handleInput(field) {
      console.log(`[BottleSingle] Handle input for field: ${field}, value: ${this.editingValue}`)
      
      if (this.updateTimeout) {
        clearTimeout(this.updateTimeout)
      }
      // Don't update on input, just store the value
      // Only convert to number for numeric fields, leave units as string
      if (field !== 'units') {
        this.editingValue = Number(this.editingValue)
      }
      
      console.log(`[BottleSingle] Processed editingValue: ${this.editingValue}`)
    },
    finishEditing(field) {
      console.log(`[BottleSingle] Finishing edit for field: ${field}`)
      console.log(`[BottleSingle] Final editingValue: ${this.editingValue}, isUpdating: ${this.isUpdating}`)
      
      if (this.isUpdating) return
      this.isUpdating = true
      
      if (field === 'units' || this.editingValue >= 0) {
        const oldValue = field === 'total' ? this.totalVolume : 
                        field === 'current' ? this.currentVolume :
                        field === 'concentration' ? this.concentration :
                        this.units;
        
        const eventName = 'update:' + (field === 'total' ? 'totalVolume' : 
                               field === 'current' ? 'currentVolume' :
                               field === 'concentration' ? 'concentration' :
                               'units');
        
        console.log(`[BottleSingle] Emitting ${eventName} with value: ${this.editingValue} (old value: ${oldValue})`)
        
        this.$emit(eventName, this.editingValue)
      } else {
        console.log(`[BottleSingle] Skipping emit - invalid value: ${this.editingValue}`)
      }
      
      this.editing[field] = false
      
      // Reset the flag after a short delay
      setTimeout(() => {
        this.isUpdating = false
      }, 100)
    },
    cancelEditing() {
      console.log(`[BottleSingle] Canceling edit`)
      
      if (this.updateTimeout) {
        clearTimeout(this.updateTimeout)
      }
      this.editing.total = false
      this.editing.current = false
      this.editing.concentration = false
      this.editing.units = false
    }
  },
  watch: {
    fillPercentage() {
      this.updateLiquid()
    }
  },
  mounted() {
    this.maskImage.src = bottleMask
    this.maskImage.onload = () => {
      const canvas = this.$refs.maskCanvas
      const ctx = canvas.getContext('2d')
      const srcW = this.maskImage.width
      const srcH = this.maskImage.height
      const { drawW, drawH, offsetX, offsetY, scale } = this.getImageDrawParams(srcW, srcH)
      
      // Draw mask at exact same position as bottle
      ctx.clearRect(0, 0, this.canvasWidth, this.canvasHeight)
      ctx.drawImage(this.maskImage, offsetX, offsetY, drawW, drawH)
      
      // Store mask data for liquid fill
      this.maskData = ctx.getImageData(0, 0, this.canvasWidth, this.canvasHeight).data
      this.maskLoaded = true
      
      // Initial liquid update
      this.updateLiquid()
    }

    // Get natural dimensions of bottle image
    const bottleImg = this.$refs.bottleImg
    if (bottleImg) {
      bottleImg.onload = () => {
        this.bottleNaturalWidth = bottleImg.naturalWidth
        this.bottleNaturalHeight = bottleImg.naturalHeight
        // Calculate canvas dimensions based on bottle's natural size
        const aspectRatio = this.bottleNaturalHeight / this.bottleNaturalWidth
        this.canvasWidth = 150
        this.canvasHeight = Math.round(this.canvasWidth * aspectRatio)
      }
    }
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.updateCanvasSize)
  }
}
</script>

<style scoped>
.bottle-container {
  position: relative;
  width: v-bind(canvasWidth + 'px');
  height: v-bind(canvasHeight + 'px');
  transform: scale(v-bind(bottleScale));
  transform-origin: bottom center;
  display: flex;
  align-items: flex-end;
  min-width: 50px;
  max-width: 150px;
  width: 100%;
}

.bottle {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: flex-end;
}

.bottle-content {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  overflow: hidden;
}

.bottle-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  position: absolute;
  left: 0;
  bottom: 0;
  z-index: 1;
  transition: filter 0.3s;
}

.mask-canvas, .liquid-canvas {
  position: absolute;
  width: 100%;
  height: 100%;
  z-index: 0;
  bottom: 0;
  left: 0;
  object-fit: contain;
}

.mask-canvas {
  opacity: 0;
  pointer-events: none;
}

.liquid-canvas {
  pointer-events: none;
}

.volume-display {
  position: absolute;
  width: 100%;
  height: 100%;
  z-index: 2;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  pointer-events: none;
  bottom: 0;
  left: 0;
}

.total-volume, .current-volume {
  pointer-events: auto;
  cursor: text;
  user-select: none;
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}

.total-volume {
  top: 80px;
  font-size: 1rem;
  font-weight: 600;
  color: #333333;
}

.current-volume {
  bottom: 32px;
  color: #FFD700;
  font-size: 16px;
  text-align: center;
  background-color: rgba(0, 0, 0, 0.7);
  padding: 3px 6px;
  border-radius: 4px;
  text-shadow: 1px 1px 1px rgba(0, 0, 0, 0.5);
}

.volume-input {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  width: 120px;
  text-align: center;
  padding: 2px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.9rem;
  background: transparent;
  color: #2c3e50;
  z-index: 3;
}

.volume-input:focus {
  outline: none;
  border-color: #2196F3;
  box-shadow: 0 0 0 2px rgba(33, 150, 243, 0.2);
}

.volume-input[data-type="total"] {
  top: 80px;
}

.volume-input[data-type="current"] {
  bottom: 32px;
  color: #FFD700;
  background-color: rgba(0, 0, 0, 0.7);
  border: 1px solid #FFD700;
}

.bottle-name {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  top: 20%;
  font-size: 16px;
  font-weight: bold;
  color: #FFFFFF;
  text-align: center;
  width: 100%;
  z-index: 2;
  pointer-events: none;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
}

.bottle-icon {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  z-index: 2;
  color: #8B0000;
  filter: drop-shadow(0 0 4px rgba(139, 0, 0, 0.6));
}

.waste-icon {
  color: #666666;
  filter: drop-shadow(0 0 4px rgba(102, 102, 102, 0.6));
}

.concentration-container {
  position: absolute;
  left: 50%;
  bottom: 65px;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 4px;
  z-index: 3;
  pointer-events: auto;
}

.concentration, .units {
  font-size: 14px;
  color: #FF4444;
  background-color: rgba(0, 0, 0, 0.7);
  padding: 2px 6px;
  border-radius: 4px;
  cursor: text;
  user-select: none;
}

.volume-input[data-type="concentration"], .volume-input[data-type="units"] {
  color: #FF4444;
  background-color: rgba(0, 0, 0, 0.7);
  border: 1px solid #FF4444;
}

.volume-input[data-type="concentration"] {
  width: 120px;
}

.volume-input[data-type="units"] {
  width: 60px;
}
</style>
 