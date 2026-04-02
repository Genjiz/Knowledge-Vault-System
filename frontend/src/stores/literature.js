import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as literatureApi from '@/api/literature'

export const useLiteratureStore = defineStore('literature', () => {
  const literatures = ref([])
  const currentLiterature = ref(null)
  const loading = ref(false)
  const total = ref(0)
  const statistics = ref(null)
  
  async function fetchLiteratures(params) {
    loading.value = true
    try {
      const result = await literatureApi.getLiteratures(params)
      literatures.value = result.items
      total.value = result.total
      return result
    } finally {
      loading.value = false
    }
  }
  
  async function fetchLiterature(id) {
    loading.value = true
    try {
      currentLiterature.value = await literatureApi.getLiterature(id)
      return currentLiterature.value
    } finally {
      loading.value = false
    }
  }
  
  async function createLiterature(data) {
    const newLiterature = await literatureApi.createLiterature(data)
    literatures.value.unshift(newLiterature)
    total.value++
    return newLiterature
  }
  
  async function updateLiterature(id, data) {
    const updated = await literatureApi.updateLiterature(id, data)
    const index = literatures.value.findIndex(l => l.id === id)
    if (index !== -1) {
      literatures.value[index] = updated
    }
    if (currentLiterature.value?.id === id) {
      currentLiterature.value = updated
    }
    return updated
  }
  
  async function deleteLiterature(id) {
    await literatureApi.deleteLiterature(id)
    literatures.value = literatures.value.filter(l => l.id !== id)
    total.value--
  }
  
  async function fetchStatistics() {
    statistics.value = await literatureApi.getStatistics()
    return statistics.value
  }
  
  return {
    literatures,
    currentLiterature,
    loading,
    total,
    statistics,
    fetchLiteratures,
    fetchLiterature,
    createLiterature,
    updateLiterature,
    deleteLiterature,
    fetchStatistics
  }
})
