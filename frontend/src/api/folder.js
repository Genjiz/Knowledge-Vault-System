import api from './index'

export function getFolders() {
  return api.get('/folders')
}

export function getRootFolders() {
  return api.get('/folders/root')
}

export function getFolder(id) {
  return api.get(`/folders/${id}`)
}

export function getChildren(id) {
  return api.get(`/folders/${id}/children`)
}

export function createFolder(data) {
  return api.post('/folders', data)
}

export function updateFolder(id, data) {
  return api.put(`/folders/${id}`, data)
}

export function deleteFolder(id) {
  return api.delete(`/folders/${id}`)
}
