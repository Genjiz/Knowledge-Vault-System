import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import * as crawlerTaskApi from '@/api/crawlerTask'
import * as rawIssueApi from '@/api/rawIssue'

export const useCrawlerStore = defineStore('crawler', () => {
  const tasks = ref([])
  const rawIssues = ref([])
  const currentIssue = ref(null)
  const currentAnalysis = ref(null)
  const loadingCounter = ref(0)
  const loading = computed(() => loadingCounter.value > 0)
  const submitting = ref(false)

  function beginLoading() {
    loadingCounter.value += 1
  }

  function endLoading() {
    loadingCounter.value = Math.max(0, loadingCounter.value - 1)
  }

  async function fetchTasks() {
    beginLoading()
    try {
      const result = await crawlerTaskApi.getCrawlTasks()
      if (Array.isArray(result)) {
        tasks.value = result
      } else if (Array.isArray(result?.items)) {
        tasks.value = result.items
      } else {
        tasks.value = []
      }
      return tasks.value
    } finally {
      endLoading()
    }
  }

  async function createTask(data) {
    submitting.value = true
    try {
      const result = await crawlerTaskApi.createCrawlTask(data)
      await fetchTasks()
      return result
    } finally {
      submitting.value = false
    }
  }

  async function fetchRawIssues() {
    beginLoading()
    try {
      const result = await rawIssueApi.getRawIssues()
      if (Array.isArray(result?.items)) {
        rawIssues.value = result.items
      } else if (Array.isArray(result)) {
        rawIssues.value = result
      } else {
        rawIssues.value = []
      }
      return rawIssues.value
    } finally {
      endLoading()
    }
  }

  async function fetchRawIssue(id) {
    beginLoading()
    try {
      currentIssue.value = await rawIssueApi.getRawIssue(id)
      return currentIssue.value
    } finally {
      endLoading()
    }
  }

  async function translateIssue(id) {
    try {
      const result = await rawIssueApi.translateRawIssue(id)
      if (currentIssue.value?.id === Number(id)) {
        currentIssue.value = await rawIssueApi.getRawIssue(id)
      }
      return result
    } catch (error) {
      if (error?.isBackgroundTimeout) {
        setTimeout(() => {
          if (currentIssue.value?.id === Number(id)) {
            fetchRawIssue(id).catch(() => {})
          }
        }, 5000)
        return { backgroundRunning: true }
      }
      throw error
    }
  }

  async function analyzeIssue(id) {
    try {
      currentAnalysis.value = await rawIssueApi.analyzeRawIssue(id)
      return currentAnalysis.value
    } catch (error) {
      if (error?.isBackgroundTimeout) {
        setTimeout(() => {
          fetchAnalysis(id).catch(() => {})
        }, 5000)
        return { backgroundRunning: true }
      }
      throw error
    }
  }

  async function fetchAnalysis(id) {
    currentAnalysis.value = await rawIssueApi.getRawIssueAnalysis(id)
    return currentAnalysis.value
  }

  return {
    tasks,
    rawIssues,
    currentIssue,
    currentAnalysis,
    loading,
    submitting,
    fetchTasks,
    createTask,
    fetchRawIssues,
    fetchRawIssue,
    translateIssue,
    analyzeIssue,
    fetchAnalysis
  }
})
