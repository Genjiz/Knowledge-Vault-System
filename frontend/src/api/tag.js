import api from './index'

export function getTags() {
  return api.get('/tags')
}

export function getTag(id) {
  return api.get(`/tags/${id}`)
}

export function createTag(data) {
  return api.post('/tags', data)
}

export function updateTag(id, data) {
  return api.put(`/tags/${id}`, data)
}

export function deleteTag(id) {
  return api.delete(`/tags/${id}`)
}
