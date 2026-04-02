import api from './index'

export function getLiteratures(params) {
  return api.get('/literatures', { params })
}

export function getLiterature(id) {
  return api.get(`/literatures/${id}`)
}

export function createLiterature(data) {
  return api.post('/literatures', data)
}

export function updateLiterature(id, data) {
  return api.put(`/literatures/${id}`, data)
}

export function deleteLiterature(id) {
  return api.delete(`/literatures/${id}`)
}

export function uploadPdf(id, file) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post(`/literatures/${id}/pdf`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function deletePdf(id) {
  return api.delete(`/literatures/${id}/pdf`)
}

export function searchLiteratures(params) {
  return api.get('/literatures/search', { params })
}

export function getStatistics() {
  return api.get('/literatures/statistics')
}
