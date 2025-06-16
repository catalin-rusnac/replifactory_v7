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
      :style="{ height: tableHeight }"
      :plugins="plugins"
      :hideAttribution="true"
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
    readonly: { type: Boolean, default: false }
  },
  setup(props) {
    const gridColumns = ref([]);
    const gridSource = ref([]);
    const rowHeight = 32;
    const tableHeight = computed(() =>
      (gridSource.value.length * rowHeight) + 55 + 'px'
    );

    const plugins = ref([HistoryPlugin]);
    const grid = ref();

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
          size: 130,
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
  min-width: 100%;
  max-width: 100%;
  /* Dark background for the table */
  background: #23272f;
  color: #e0e0e0;
  /* Add touch-action and other performance optimizations */
  touch-action: manipulation;
  -webkit-overflow-scrolling: touch;
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

</style>

