<template>
  <div @mouseover="handleMouseOver" @mouseout="handleMouseOut">
    <RevoGrid
      ref="grid"
      :columns="gridColumns"
      :source="gridSource"
      :readonly="readonly"
      @afteredit="handleEdit"
      class="hot-table"
      :theme="'material'"
      :range="true"
      :rowHeaders="false"
      :rowSize="rowHeight"
      :style="{ height: tableHeight, width: 'fit-content' }"
      :plugins="plugins"
      :hideAttribution="true"
      :stretch="false"
    />
    
    <!-- Tooltip -->
    <div
      v-if="tooltip.show"
      class="custom-tooltip"
      :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
    >
      <div class="tooltip-header">{{ tooltip.paramName }}</div>
      <div class="tooltip-description">{{ tooltip.text }}</div>
      <div class="tooltip-arrow"></div>
    </div>
  </div>
</template>

<script>
import { defineComponent, ref, onMounted, watch, computed, onBeforeUnmount, nextTick } from "vue";
import RevoGrid from '@revolist/vue3-datagrid';
import {
  HistoryPlugin,
} from '@revolist/revogrid-pro';

export default defineComponent({
  components: { RevoGrid },
  props: {
    fetchData: { type: Function, required: true },
    updateData: { type: Function, required: true },
    columnHeaders: { type: Array, default: () => [] },
    rowHeaderLabel: { type: String, default: "Row" },
    rowHeaderWidth: { type: Number, default: 270 },
    readonly: { type: Boolean, default: false },
    fixedRows: { type: Number, default: null },
    rowTooltips: { type: Object, default: () => ({}) }
  },
  setup(props) {
    const gridColumns = ref([]);
    const gridSource = ref([]);
    const rowHeight = 32;
    const tableHeight = computed(() => {
      const rows = props.fixedRows || gridSource.value.length;
      return (rows * rowHeight) + 55 + 'px';
    });

    const plugins = ref([HistoryPlugin]);
    const grid = ref();

    // Tooltip state
    const tooltip = ref({
      show: false,
      text: '',
      paramName: '',
      x: 0,
      y: 0
    });

    // Tooltip handlers
    const showTooltip = (event, rowKey) => {
      if (props.rowTooltips[rowKey]) {
        tooltip.value.text = props.rowTooltips[rowKey];
        tooltip.value.paramName = rowKey;
        tooltip.value.x = event.clientX + 10;
        tooltip.value.y = event.clientY - 10;
        tooltip.value.show = true;
        
        // Add highlighting to the target element
        event.target.classList.add('tooltip-highlighted');
      }
    };

    const hideTooltip = (targetElement = null) => {
      tooltip.value.show = false;
      
      // Remove highlighting from the target element
      if (targetElement) {
        targetElement.classList.remove('tooltip-highlighted');
      }
      // Also remove from any elements that might still have the class
      const highlighted = document.querySelectorAll('.tooltip-highlighted');
      highlighted.forEach(el => el.classList.remove('tooltip-highlighted'));
    };

    // Mouse event handlers for the wrapper div
    const handleMouseOver = (event) => {
      const target = event.target;
      if (target && target.textContent) {
        const paramKey = Object.keys(props.rowTooltips).find(key => 
          target.textContent.trim() === key
        );
        if (paramKey) {
          showTooltip(event, paramKey);
        }
      }
    };

    const handleMouseOut = (event) => {
      const target = event.target;
      if (target && target.textContent) {
        const paramKey = Object.keys(props.rowTooltips).find(key => 
          target.textContent.trim() === key
        );
        if (paramKey) {
          hideTooltip(target);
        }
      }
    };

    // Handle horizontal scrolling with shift+wheel or when no vertical scroll is possible
    const handleWheel = (event) => {
      const gridElement = grid.value?.$el;
      if (!gridElement) return;
      
      const scrollContainer = gridElement.closest('[style*="overflow-x"]') || 
                             gridElement.closest('.table-scroll-container');
      
      if (scrollContainer && (event.shiftKey || Math.abs(event.deltaX) > Math.abs(event.deltaY))) {
        event.preventDefault();
        const scrollAmount = event.deltaY || event.deltaX;
        scrollContainer.scrollLeft += scrollAmount;
      }
    };



    const loadTableData = async () => {
      const { data, keys } = await props.fetchData();
      // Add row header column
      gridColumns.value = [
        {
          prop: 'rowHeader',
          name: props.rowHeaderLabel,
          size: props.rowHeaderWidth,
          readonly: true,
          resizable: true
        },
        ...props.columnHeaders.map((name, idx) => ({
          prop: `col${idx}`,
          name,
          size: 140,
          resizable: true
        }))
      ];

      // Map your data into objects with properties matching columns
      gridSource.value = data.map((row, rIdx) => {
        const obj = { rowHeader: keys[rIdx] };
        // Only map cells up to the number of column headers to prevent extra columns
        for (let cIdx = 0; cIdx < Math.min(row.length, props.columnHeaders.length); cIdx++) {
          obj[`col${cIdx}`] = row[cIdx];
        }
        return obj;
      });

      // Add tooltip event listeners after grid is rendered
      nextTick(() => {
        setupTooltipListeners(keys);
      });
    };

    const setupTooltipListeners = (keys) => {
      setTimeout(() => {
        const gridElement = grid.value?.$el;
        if (gridElement) {
          // Try multiple selectors to find row header cells
          let rowHeaderCells = gridElement.querySelectorAll('.rgRowHeaderCell');
          if (rowHeaderCells.length === 0) {
            rowHeaderCells = gridElement.querySelectorAll('[data-rgrow]');
          }
          if (rowHeaderCells.length === 0) {
            rowHeaderCells = gridElement.querySelectorAll('revogrid-row-header');
          }
          if (rowHeaderCells.length === 0) {
            // Try looking for cells containing the row header text
            rowHeaderCells = Array.from(gridElement.querySelectorAll('*')).filter(el => 
              keys.some(key => el.textContent && el.textContent.includes(key))
            );
          }
          
          // Instead of relying on index position, match by text content
          rowHeaderCells.forEach((cell) => {
            const cellText = cell.textContent?.trim();
            if (cellText && props.rowTooltips[cellText]) {
              cell.style.cursor = 'help';
              cell.addEventListener('mouseenter', (e) => showTooltip(e, cellText));
              cell.addEventListener('mouseleave', () => hideTooltip(cell));
            }
          });
        }
      }, 500);
    };

    // Listen for prop changes
    watch(() => props.columnHeaders, loadTableData, { immediate: true });
    
    // Also watch for rowTooltips changes
    watch(() => props.rowTooltips, () => {
      const { keys } = props.fetchData();
      nextTick(() => {
        setupTooltipListeners(keys);
      });
    }, { immediate: true });

    // Setup wheel event handling for horizontal scroll
    onMounted(() => {
      // Wait for grid to be fully initialized
      setTimeout(() => {
        const gridElement = grid.value?.$el;
        if (gridElement) {
          gridElement.addEventListener('wheel', handleWheel, { passive: false });
          
          // Alternative approach: listen for mouseover on the entire grid
          gridElement.addEventListener('mouseover', (e) => {
            const target = e.target;
            if (target && target.textContent) {
              // Check if the target contains any of our parameter names
              const paramKey = Object.keys(props.rowTooltips).find(key => 
                target.textContent.trim() === key
              );
              if (paramKey) {
                showTooltip(e, paramKey);
              }
            }
          });
          
          gridElement.addEventListener('mouseout', (e) => {
            const target = e.target;
            if (target && target.textContent) {
              const paramKey = Object.keys(props.rowTooltips).find(key => 
                target.textContent.trim() === key
              );
              if (paramKey) {
                hideTooltip();
              }
            }
          });
        }
      }, 100);
    });

    onBeforeUnmount(() => {
      const gridElement = grid.value?.$el;
      if (gridElement) {
        gridElement.removeEventListener('wheel', handleWheel);
      }
    });

    // Editing callback
    const handleEdit = async (event) => {
      // After edit, convert back to original structure and send to updateData
      const allData = gridSource.value.map(row =>
        props.columnHeaders.map((_, idx) => row[`col${idx}`])
      );
      await props.updateData(allData);
    };



    return { gridColumns, gridSource, handleEdit, tableHeight, rowHeight, plugins, grid, readonly: props.readonly, tooltip, handleMouseOver, handleMouseOut };
  }
});
</script>

