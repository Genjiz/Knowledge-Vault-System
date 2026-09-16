import { lazy } from 'react'

export const DashboardPage = lazy(() =>
  import('@/features/dashboard/pages').then((module) => ({ default: module.DashboardPage })),
)
export const StatisticsPage = lazy(() =>
  import('@/features/dashboard/pages').then((module) => ({ default: module.StatisticsPage })),
)
export const FolderPage = lazy(() =>
  import('@/features/organize/pages').then((module) => ({ default: module.FolderPage })),
)
export const TagPage = lazy(() =>
  import('@/features/organize/pages').then((module) => ({ default: module.TagPage })),
)
export const BackupPage = lazy(() =>
  import('@/features/utilities/pages').then((module) => ({ default: module.BackupPage })),
)
export const ImportPage = lazy(() =>
  import('@/features/utilities/pages').then((module) => ({ default: module.ImportPage })),
)
export const LiteratureDetailPage = lazy(() =>
  import('@/features/literatures/pages').then((module) => ({
    default: module.LiteratureDetailPage,
  })),
)
export const LiteratureFormPage = lazy(() =>
  import('@/features/literatures/pages').then((module) => ({ default: module.LiteratureFormPage })),
)
export const LiteratureListPage = lazy(() =>
  import('@/features/literatures/pages').then((module) => ({ default: module.LiteratureListPage })),
)
export const PaperAnalysisPage = lazy(() =>
  import('@/features/analysis/pages').then((module) => ({ default: module.PaperAnalysisPage })),
)
export const ModelSettingsPage = lazy(() =>
  import('@/features/settings/pages').then((module) => ({ default: module.ModelSettingsPage })),
)
export const CollectionSettingsPage = lazy(() =>
  import('@/features/settings/collection').then((module) => ({
    default: module.CollectionSettingsPage,
  })),
)
export const CrawlTaskPage = lazy(() =>
  import('@/features/collection/pages').then((module) => ({ default: module.CrawlTaskPage })),
)
export const JournalSourcesPage = lazy(() =>
  import('@/features/collection/pages').then((module) => ({ default: module.JournalSourcesPage })),
)
export const RawIssueDetailPage = lazy(() =>
  import('@/features/collection/pages').then((module) => ({ default: module.RawIssueDetailPage })),
)
export const RawIssueListPage = lazy(() =>
  import('@/features/collection/pages').then((module) => ({ default: module.RawIssueListPage })),
)
