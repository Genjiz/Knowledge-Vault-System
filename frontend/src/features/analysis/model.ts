import type { AnalysisIssueOption } from '@/api/types'

export function issueKey(
  issue: Pick<AnalysisIssueOption, 'journal_id' | 'journal' | 'year' | 'volume' | 'issue'>,
) {
  return `${issue.journal}:${issue.year}:${issue.volume || 'unknown'}:${issue.issue}`
}

export function mergeSelectionIds(explicitIds: number[], expandedIds: number[]) {
  return [...new Set([...explicitIds, ...expandedIds])]
}

export function toggleSelectedPaper(current: number[], paperId: number, checked: boolean) {
  if (checked) return current.includes(paperId) ? current : [...current, paperId]
  return current.filter((value) => value !== paperId)
}

export function analysisPageCount(total: number, perPage: number) {
  return Math.max(1, Math.ceil(total / perPage))
}

export interface AnalysisVolumeGroup {
  volume: string
  issues: AnalysisIssueOption[]
}

export interface AnalysisYearGroup {
  year: number
  volumes: AnalysisVolumeGroup[]
}

export interface AnalysisJournalGroup {
  journal: string
  years: AnalysisYearGroup[]
}

export function groupAnalysisIssues(items: AnalysisIssueOption[]): AnalysisJournalGroup[] {
  const journals = new Map<string, Map<number, Map<string, AnalysisIssueOption[]>>>()
  for (const item of items) {
    const years =
      journals.get(item.journal) || new Map<number, Map<string, AnalysisIssueOption[]>>()
    const volumes = years.get(item.year) || new Map<string, AnalysisIssueOption[]>()
    const volume = item.volume || 'unknown'
    volumes.set(volume, [...(volumes.get(volume) || []), item])
    years.set(item.year, volumes)
    journals.set(item.journal, years)
  }
  return [...journals.entries()]
    .sort(([a], [b]) => a.localeCompare(b, 'zh-CN'))
    .map(([journal, years]) => ({
      journal,
      years: [...years.entries()]
        .sort(([a], [b]) => b - a)
        .map(([year, volumes]) => ({
          year,
          volumes: [...volumes.entries()]
            .sort(([a], [b]) => {
              if (a === 'unknown') return 1
              if (b === 'unknown') return -1
              return b.localeCompare(a, undefined, { numeric: true })
            })
            .map(([volume, issues]) => ({
              volume,
              issues: [...issues].sort((a, b) =>
                a.issue.localeCompare(b.issue, undefined, { numeric: true }),
              ),
            })),
        })),
    }))
}