<style>
.hot-table {
  width: fit-content;
  max-width: fit-content;
  /* Dark background for the table */
  background: #23272f;
  color: #e0e0e0;
  /* Add touch-action and other performance optimizations */
  touch-action: manipulation;
  -webkit-overflow-scrolling: touch;
  /* Allow proper scrolling */
  overflow: auto;
}

.hot-table .rgHeaderCell,
.hot-table .rgRowHeaderCell {
  background: #23272f !important;
  color: #737373 !important;
  font-weight: bold;
  font-size: 19px;
  /* Performance optimizations */
  touch-action: manipulation;
}
.hot-table .rgCell {
  background: #23272f !important;
  color: #c6cfd7 !important;
  font-size: 17px;
  /* Performance optimizations */
  touch-action: manipulation;
}

/* Style the editor's container */
.hot-table .edit-input-wrapper {
  background: #282f47 !important;
}

/* Add passive scroll handling for the grid container */
.hot-table * {
  touch-action: manipulation;
}

/* More comprehensive RevoGrid optimizations */
revo-grid,
revo-grid *,
revogrid-data,
revogrid-data *,
.rgViewport,
.rgRow {
  touch-action: manipulation !important;
  -ms-touch-action: manipulation !important;
  overscroll-behavior: contain;
}

