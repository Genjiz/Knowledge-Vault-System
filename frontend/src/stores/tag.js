import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as tagApi from '@/api/tag'

export const useTagStore = defineStore('tag', () => {
  const tags = ref([])
  const loading = ref(false)
  
  async function fetchTags() {
    loading.value = true
    try {
      tags.value = await tagApi.getTags()
      return tags.value
    } finally {
      loading.value = false
    }
  }
  
  async function createTag(data) {
    const newTag = await tagApi.createTag(data)
    await fetchTags()
    return newTag
  }
  
  async function updateTag(id, data) {
    const updated = await tagApi.updateTag(id, data)
    await fetchTags()
    return updated
  }
  
  async function deleteTag(id) {
    await tagApi.deleteTag(id)
    await fetchTags()
  }
  
  return {
    tags,
    loading,
    fetchTags,
    createTag,
    updateTag,
    deleteTag
  }
})
