<template>
  <div class="experiment-summary-container" ref="summaryContainer" :style="{ minHeight: containerHeight + 'px' }">
    <h2>
      Experiment Summary
      <span 
        class="info-icon" 
        @click="toast.info('Live experiment data summary with auto-refresh every 30 seconds.', { position: 'top-right', autoClose: 8000 })"
        style="cursor: pointer; margin-left: 8px; font-size: 0.8em;"
      >
        ⓘ
      </span>
    </h2>
    <div class="table-container" @mouseover="handleTableMouseOver" @mouseout="handleTableMouseOut">
      <TableComponent
        :key="tableKey"
        :fetchData="fetchTableData"
        :updateData="updateTableData"
        :columnHeaders="['Vial 1', 'Vial 2', 'Vial 3', 'Vial 4', 'Vial 5', 'Vial 6', 'Vial 7', 'Total']"
        rowHeaderLabel="Metric"
        :rowHeaderWidth="200"
        :readonly="true"
        :fixedRows="12"
      />
      <!-- Custom tooltip -->
      <div 
        v-if="tooltip.show" 
        class="custom-tooltip"
        :style="{ top: tooltip.y + 'px', left: tooltip.x + 'px' }"
      >
        {{ tooltip.text }}
      </div>
    </div>
    <div class="refresh-controls">
      <v-btn
        color="primary"
        size="small"
        :loading="loading"
        @click="refreshData"
      >
        <v-icon left>mdi-refresh</v-icon>
        Refresh
      </v-btn>
      <span class="last-updated">
        {{ lastUpdated ? `Last updated: ${lastUpdatedText}` : '' }}
      </span>
    </div>
  </div>
</template>

<script>
import { defineComponent, ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useExperimentStore } from '@/client/stores/experiment'
import { useDeviceStore } from '@/client/stores/device'
import { toast } from 'vue3-toastify'
import 'vue3-toastify/dist/index.css'
import TableComponent from '../PredictionTab/TableComponent.vue'

