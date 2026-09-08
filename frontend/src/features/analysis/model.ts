import type { AnalysisIssueOption } from '@/api/types'

export function issueKey(
  issue: Pick<AnalysisIssueOption, 'journal_id' | 'journal' | 'year' | 'issue'>,
) {
  return `${issue.journal}:${issue.year}:${issue.issue}`
}

export function mergeSelectionIds(explicitIds: number[], expandedIds: number[]) {
  return [...new Set([...explicitIds, ...expandedIds])]
}
