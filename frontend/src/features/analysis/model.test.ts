import { describe, expect, it } from 'vitest'
import { issueKey, mergeSelectionIds } from './model'

describe('paper analysis selection', () => {
  it('builds stable issue keys for persisted and text-only journals', () => {
    expect(issueKey({ journal_id: 8, journal: '情报学报', year: 2026, issue: '1' })).toBe(
      '情报学报:2026:1',
    )
    expect(
      issueKey({ journal_id: null, journal: 'Imported Journal', year: 2025, issue: 'S1' }),
    ).toBe('Imported Journal:2025:S1')
  })

  it('merges explicit and expanded paper ids without duplicates', () => {
    expect(mergeSelectionIds([3, 1, 3], [2, 1])).toEqual([3, 1, 2])
  })
})
