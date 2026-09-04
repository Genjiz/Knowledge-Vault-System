import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue')
  },
  {
    path: '/literatures',
    name: 'LiteratureList',
    component: () => import('@/views/LiteratureList.vue')
  },
  {
    path: '/literatures/:id',
    name: 'LiteratureDetail',
    component: () => import('@/views/LiteratureDetail.vue')
  },
  {
    path: '/literatures/new',
    name: 'LiteratureNew',
    component: () => import('@/views/LiteratureForm.vue')
  },
  {
    path: '/literatures/:id/edit',
    name: 'LiteratureEdit',
    component: () => import('@/views/LiteratureForm.vue')
  },
  {
    path: '/tags',
    name: 'TagManage',
    component: () => import('@/views/TagManage.vue')
  },
  {
    path: '/folders',
    name: 'FolderManage',
    component: () => import('@/views/FolderManage.vue')
  },
  {
    path: '/statistics',
    name: 'Statistics',
    component: () => import('@/views/Statistics.vue')
  },
  {
    path: '/import',
    name: 'Import',
    component: () => import('@/views/Import.vue')
  },
  {
    path: '/backup',
    name: 'Backup',
    component: () => import('@/views/Backup.vue')
  },
  {
    path: '/crawler/journals',
    name: 'JournalSources',
    component: () => import('@/views/JournalSources.vue')
  },
  {
    path: '/crawler/tasks',
    name: 'CrawlTaskCenter',
    component: () => import('@/views/CrawlTaskCenter.vue')
  },
  {
    path: '/crawler/issues',
    name: 'RawIssueList',
    component: () => import('@/views/RawIssueList.vue')
  },
  {
    path: '/crawler/issues/:id',
    name: 'RawIssueDetail',
    component: () => import('@/views/RawIssueDetail.vue')
  },
  {
    path: '/crawler/issues/:id/analysis',
    name: 'RawIssueAnalysis',
    redirect: to => ({
      name: 'RawIssueDetail',
      params: { id: to.params.id },
      query: { ...to.query, tab: 'analysis' }
    })
  },
  {
    path: '/video-notes',
    name: 'VideoNotesHome',
    component: () => import('@/views/VideoNotesHome.vue')
  },
  {
    path: '/video-notes/tasks',
    name: 'VideoNoteTaskList',
    component: () => import('@/views/VideoNoteTaskList.vue')
  },
  {
    path: '/video-notes/tasks/:id',
    name: 'VideoNoteTaskDetail',
    component: () => import('@/views/VideoNoteTaskDetail.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
