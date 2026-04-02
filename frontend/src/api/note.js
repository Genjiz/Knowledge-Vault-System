import api from './index'

export function getNotes(literatureId, type = null) {
  const params = { literature_id: literatureId }
  if (type) params.type = type
  return api.get('/notes', { params })
}

export function getNote(id) {
  return api.get(`/notes/${id}`)
}

export function createNote(data) {
  return api.post('/notes', data)
}

export function updateNote(id, data) {
  return api.put(`/notes/${id}`, data)
}

export function deleteNote(id) {
  return api.delete(`/notes/${id}`)
}
