import api from './index'

export function createVideoNoteTask(data) {
  return api.post('/video-note-tasks', data)
}

export function getVideoNoteTasks() {
  return api.get('/video-note-tasks')
}

export function getVideoNoteTask(id) {
  return api.get(`/video-note-tasks/${id}`)
}

export function getVideoNoteTaskLogs(id) {
  return api.get(`/video-note-tasks/${id}/logs`)
}
