import { describe, expect, it } from 'vitest'
import {
  collectionPeriodLabel,
  collectionScopeNoun,
  collectionVolumeLabel,
  groupRawIssues,
  hasChineseTranslation,
  isUnassignedIssue,
} from './collection'

describe('collection period labels', () => {
  it('formats issue-scoped and year-scoped records', () => {
    expect(collectionPeriodLabel(2026, '3')).toBe('2026 年第 3 期')
    expect(collectionPeriodLabel(2025, 'year')).toBe('2025 年')
  })

  it('uses the matching scope noun', () => {
    expect(collectionScopeNoun('3')).toBe('本期')
    expect(collectionScopeNoun('year')).toBe('本年')
  })

  it('uses readable labels for missing volume and issue metadata', () => {
    expect(collectionPeriodLabel(2026, 'unassigned')).toBe('2026 年未分期')
    expect(collectionVolumeLabel('unknown')).toBe('卷号未知')
    expect(collectionVolumeLabel('63')).toBe('第 63 卷')
  })

  it('recognizes internal missing-issue markers defensively', () => {
    expect(isUnassignedIssue('unassigned')).toBe(true)
    expect(isUnassignedIssue('year')).toBe(true)
    expect(isUnassignedIssue('1')).toBe(false)
  })

  it('only enables translated display when translated content exists', () => {
    expect(hasChineseTranslation([{}])).toBe(false)
    expect(hasChineseTranslation([{ title_zh: '论文' }])).toBe(true)
  })

  it('groups issues by journal, year, and volume', () => {
    const grouped = groupRawIssues([
      {
        id: 1,
        journal_name: 'IP&M',
        source_type: 'scopus',
        region: 'foreign',
        year: 2026,
        volume: '63',
        issue: '1',
      },
      {
        id: 2,
        journal_name: 'IP&M',
        source_type: 'scopus',
        region: 'foreign',
        year: 2026,
        volume: '64',
        issue: '1',
      },
      {
        id: 3,
        journal_name: 'IP&M',
        source_type: 'scopus',
        region: 'foreign',
        year: 2026,
        volume: 'unknown',
        issue: 'unassigned',
      },
      {
        id: 4,
        journal_name: 'IP&M',
        source_type: 'scopus',
        region: 'foreign',
        year: 2026,
        volume: '63',
        issue: 'unassigned',
      },
    ])

    expect(grouped).toHaveLength(1)
    expect(grouped[0]!.years[0]!.volumes.map((item) => item.volume)).toEqual([
      '64',
      '63',
      'unknown',
    ])
    expect(grouped[0]!.years[0]!.volumes[0]!.issues[0]!.id).toBe(2)
    expect(grouped[0]!.years[0]!.volumes[1]!.issues.map((item) => item.id)).toEqual([1, 4])
  })
})
