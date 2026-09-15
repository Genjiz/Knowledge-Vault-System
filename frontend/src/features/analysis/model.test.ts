import { describe, expect, it } from 'vitest'
import {
  analysisPageCount,
  groupAnalysisIssues,
  issueKey,
  mergeSelectionIds,
  toggleSelectedPaper,
} from './model'

describe('paper analysis selection', () => {
  it('builds stable issue keys for persisted and text-only journals', () => {
    expect(
      issueKey({ journal_id: 8, journal: '情报学报', year: 2026, volume: '45', issue: '1' }),
    ).toBe('情报学报:2026:45:1')
    expect(
      issueKey({
        journal_id: null,
        journal: 'Imported Journal',
        year: 2025,
        volume: 'unknown',
        issue: 'S1',
      }),
    ).toBe('Imported Journal:2025:unknown:S1')
  })

  it('merges explicit and expanded paper ids without duplicates', () => {
    expect(mergeSelectionIds([3, 1, 3], [2, 1])).toEqual([3, 1, 2])
  })

  it('groups issue options by journal, year, and volume', () => {
    const groups = groupAnalysisIssues([
      { journal: 'IP&M', year: 2026, volume: '63', issue: '1', paper_count: 10 },
      { journal: 'IP&M', year: 2026, volume: '64', issue: '1', paper_count: 1 },
      { journal: '情报学报', year: 2026, volume: '45', issue: '1', paper_count: 20 },
    ])

    expect(groups.map((item) => item.journal).sort()).toEqual(['IP&M', '情报学报'].sort())
    const ipm = groups.find((item) => item.journal === 'IP&M')
    expect(ipm).toBeDefined()
    expect(ipm!.years[0]!.volumes.map((item) => item.volume)).toEqual(['64', '63'])
  })

  it('keeps selections from other pages while toggling the current paper', () => {
    expect(toggleSelectedPaper([1, 2], 3, true)).toEqual([1, 2, 3])
    expect(toggleSelectedPaper([1, 2, 3], 2, false)).toEqual([1, 3])
    expect(toggleSelectedPaper([1, 2], 2, true)).toEqual([1, 2])
  })

  it('calculates a stable page count for empty and partial result sets', () => {
    expect(analysisPageCount(0, 30)).toBe(1)
    expect(analysisPageCount(31, 30)).toBe(2)
  })
})
