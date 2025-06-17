<template>
  <div>
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
  </div>
</template>

<script>
import { defineComponent, ref, onMounted, watch, computed, onBeforeUnmount } from "vue";
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
    fixedRows: { type: Number, default: null }
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
    };

    // Listen for prop changes
    watch(() => props.columnHeaders, loadTableData, { immediate: true });

    // Setup wheel event handling for horizontal scroll
    onMounted(() => {
      // Wait for grid to be fully initialized
      setTimeout(() => {
        const gridElement = grid.value?.$el;
        if (gridElement) {
          gridElement.addEventListener('wheel', handleWheel, { passive: false });
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



    return { gridColumns, gridSource, handleEdit, tableHeight, rowHeight, plugins, grid, readonly: props.readonly };
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
  /* Prevent internal scrollbars */
  overflow: visible;
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

/* Enable horizontal scrolling for the parent container */
revo-grid {
  scroll-behavior: smooth;
  will-change: scroll-position;
  /* Allow wheel events to bubble up for horizontal scrolling */
  overflow-x: visible !important;
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

/* Prevent grid from extending beyond columns and internal scrollbars */
.hot-table revo-grid {
  overflow: visible;
}

</style>

