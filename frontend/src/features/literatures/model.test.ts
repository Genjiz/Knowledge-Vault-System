import { describe, expect, it } from 'vitest'
import { literatureFormSchema, normalizeLiteraturePayload } from './model'

describe('literature form model', () => {
  it('requires a title and at least one author', () => {
    const result = literatureFormSchema.safeParse({ title: '', authors: '' })
    expect(result.success).toBe(false)
  })

  it('normalizes optional fields and numeric identifiers for the API', () => {
    expect(
      normalizeLiteraturePayload({
        title: '  Test paper  ',
        authors: ' Alice, Bob ',
        year: '',
        tag_ids: ['2', '5'],
        folder_ids: ['9'],
        language: 'en',
        literature_type: 'journal',
        status: '未读',
      }),
    ).toMatchObject({
      title: 'Test paper',
      authors: 'Alice, Bob',
      year: null,
      tag_ids: [2, 5],
      folder_ids: [9],
    })
  })
})