export default defineComponent({
  components: { TableComponent },
  setup() {
    const experimentStore = useExperimentStore()
    const deviceStore = useDeviceStore()

    const loading = ref(false)
    const lastUpdated = ref(null)
    const refreshInterval = ref(null)
    const tableKey = ref(0)
    const currentTime = ref(new Date())
    const timeInterval = ref(null)
    
    // Visibility tracking
    const isPageVisible = ref(true)
    const isComponentVisible = ref(true)
    const intersectionObserver = ref(null)
    const summaryContainer = ref(null)

    // Data structure for TableComponent - 2D array format
    const summaryData = ref([])

    const rowKeys = [
      'Last OD',
      'OD Timestamp',
      'Growth Rate (1/h)',
      'RPM (1h)',
      'Current Concentration',
      'Medium Used (1h)',
      'Medium Used (24h)',
      'Drug Used (1h)',
      'Drug Used (24h)',
      'Total Dilutions',
      'Last Dilution',
      'Runtime'
    ]

    const tooltipData = {
      'Last OD': 'Most recent optical density measurement',
      'OD Timestamp': 'Time when the last OD measurement was taken',
      'Growth Rate (1/h)': 'Current growth rate (mu)',
      'RPM (1h)': 'Average stirrer speed over the last hour (mean ± standard deviation)',
      'Current Concentration': 'Current drug concentration in the culture',
      'Medium Used (1h)': 'Volume of pump1 medium growth medium consumed in the last hour',
      'Medium Used (24h)': 'Volume of pump1 medium consumed in the last 24 hours',
      'Drug Used (1h)': 'Volume of pump2 medium (drug) consumed in the last hour',
      'Drug Used (24h)': 'Volume of pump2 medium (drug) consumed in the last 24 hours',
      'Total Dilutions': 'Total number of dilution events since experiment start',
      'Last Dilution': 'Most recent dilution event',
      'Runtime': 'Time between first and last OD measurements'
    }

    // Tooltip state
    const tooltip = ref({
      show: false,
      text: '',
      x: 0,
      y: 0
    })

    // Initialize empty data structure
    function initializeSummaryData() {
      summaryData.value = rowKeys.map(() => Array(8).fill('—'))
    }

    // Calculate totals for rows that make sense to sum
    function calculateTotals() {
      const rowsToSum = [5, 6, 7, 8, 9] // Medium Used (1h), Medium Used (24h), Drug Used (1h), Drug Used (24h), Total Dilutions
      
      for (const rowIndex of rowsToSum) {
        let total = 0
        let hasValidData = false
        
        // Sum values from vials 1-7 (indices 0-6)
        for (let vialIndex = 0; vialIndex < 7; vialIndex++) {
          const cellValue = summaryData.value[rowIndex][vialIndex]
          if (cellValue !== '—') {
            // Extract numeric value from strings like "1.5 mL"
            const numericValue = parseFloat(cellValue.toString().replace(/[^\d.-]/g, ''))
            if (!isNaN(numericValue)) {
              total += numericValue
              hasValidData = true
            }
          }
        }
        
        // Set total value
        if (hasValidData) {
          if (rowIndex === 9) {
            // Total Dilutions - no units
            summaryData.value[rowIndex][7] = total.toString()
          } else {
            // Volume measurements - add appropriate units
            const unit = rowIndex === 7 || rowIndex === 8 ? 'mL' : 'mL' // Drug uses mL, medium uses mL
            summaryData.value[rowIndex][7] = `${total.toFixed(2)} ${unit}`
          }
        } else {
          summaryData.value[rowIndex][7] = '—'
        }
      }
      
      // For rows that don't make sense to sum, show "—"
      const rowsNotToSum = [0, 1, 2, 3, 4, 10, 11] // Last OD, OD Timestamp, Growth Rate, RPM, Current Concentration, Last Dilution, Runtime
      for (const rowIndex of rowsNotToSum) {
        summaryData.value[rowIndex][7] = '—'
      }
    }

    // TableComponent interface functions
    async function fetchTableData() {
      return {
        data: summaryData.value,
        keys: rowKeys
      }
    }

    async function updateTableData(newData) {
      // This is read-only, so we don't actually update anything
      // Just log that someone tried to edit
      console.log('Summary table is read-only')
    }

    // Tooltip handlers
    function handleTableMouseOver(event) {
      const targetCell = event.target.closest('.rgCell')
      if (targetCell) {
        const cellText = targetCell.textContent?.trim()
        if (cellText && tooltipData[cellText]) {
          const rect = targetCell.getBoundingClientRect()
          const containerRect = summaryContainer.value.getBoundingClientRect()
          
          tooltip.value = {
            show: true,
            text: tooltipData[cellText],
            x: rect.left - containerRect.left,
            y: rect.top - containerRect.top - 40 // Show above the cell
          }
        }
      }
    }

    function handleTableMouseOut() {
      tooltip.value.show = false
    }

    // Format time for display - show "X seconds ago"
    function formatTime(timestamp) {
      if (!timestamp) return ''
      
      const now = currentTime.value
      const then = new Date(timestamp)
      const diffInSeconds = Math.max(0, Math.floor((now - then) / 1000))
      
      if (diffInSeconds < 60) {
        return `${diffInSeconds} seconds ago`
      } else if (diffInSeconds < 3600) {
        const minutes = Math.floor(diffInSeconds / 60)
        return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`
      } else {
        const hours = Math.floor(diffInSeconds / 3600)
        return `${hours} hour${hours !== 1 ? 's' : ''} ago`
      }
    }

    // Refresh data from backend
    async function refreshData() {
      loading.value = true
      try {
        await fetchExperimentSummary()
        lastUpdated.value = new Date()
      } catch (error) {
        console.error('Failed to refresh summary data:', error)
        toast.error(`Failed to refresh summary data: ${error.message || 'Unknown error'}`)
      } finally {
        loading.value = false
      }
    }

    // Fetch experiment summary data from backend
    async function fetchExperimentSummary() {
      const currentExperiment = experimentStore.currentExperiment
      if (!currentExperiment) {
        return
      }
      
      try {
        const backendSummary = await experimentStore.fetchExperimentSummary()
        
        // Also fetch bottle data when summary is updated
        await deviceStore.fetchDeviceData()
        await experimentStore.fetchCurrentExperiment()

        // Initialize/reset data structure
        if (summaryData.value.length === 0) {
          initializeSummaryData()
        }
        
        // Update summary data with backend response - populate 2D array
        // Explicitly limit to 7 vials to match column headers
        for (let vial = 1; vial <= 7; vial++) {
          const vialKey = `vial${vial}`
          const vialData = backendSummary[vialKey]
          const vialIndex = vial - 1 // Convert to 0-based index
          
          if (vialData) {
            summaryData.value[0][vialIndex] = (vialData.last_od !== null && vialData.last_od !== undefined) ? 
              vialData.last_od.toFixed(3) : '—'
            summaryData.value[1][vialIndex] = vialData.od_timestamp ? 
              new Date(vialData.od_timestamp).toLocaleTimeString() : '—'
            summaryData.value[2][vialIndex] = (vialData.growth_rate !== null && vialData.growth_rate !== undefined) ? 
              vialData.growth_rate.toFixed(3) : '—'
            
            // RPM data with mean ± std format
            if (vialData.rpm_mean_1h !== null && vialData.rpm_mean_1h !== undefined) {
              const mean = vialData.rpm_mean_1h.toFixed(0)
              const std = vialData.rpm_std_1h !== null ? vialData.rpm_std_1h.toFixed(0) : '0'
              summaryData.value[3][vialIndex] = `${mean} ± ${std}`
            } else {
              summaryData.value[3][vialIndex] = '—'
            }
            
            summaryData.value[4][vialIndex] = (vialData.current_concentration !== null && vialData.current_concentration !== undefined) ? 
              vialData.current_concentration.toFixed(3) : '—'
            summaryData.value[5][vialIndex] = (vialData.medium_used_1h !== null && vialData.medium_used_1h !== undefined) ? 
              `${vialData.medium_used_1h.toFixed(2)} mL` : '—'
            summaryData.value[6][vialIndex] = (vialData.medium_used_24h !== null && vialData.medium_used_24h !== undefined) ? 
              `${vialData.medium_used_24h.toFixed(2)} mL` : '—'
            summaryData.value[7][vialIndex] = (vialData.drug_used_1h !== null && vialData.drug_used_1h !== undefined) ? 
              `${vialData.drug_used_1h.toFixed(2)} mL` : '—'
            summaryData.value[8][vialIndex] = (vialData.drug_used_24h !== null && vialData.drug_used_24h !== undefined) ? 
              `${vialData.drug_used_24h.toFixed(2)} mL` : '—'
            summaryData.value[9][vialIndex] = vialData.total_dilutions || '—'
            summaryData.value[10][vialIndex] = vialData.last_dilution || '—'
            summaryData.value[11][vialIndex] = vialData.runtime || '—'
          } else {
            // No data for this vial - fill with dashes (only for the 7 vial columns)
            for (let rowIndex = 0; rowIndex < 12; rowIndex++) {
              summaryData.value[rowIndex][vialIndex] = '—'
            }
          }
        }
        
        // Calculate totals for the new Total column
        calculateTotals()
        
        // Force table re-render
        tableKey.value += 1
        
      } catch (error) {
        console.error('Error fetching experiment summary:', error)
        throw error
      }
    }

    // Visibility tracking functions
    const shouldAllowUpdates = () => {
      return isPageVisible.value && isComponentVisible.value
    }
    
    // Check if experiment is running and should auto-update
    const shouldAutoUpdate = () => {
      const currentExperiment = experimentStore.currentExperiment
      if (!currentExperiment) return false
      
      const isRunning = currentExperiment.status === 'running'
      const isVisible = shouldAllowUpdates()
      
      return isRunning && isVisible
    }
    
    function handleVisibilityChange() {
      isPageVisible.value = !document.hidden
    }
    
    function setupVisibilityObserver() {
      if (!summaryContainer.value) return
      
      intersectionObserver.value = new IntersectionObserver(
        (entries) => {
          isComponentVisible.value = entries[0].isIntersecting
        },
        {
          threshold: 0.1 // Component is considered visible when 10% is in view
        }
      )
      
      intersectionObserver.value.observe(summaryContainer.value)
    }

    // Auto-refresh every 30 seconds - only when visible and experiment is running
    function startAutoRefresh() {
      refreshInterval.value = setInterval(() => {
        // Only refresh if experiment is running and component is visible
        if (shouldAutoUpdate()) {
          refreshData()
        } else {
          const currentExperiment = experimentStore.currentExperiment
          const status = currentExperiment?.status || 'no experiment'
          const visible = shouldAllowUpdates() ? 'visible' : 'not visible'
          console.log(`ExperimentSummary: Skipping auto-refresh - experiment ${status}, component ${visible}`)
        }
      }, 30000)
    }

    function stopAutoRefresh() {
      if (refreshInterval.value) {
        clearInterval(refreshInterval.value)
        refreshInterval.value = null
      }
    }

    // Update current time every second
    function startTimeUpdater() {
      timeInterval.value = setInterval(() => {
        currentTime.value = new Date()
      }, 1000)
    }

    function stopTimeUpdater() {
      if (timeInterval.value) {
        clearInterval(timeInterval.value)
        timeInterval.value = null
      }
    }

    // Computed property for last updated display
    const lastUpdatedText = computed(() => {
      return lastUpdated.value ? formatTime(lastUpdated.value) : ''
    })

    // Computed property for container height based on number of rows
    const containerHeight = computed(() => {
      const numRows = rowKeys.length; // 12 rows
      const rowHeight = 32;
      const headerHeight = 55;
      const titleHeight = 40; // h2 + margin
      const refreshControlsHeight = 50;
      const padding = 20; // Extra buffer
      
      return (numRows * rowHeight) + headerHeight + titleHeight + refreshControlsHeight + padding;
    })

    // Watch for experiment changes and refresh table
    watch(() => experimentStore.currentExperiment?.id, (newId, oldId) => {
      if (newId !== oldId) {
        console.log('Experiment changed, refreshing summary table')
        // Reset data first to show loading state
        initializeSummaryData()
        tableKey.value += 1
        // Refresh with new experiment data
        refreshData()
      }
    }, { immediate: false })

    onMounted(() => {
      initializeSummaryData()
      refreshData()
      startAutoRefresh()
      startTimeUpdater()
      
      // Setup visibility tracking
      document.addEventListener('visibilitychange', handleVisibilityChange)
      setupVisibilityObserver()
      isPageVisible.value = !document.hidden
      
      // Fix horizontal scrolling - add wheel event listener
      if (summaryContainer.value) {
        const tableContainer = summaryContainer.value.querySelector('.table-container')
        if (tableContainer) {
          tableContainer.addEventListener('wheel', (e) => {
            if (e.deltaX !== 0) {
              // Horizontal scroll detected
              e.preventDefault()
              tableContainer.scrollLeft += e.deltaX
            } else if (e.shiftKey && e.deltaY !== 0) {
              // Shift + vertical scroll = horizontal scroll
              e.preventDefault()
              tableContainer.scrollLeft += e.deltaY
            }
          }, { passive: false })
        }
      }
    })

    onUnmounted(() => {
      stopAutoRefresh()
      stopTimeUpdater()
      
      // Cleanup visibility tracking
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      if (intersectionObserver.value) {
        intersectionObserver.value.disconnect()
      }
    })

          return {
        loading,
        lastUpdated,
        fetchTableData,
        updateTableData,
        formatTime,
        refreshData,
        toast,
        tableKey,
        lastUpdatedText,
        containerHeight,
        summaryContainer,
        isPageVisible,
        isComponentVisible,
        shouldAllowUpdates,
        tooltip,
        handleTableMouseOver,
        handleTableMouseOut
      }
  }
})
</script>

<style scoped>
.experiment-summary-container {
  /* Dynamic height calculated based on number of rows */
  width: 100%;
  max-width: none;
  margin: 0 auto;
  padding: 0 20px;
}

.table-container {
  width: 100%;
  min-width: 924px;
  /* Allow horizontal scroll when table is wider than viewport */
  overflow-x: auto;
  overflow-y: visible;
  position: relative;
}

h2 {
  margin: 0 0 10px 0;
  font-size: 1.2em;
  color: #fff;
  display: flex;
  align-items: center;
}

.info-icon {
  color: #666;
  font-weight: normal;
}

.refresh-controls {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #333;
  /* Fixed height to prevent layout shifts */
  height: 50px;
  min-height: 50px;
}

.last-updated {
  color: #666;
  font-size: 0.9em;
  /* Fixed width to prevent layout shifts */
  min-width: 200px;
  white-space: nowrap;
}

.custom-tooltip {
  position: absolute;
  background: rgba(0, 0, 0, 0.9);
  color: white;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 0.9em;
  max-width: 300px;
  z-index: 1000;
  pointer-events: none;
  white-space: normal;
  word-wrap: break-word;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.custom-tooltip::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  margin-left: -5px;
  border-width: 5px;
  border-style: solid;
  border-color: rgba(0, 0, 0, 0.9) transparent transparent transparent;
}
</style> 