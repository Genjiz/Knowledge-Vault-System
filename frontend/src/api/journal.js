import api from './index'

export function getSources() {
  return api.get('/collection/sources')
}

export function getJournals() {
  return api.get('/journals')
}

export function createJournal(data) {
  return api.post('/journals', data)
}

export function updateJournal(id, data) {
  return api.put(`/journals/${id}`, data)
}

export function deleteJournal(id) {
  return api.delete(`/journals/${id}`)
}

export function replaceJournalSources(id, sources) {
  return api.put(`/journals/${id}/sources`, { sources })
}

export function testJournalSource(id, sourceId) {
  return api.post(`/journals/${id}/sources/${sourceId}/test`, {}, { timeout: 30000 })
}

export function probeJournalIssues(id, sourceId, year) {
  return api.get(`/journals/${id}/issues`, {
    params: { source_id: sourceId, year },
    timeout: 30000
  })
}

export function importKnownJournals() {
  return api.post('/journals/import-known')
}
