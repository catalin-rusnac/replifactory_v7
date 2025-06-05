import { defineStore } from 'pinia'
import api from '@/api'

export const useHostStore = defineStore('host', {
  state: () => ({
    hostname: null,
  }),
  actions: {
    async fetchHostname() {
      const response = await api.get('/hostname')
      this.hostname = response.data.hostname
    },
    setHostname(hostname) {
      this.hostname = hostname
    }
  }
})