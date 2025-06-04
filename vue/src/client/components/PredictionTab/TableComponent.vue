<template>
  <div>
    <RevoGrid
      :columns="gridColumns"
      :source="gridSource"
      :readonly="false"
      @afteredit="handleEdit"
      class="hot-table"
      :theme="'material'"
      :range="true"
      :rowHeaders="true"
      :rowHeaderWidth="270"
    />
  </div>
</template>

<script>
import { defineComponent, ref, onMounted, watch } from "vue";
import RevoGrid from '@revolist/vue3-datagrid';

export default defineComponent({
  components: { RevoGrid },
  props: {
    fetchData: { type: Function, required: true },
    updateData: { type: Function, required: true },
    columnHeaders: { type: Array, default: () => [] },
    rowHeaderLabel: { type: String, default: "Row" },
    rowHeaderWidth: { type: Number, default: 270 }
  },
  setup(props) {
    const gridColumns = ref([]);
    const gridSource = ref([]);

    const loadTableData = async () => {
      console.log("loading table data");
      const { data, keys } = await props.fetchData();
      console.log(data, keys);

      // Add row header column
      gridColumns.value = [
        {
          prop: 'rowHeader',
          name: props.rowHeaderLabel,
          size: props.rowHeaderWidth,
          readonly: true
        },
        ...props.columnHeaders.map((name, idx) => ({
          prop: `col${idx}`,
          name,
          size: 120
        }))
      ];

      // Map your data into objects with properties matching columns
      gridSource.value = data.map((row, rIdx) => {
        const obj = { rowHeader: keys[rIdx] };
        row.forEach((cell, cIdx) => {
          obj[`col${cIdx}`] = cell;
        });
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

    return { gridColumns, gridSource, handleEdit };
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
  /* Remove scrollbars and allow table to expand */
  overflow: visible !important;
  height: auto !important;
  max-height: none !important;
}

/* RevoGrid cell and header styling for dark mode */
.hot-table .rgCell,
.hot-table .rgHeaderCell,
.hot-table .rgRowHeaderCell {
  background: #23272f !important;
  color: #e0e0e0 !important;
}

.hot-table .rgHeaderCell {
  font-weight: bold;
}

.hot-table .rgCell:focus {
  outline: 1px solid #90caf9;
}

/* Remove scrollbars from RevoGrid inner containers */
.hot-table .rgContent,
.hot-table .rgViewport,
.hot-table .rgRows,
.hot-table .rgHeader,
.hot-table .rgRowHeaders {
  overflow: visible !important;
  max-height: none !important;
}
</style>