/* Enable proper scrolling for the grid container */
revo-grid {
  scroll-behavior: smooth;
  will-change: scroll-position;
  /* Allow proper scrolling */
  overflow: auto !important;
  /* Constrain grid to content size */
  width: fit-content !important;
  max-width: fit-content !important;
}

/* Fix wheel scrolling for horizontal scroll */
.hot-table revo-grid {
  pointer-events: auto;
}

.hot-table revo-grid * {
  /* Allow horizontal wheel scrolling to bubble up */
  overscroll-behavior-x: auto;
}

/* Hide extra grid areas beyond content */
.hot-table .rgViewport,
.hot-table .rgRow {
  width: fit-content !important;
  max-width: none !important;
}

/* Allow proper scrolling within the grid */
.hot-table revo-grid {
  overflow: auto;
}

/* Tooltip styles */
.custom-tooltip {
  position: fixed;
  background: #2d3748;
  color: #e2e8f0;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
  max-width: 300px;
  z-index: 10000;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
  border: 1px solid #4a5568;
  pointer-events: none;
}

.tooltip-header {
  font-weight: bold;
  font-size: 14px;
  color: #4a90e2;
  margin-bottom: 4px;
  border-bottom: 1px solid #4a5568;
  padding-bottom: 4px;
}

.tooltip-description {
  font-size: 13px;
  line-height: 1.4;
}

.tooltip-arrow {
  position: absolute;
  top: -5px;
  left: 10px;
  width: 0;
  height: 0;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-bottom: 5px solid #2d3748;
}

/* Highlighting for tooltip target */
.tooltip-highlighted {
  background-color: #4a90e2 !important;
  color: #ffffff !important;
  border-radius: 3px !important;
  padding: 2px 4px !important;
  transition: all 0.2s ease-in-out !important;
  box-shadow: 0 0 8px rgba(74, 144, 226, 0.4) !important;
}

</style>

