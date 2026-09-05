import { describe, expect, it } from 'vitest'
import { parseEndnote } from './endnote'

describe('parseEndnote', () => {
  it('parses repeated authors and core metadata', () => {
    const records = parseEndnote(
      '%0 Journal Article\n%T Test Paper\n%A Alice\n%A Bob\n%J Demo\n%D 2026\n%K AI\n',
    )
    expect(records).toEqual([
      expect.objectContaining({
        title: 'Test Paper',
        authors: 'Alice, Bob',
        journal: 'Demo',
        year: 2026,
        keywords: 'AI',
      }),
    ])
  })

  it('drops records without a title', () => {
    expect(parseEndnote('%0 Journal Article\n%A Alice\n')).toEqual([])
  })
})
