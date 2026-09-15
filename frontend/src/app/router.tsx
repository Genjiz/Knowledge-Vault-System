import { createRootRoute, createRoute, createRouter } from '@tanstack/react-router'
import type { ComponentType } from 'react'
import { AppShell } from './AppShell'
import {
  BackupPage,
  CollectionSettingsPage,
  CrawlTaskPage,
  DashboardPage,
  FolderPage,
  ImportPage,
  JournalSourcesPage,
  LiteratureDetailPage,
  LiteratureFormPage,
  LiteratureListPage,
  ModelSettingsPage,
  PaperAnalysisPage,
  RawIssueDetailPage,
  RawIssueListPage,
  StatisticsPage,
  TagPage,
  VideoNoteDetailPage,
  VideoNoteHomePage,
  VideoNoteListPage,
} from './route-components'

const rootRoute = createRootRoute({ component: AppShell })
const route = <TPath extends string>(path: TPath, Component: ComponentType) =>
  createRoute({ getParentRoute: () => rootRoute, path, component: () => <Component /> })
const routes = [
  route('/', DashboardPage),
  route('/literatures', LiteratureListPage),
  route('/literatures/new', LiteratureFormPage),
  route('/literatures/$id', LiteratureDetailPage),
  route('/literatures/$id/edit', LiteratureFormPage),
  route('/paper-analysis', PaperAnalysisPage),
  route('/tags', TagPage),
  route('/folders', FolderPage),
  route('/statistics', StatisticsPage),
  route('/import', ImportPage),
  route('/backup', BackupPage),
  route('/crawler/journals', JournalSourcesPage),
  route('/crawler/tasks', CrawlTaskPage),
  route('/crawler/issues', RawIssueListPage),
  route('/crawler/issues/$id', RawIssueDetailPage),
  route('/crawler/settings', CollectionSettingsPage),
  route('/video-notes', VideoNoteHomePage),
  route('/video-notes/tasks', VideoNoteListPage),
  route('/video-notes/tasks/$id', VideoNoteDetailPage),
  route('/settings/models', ModelSettingsPage),
]
const routeTree = rootRoute.addChildren(routes)
export const router = createRouter({ routeTree, defaultPreload: 'intent' })
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
