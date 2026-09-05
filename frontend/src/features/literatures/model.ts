import { z } from 'zod'
import type { Literature } from '@/api/types'

const optionalText = z.string().max(10_000)

export const literatureFormSchema = z.object({
  title: z.string().trim().min(1, '请输入文献标题').max(500),
  authors: z.string().trim().min(1, '请填写至少一名作者').max(5_000),
  journal: optionalText,
  year: z.union([z.number().int().min(1900).max(2100), z.literal('')]),
  volume: optionalText,
  issue: optionalText,
  pages: optionalText,
  doi: optionalText,
  abstract: optionalText,
  keywords: optionalText,
  url: optionalText,
  language: z.enum(['zh', 'en']),
  literature_type: z.enum(['journal', 'conference', 'thesis', 'book']),
  publisher: optionalText,
  status: z.enum(['未读', '摘要浏览', '正在阅读', '已读完', '需要重读']),
  tag_ids: z.array(z.string()),
  folder_ids: z.array(z.string()),
})

export type LiteratureFormValues = z.infer<typeof literatureFormSchema>

export const literatureFormDefaults: LiteratureFormValues = {
  title: '',
  authors: '',
  journal: '',
  year: '',
  volume: '',
  issue: '',
  pages: '',
  doi: '',
  abstract: '',
  keywords: '',
  url: '',
  language: 'en',
  literature_type: 'journal',
  publisher: '',
  status: '未读',
  tag_ids: [],
  folder_ids: [],
}

export function literatureToForm(literature: Literature): LiteratureFormValues {
  return {
    ...literatureFormDefaults,
    title: literature.title || '',
    authors: literature.authors || '',
    journal: literature.journal || '',
    year: literature.year ?? '',
    volume: literature.volume || '',
    issue: literature.issue || '',
    pages: literature.pages || '',
    doi: literature.doi || '',
    abstract: literature.abstract || '',
    keywords: literature.keywords || '',
    url: literature.url || '',
    language: literature.language === 'zh' ? 'zh' : 'en',
    literature_type: ['journal', 'conference', 'thesis', 'book'].includes(
      literature.literature_type || '',
    )
      ? (literature.literature_type as LiteratureFormValues['literature_type'])
      : 'journal',
    status: ['未读', '摘要浏览', '正在阅读', '已读完', '需要重读'].includes(literature.status || '')
      ? (literature.status as LiteratureFormValues['status'])
      : '未读',
    publisher: literature.publisher || '',
    tag_ids: (literature.tags || []).map((tag) => String(tag.id)),
    folder_ids: (literature.folder_ids || []).map(String),
  }
}

export function normalizeLiteraturePayload(
  input: Partial<LiteratureFormValues> & Pick<LiteratureFormValues, 'title' | 'authors'>,
) {
  const values = { ...literatureFormDefaults, ...input }
  const clean = (value: string) => value.trim() || null
  return {
    title: values.title.trim(),
    authors: values.authors.trim(),
    journal: clean(values.journal),
    year: values.year === '' ? null : Number(values.year),
    volume: clean(values.volume),
    issue: clean(values.issue),
    pages: clean(values.pages),
    doi: clean(values.doi),
    abstract: clean(values.abstract),
    keywords: clean(values.keywords),
    url: clean(values.url),
    language: values.language,
    literature_type: values.literature_type,
    publisher: clean(values.publisher),
    status: values.status,
    tag_ids: values.tag_ids.map(Number),
    folder_ids: values.folder_ids.map(Number),
  }
}
