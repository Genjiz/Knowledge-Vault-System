import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import * as videoNoteTaskApi from '@/api/videoNoteTask'

export const useVideoNotesStore = defineStore('video-notes', () => {
  const tasks = ref([])
  const currentTask = ref(null)
  const currentLogs = ref([])
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
      const result = await videoNoteTaskApi.getVideoNoteTasks()
      tasks.value = Array.isArray(result) ? result : []
      return tasks.value
    } finally {
      endLoading()
    }
  }

  async function createTask(data) {
    submitting.value = true
    try {
      const task = await videoNoteTaskApi.createVideoNoteTask(data)
      await fetchTasks()
      return task
    } finally {
      submitting.value = false
    }
  }

  async function fetchTask(id) {
    beginLoading()
    try {
      currentTask.value = await videoNoteTaskApi.getVideoNoteTask(id)
      return currentTask.value
    } finally {
      endLoading()
    }
  }

  async function fetchTaskLogs(id) {
    beginLoading()
    try {
      currentLogs.value = await videoNoteTaskApi.getVideoNoteTaskLogs(id)
      return currentLogs.value
    } finally {
      endLoading()
    }
  }

  return {
    tasks,
    currentTask,
    currentLogs,
    loading,
    submitting,
    fetchTasks,
    createTask,
    fetchTask,
    fetchTaskLogs
  }
})
