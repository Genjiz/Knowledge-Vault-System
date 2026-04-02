import api from './index'

export function createCrawlTask(data) {
  return api.post('/crawl-tasks', data, { timeout: 180000 })
}

export function getCrawlTasks() {
  return api.get('/crawl-tasks')
}

export function getCrawlTask(id) {
  return api.get(`/crawl-tasks/${id}`)
}

export function getCrawlTaskLogs(id) {
  return api.get(`/crawl-tasks/${id}/logs`)
}
