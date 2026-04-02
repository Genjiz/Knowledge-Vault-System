import api from './index'

export function getRawIssues() {
  return api.get('/raw-issues')
}

export function getRawIssue(id) {
  return api.get(`/raw-issues/${id}`)
}

export function getRawIssuePapers(id) {
  return api.get(`/raw-issues/${id}/papers`)
}

export function translateRawIssue(id) {
  return api.post(`/raw-issues/${id}/translate`, {}, { timeout: 180000 })
}

export function analyzeRawIssue(id) {
  return api.post(`/raw-issues/${id}/analyze`, {}, { timeout: 180000 })
}

export function getRawIssueAnalysis(id) {
  return api.get(`/raw-issues/${id}/analysis`)
}
