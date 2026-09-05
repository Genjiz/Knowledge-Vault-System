import { api } from './client'
import type {
  CrawlTask,
  CrawlTaskResult,
  Folder,
  ImportKnownResult,
  IssueAnalysis,
  Journal,
  Literature,
  LiteraturePage,
  Note,
  ProbeIssuesResult,
  RawIssue,
  RawIssuePage,
  SourceMeta,
  SourceTestResult,
  Statistics,
  TagRecord,
  VideoLog,
  VideoTask,
} from './types'

const data = async <T>(request: Promise<{ data: unknown }>) => (await request).data as T

export const literatureApi = {
  list: (params?: Record<string, unknown>) =>
    data<LiteraturePage>(api.get('/literatures', { params })),
  get: (id: string | number) => data<Literature>(api.get(`/literatures/${id}`)),
  create: (payload: Record<string, unknown>) => data<Literature>(api.post('/literatures', payload)),
  update: (id: string | number, payload: Record<string, unknown>) =>
    data<Literature>(api.put(`/literatures/${id}`, payload)),
  remove: (id: string | number) => data<void>(api.delete(`/literatures/${id}`)),
  statistics: () => data<Statistics>(api.get('/literatures/statistics')),
  uploadPdf: (id: string | number, file: File) => {
    const body = new FormData()
    body.append('file', file)
    return data(api.post(`/literatures/${id}/pdf`, body))
  },
  deletePdf: (id: string | number) => data(api.delete(`/literatures/${id}/pdf`)),
}
export const tagApi = {
  list: () => data<TagRecord[]>(api.get('/tags')),
  create: (p: object) => data<TagRecord['tag']>(api.post('/tags', p)),
  update: (id: number, p: object) => data<TagRecord['tag']>(api.put(`/tags/${id}`, p)),
  remove: (id: number) => data<void>(api.delete(`/tags/${id}`)),
}
export const folderApi = {
  list: () => data<Folder[]>(api.get('/folders')),
  create: (p: object) => data<Folder>(api.post('/folders', p)),
  update: (id: number, p: object) => data<Folder>(api.put(`/folders/${id}`, p)),
  remove: (id: number) => data<void>(api.delete(`/folders/${id}`)),
}
export const noteApi = {
  list: (literatureId: string | number) =>
    data<Note[]>(api.get('/notes', { params: { literature_id: literatureId } })),
  create: (p: object) => data<Note>(api.post('/notes', p)),
  update: (id: number, p: object) => data<Note>(api.put(`/notes/${id}`, p)),
  remove: (id: number) => data<void>(api.delete(`/notes/${id}`)),
}
export const journalApi = {
  sources: () => data<SourceMeta[]>(api.get('/collection/sources')),
  list: () => data<Journal[]>(api.get('/journals')),
  create: (p: object) => data<Journal>(api.post('/journals', p)),
  update: (id: number, p: object) => data<Journal>(api.put(`/journals/${id}`, p)),
  remove: (id: number) => data(api.delete(`/journals/${id}`)),
  replaceSources: (id: number, sources: object[]) =>
    data<Journal>(api.put(`/journals/${id}/sources`, { sources })),
  testSource: (id: number, sourceId: string) =>
    data<SourceTestResult>(
      api.post(`/journals/${id}/sources/${sourceId}/test`, {}, { timeout: 30_000 }),
    ),
  probeIssues: (id: number, sourceId: string, year: number) =>
    data<ProbeIssuesResult>(
      api.get(`/journals/${id}/issues`, { params: { source_id: sourceId, year }, timeout: 30_000 }),
    ),
  importKnown: () => data<ImportKnownResult>(api.post('/journals/import-known')),
}
export const crawlApi = {
  tasks: () => data<CrawlTask[]>(api.get('/crawl-tasks', { params: { _t: Date.now() } })),
  create: (p: object) => data<CrawlTaskResult>(api.post('/crawl-tasks', p, { timeout: 180_000 })),
  issues: () => data<RawIssuePage>(api.get('/raw-issues', { params: { _t: Date.now() } })),
  issue: (id: string | number) => data<RawIssue>(api.get(`/raw-issues/${id}`)),
  translate: (id: string | number) =>
    data<RawIssue>(api.post(`/raw-issues/${id}/translate`, {}, { timeout: 180_000 })),
  analyze: (id: string | number) =>
    data<IssueAnalysis>(api.post(`/raw-issues/${id}/analyze`, {}, { timeout: 180_000 })),
  analysis: (id: string | number) =>
    data<IssueAnalysis | null>(api.get(`/raw-issues/${id}/analysis`)),
}
export const videoApi = {
  list: () => data<VideoTask[]>(api.get('/video-note-tasks')),
  get: (id: string | number) => data<VideoTask>(api.get(`/video-note-tasks/${id}`)),
  logs: (id: string | number) => data<VideoLog[]>(api.get(`/video-note-tasks/${id}/logs`)),
  create: (p: object) => data<VideoTask>(api.post('/video-note-tasks', p)),
}
