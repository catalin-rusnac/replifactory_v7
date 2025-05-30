<template>
  <div>
    <h3 v-if="tableTitle">{{ tableTitle }}</h3>
    <div ref="hotTable" class="hot-table"></div>
  </div>
</template>

<script>
import Handsontable from 'handsontable';
import 'handsontable/dist/handsontable.full.css';

export default {
  props: {
    fetchData: {
      type: Function,
      required: true
    },
    updateData: {
      type: Function,
      required: true
    },
    tableTitle: {
      type: String,
      default: ''
    },
    columnHeaders: {
      type: Array,
      default: () => []
    },
    rowHeaderLabel: {
      type: String,
      default: 'Row'
    },
    rowHeaderWidth: {
      type: Number,
      default: 200 // Default width if not provided
    }
  },
  mounted() {
    this.loadTableData();
  },
  methods: {
    async loadTableData() {
      const {data, keys} = await this.fetchData();
      const container = this.$refs.hotTable;

      this.hot = new Handsontable(container, {
        data,
        colHeaders: this.columnHeaders,
        rowHeaders: keys, // Use the parameter names as row headers
        contextMenu: true,
        afterChange: this.handleTableChange,
        licenseKey: 'non-commercial-and-evaluation',
        manualColumnResize: true,
        rowHeaderWidth: this.rowHeaderWidth
      });
    },
    async handleTableChange(changes) {
      if (changes) {

        const allData = this.hot.getData();
        await this.updateFullTable(allData);
      }
    },
    async updateFullTable(data) {
      try {
        // Replace this with the actual call to your backend
        await this.updateData(data);
      } catch (error) {
      }
    }
  }
};
</script>

<style>
@import "handsontable/dist/handsontable.full.css";
</style>
