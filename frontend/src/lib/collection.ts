import type { RawIssue } from '@/api/types'

type TranslatablePaper = { title_zh?: string; abstract_zh?: string }

export function collectionPeriodLabel(year: number, issue?: string | null) {
  if (issue === 'unassigned') return `${year} 年未分期`
  return issue === 'year' || !issue ? `${year} 年` : `${year} 年第 ${issue} 期`
}

export function collectionScopeNoun(issue?: string | null) {
  return issue === 'year' ? '本年' : '本期'
}

export function isUnassignedIssue(issue?: string | null) {
  return ['year', 'unassigned'].includes(
    String(issue || '')
      .trim()
      .toLowerCase(),
  )
}

export function hasChineseTranslation(papers?: TranslatablePaper[]) {
  return Boolean(
    papers?.some((paper) => Boolean(paper.title_zh?.trim()) || Boolean(paper.abstract_zh?.trim())),
  )
}

export function collectionVolumeLabel(volume?: string | null) {
  return !volume || volume === 'unknown' ? '卷号未知' : `第 ${volume} 卷`
}

export interface RawIssueVolumeGroup {
  volume: string
  issues: RawIssue[]
}

export interface RawIssueYearGroup {
  year: number
  volumes: RawIssueVolumeGroup[]
}

export interface RawIssueJournalGroup {
  journal: string
  years: RawIssueYearGroup[]
  issueCount: number
}

function compareVolumeDesc(a: string, b: string) {
  if (a === 'unknown') return 1
  if (b === 'unknown') return -1
  return b.localeCompare(a, undefined, { numeric: true })
}

function compareIssueDesc(a: RawIssue, b: RawIssue) {
  if (a.issue === 'unassigned') return 1
  if (b.issue === 'unassigned') return -1
  return b.issue.localeCompare(a.issue, undefined, { numeric: true })
}

export function groupRawIssues(items: RawIssue[]): RawIssueJournalGroup[] {
  const journals = new Map<string, Map<number, Map<string, RawIssue[]>>>()
  for (const item of items) {
    const years = journals.get(item.journal_name) || new Map<number, Map<string, RawIssue[]>>()
    const volumes = years.get(item.year) || new Map<string, RawIssue[]>()
    const volume = item.volume || 'unknown'
    volumes.set(volume, [...(volumes.get(volume) || []), item])
    years.set(item.year, volumes)
    journals.set(item.journal_name, years)
  }
  return [...journals.entries()]
    .sort(([a], [b]) => a.localeCompare(b, 'zh-CN'))
    .map(([journal, years]) => ({
      journal,
      issueCount: [...years.values()].reduce(
        (total, volumes) =>
          total + [...volumes.values()].reduce((count, issues) => count + issues.length, 0),
        0,
      ),
      years: [...years.entries()]
        .sort(([a], [b]) => b - a)
        .map(([year, volumes]) => ({
          year,
          volumes: [...volumes.entries()]
            .sort(([a], [b]) => compareVolumeDesc(a, b))
            .map(([volume, issues]) => ({
              volume,
              issues: [...issues].sort(compareIssueDesc),
            })),
        })),
    }))
}
