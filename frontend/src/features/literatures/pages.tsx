import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from '@tanstack/react-router'
import { BookOpen, FileText, Pencil, Plus, Trash2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { toast } from 'sonner'
import type { Note } from '@/api/types'
import { folderApi, literatureApi, noteApi, tagApi } from '@/api/resources'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Field,
  Input,
  LoadingState,
  Modal,
  PageHero,
  PanelHeader,
  Select,
  Textarea,
} from '@/components/ui'
import { formatDate } from '@/lib/utils'
import {
  literatureFormDefaults,
  literatureFormSchema,
  literatureToForm,
  normalizeLiteraturePayload,
  type LiteratureFormValues,
} from './model'

const statuses = ['未读', '摘要浏览', '正在阅读', '已读完', '需要重读'] as const
const noteTypes = [
  ['idea', '想法'],
  ['excerpt', '摘录'],
  ['structure', '结构'],
  ['critique', '评价'],
] as const

function statusTone(status?: string): 'neutral' | 'success' | 'warning' | 'danger' | 'info' {
  if (status === '已读完') return 'success'
  if (status === '正在阅读') return 'info'
  if (status === '摘要浏览') return 'warning'
  if (status === '需要重读') return 'danger'
  return 'neutral'
}

interface Filters {
  title: string
  authors: string
  abstract: string
  status: string
  language: string
  has_pdf: string
  year_start: string
  year_end: string
  tag_ids: string[]
}
const emptyFilters: Filters = {
  title: '',
  authors: '',
  abstract: '',
  status: '',
  language: '',
  has_pdf: '',
  year_start: '',
  year_end: '',
  tag_ids: [],
}

export function LiteratureListPage() {
  const client = useQueryClient()
  const [draft, setDraft] = useState<Filters>(emptyFilters)
  const [filters, setFilters] = useState<Filters>(emptyFilters)
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(10)
  const params = useMemo(
    () => ({
      page,
      per_page: perPage,
      title: filters.title || undefined,
      authors: filters.authors || undefined,
      abstract: filters.abstract || undefined,
      status: filters.status || undefined,
      language: filters.language || undefined,
      has_pdf: filters.has_pdf === '' ? undefined : filters.has_pdf === 'true',
      year_start: filters.year_start ? Number(filters.year_start) : undefined,
      year_end: filters.year_end ? Number(filters.year_end) : undefined,
      tag_ids: filters.tag_ids.length ? filters.tag_ids.map(Number) : undefined,
    }),
    [filters, page, perPage],
  )
  const query = useQuery({
    queryKey: ['literatures', params],
    queryFn: () => literatureApi.list(params),
  })
  const tagsQuery = useQuery({ queryKey: ['tags'], queryFn: tagApi.list })
  const remove = useMutation({
    mutationFn: literatureApi.remove,
    onSuccess: async () => {
      toast.success('文献已删除')
      await client.invalidateQueries({ queryKey: ['literatures'] })
    },
    onError: (error) => toast.error(error.message),
  })
  if (query.isLoading || tagsQuery.isLoading) return <LoadingState />
  if (query.error || tagsQuery.error) return <ErrorState error={query.error || tagsQuery.error} />
  const result = query.data!
  const items = result.items || []
  const pages = Math.max(1, Math.ceil(result.total / perPage))
  const update = <K extends keyof Filters>(key: K, value: Filters[K]) =>
    setDraft((current) => ({ ...current, [key]: value }))
  return (
    <div className="page-shell">
      <PageHero
        eyebrow="Library Index · Search"
        title="文献列表"
        description="统一管理正式入库文献，按题录、状态、语言、年份、标签和附件筛选。"
        metrics={[
          { label: 'Page Items', value: items.length },
          { label: 'Total Records', value: result.total },
          { label: 'With PDF', value: items.filter((item) => item.pdf_path).length },
          { label: 'Active Tags', value: filters.tag_ids.length },
        ]}
      />
      <Card>
        <PanelHeader
          title="检索与筛选"
          caption="组合条件缩小范围，筛选只在点击应用后执行。"
          actions={
            <Button asChild>
              <Link to="/literatures/new">
                <Plus size={16} />
                添加文献
              </Link>
            </Button>
          }
        />
        <div className="form-grid">
          <Field className="span-4" label="标题">
            <Input value={draft.title} onChange={(e) => update('title', e.target.value)} />
          </Field>
          <Field className="span-4" label="作者">
            <Input value={draft.authors} onChange={(e) => update('authors', e.target.value)} />
          </Field>
          <Field className="span-4" label="摘要">
            <Input value={draft.abstract} onChange={(e) => update('abstract', e.target.value)} />
          </Field>
          <Field className="span-3" label="状态">
            <Select value={draft.status} onChange={(e) => update('status', e.target.value)}>
              <option value="">全部状态</option>
              {statuses.map((item) => (
                <option key={item}>{item}</option>
              ))}
            </Select>
          </Field>
          <Field className="span-3" label="语言">
            <Select value={draft.language} onChange={(e) => update('language', e.target.value)}>
              <option value="">不限</option>
              <option value="zh">中文</option>
              <option value="en">英文</option>
            </Select>
          </Field>
          <Field className="span-3" label="PDF 附件">
            <Select value={draft.has_pdf} onChange={(e) => update('has_pdf', e.target.value)}>
              <option value="">不限</option>
              <option value="true">有附件</option>
              <option value="false">无附件</option>
            </Select>
          </Field>
          <Field className="span-3" label="标签">
            <Select
              multiple
              value={draft.tag_ids}
              onChange={(e) =>
                update(
                  'tag_ids',
                  Array.from(e.target.selectedOptions, (option) => option.value),
                )
              }
            >
              {(tagsQuery.data || []).map((row) => (
                <option key={row.tag.id} value={row.tag.id}>
                  {row.tag.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field className="span-3" label="起始年份">
            <Input
              type="number"
              min="1900"
              max="2100"
              value={draft.year_start}
              onChange={(e) => update('year_start', e.target.value)}
            />
          </Field>
          <Field className="span-3" label="结束年份">
            <Input
              type="number"
              min="1900"
              max="2100"
              value={draft.year_end}
              onChange={(e) => update('year_end', e.target.value)}
            />
          </Field>
          <div className="span-6 actions items-end justify-end">
            <Button
              variant="secondary"
              onClick={() => {
                setDraft(emptyFilters)
                setFilters(emptyFilters)
                setPage(1)
              }}
            >
              重置
            </Button>
            <Button
              onClick={() => {
                setFilters(draft)
                setPage(1)
              }}
            >
              应用筛选
            </Button>
          </div>
        </div>
      </Card>
      <Card>
        <PanelHeader title="正式文献库" caption={`共 ${result.total} 条记录`} />
        {items.length ? (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>题录</th>
                  <th>年份</th>
                  <th>状态</th>
                  <th>标签</th>
                  <th>附件</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <Link
                        className="record-link"
                        to="/literatures/$id"
                        params={{ id: String(item.id) }}
                      >
                        <strong>{item.title}</strong>
                      </Link>
                      <div className="muted mt-1">
                        {item.authors || '未填写作者'}
                        {item.journal ? ` · ${item.journal}` : ''}
                      </div>
                    </td>
                    <td>{item.year || '-'}</td>
                    <td>
                      <Badge tone={statusTone(item.status)}>{item.status || '未读'}</Badge>
                    </td>
                    <td>
                      <div className="actions">
                        {item.tags?.slice(0, 3).map((tag) => (
                          <span
                            className="tag-dot"
                            style={{ backgroundColor: tag.color }}
                            key={tag.id}
                          >
                            {tag.name}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td>
                      {item.pdf_path ? (
                        <Button
                          variant="ghost"
                          aria-label="打开 PDF"
                          onClick={() => window.open(`/${item.pdf_path}`, '_blank')}
                        >
                          <FileText size={17} />
                        </Button>
                      ) : (
                        '-'
                      )}
                    </td>
                    <td>
                      <div className="actions">
                        <Button variant="ghost" asChild>
                          <Link
                            aria-label="编辑"
                            to="/literatures/$id/edit"
                            params={{ id: String(item.id) }}
                          >
                            <Pencil size={16} />
                          </Link>
                        </Button>
                        <Button
                          variant="ghost"
                          aria-label="删除"
                          disabled={remove.isPending}
                          onClick={() => {
                            if (confirm(`确定删除《${item.title}》吗？`)) remove.mutate(item.id)
                          }}
                        >
                          <Trash2 size={16} />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState>没有符合条件的文献</EmptyState>
        )}
        <div className="pagination">
          <span className="muted">
            第 {page} / {pages} 页
          </span>
          <Select
            aria-label="每页数量"
            value={perPage}
            onChange={(e) => {
              setPerPage(Number(e.target.value))
              setPage(1)
            }}
          >
            <option value="10">10 / 页</option>
            <option value="20">20 / 页</option>
            <option value="50">50 / 页</option>
          </Select>
          <Button
            variant="secondary"
            disabled={page <= 1}
            onClick={() => setPage((value) => value - 1)}
          >
            上一页
          </Button>
          <Button
            variant="secondary"
            disabled={page >= pages}
            onClick={() => setPage((value) => value + 1)}
          >
            下一页
          </Button>
        </div>
      </Card>
    </div>
  )
}

function flattenFolders(
  folders: import('@/api/types').Folder[],
  prefix = '',
): Array<{ id: number; label: string }> {
  return folders.flatMap((folder) => {
    const label = prefix ? `${prefix} / ${folder.name}` : folder.name
    return [{ id: folder.id, label }, ...flattenFolders(folder.children || [], label)]
  })
}

export function LiteratureFormPage() {
  const { id } = useParams({ strict: false })
  const navigate = useNavigate()
  const client = useQueryClient()
  const isEdit = Boolean(id)
  const detail = useQuery({
    queryKey: ['literature', id],
    queryFn: () => literatureApi.get(id!),
    enabled: isEdit,
  })
  const tags = useQuery({ queryKey: ['tags'], queryFn: tagApi.list })
  const folders = useQuery({ queryKey: ['folders'], queryFn: folderApi.list })
  const [pdf, setPdf] = useState<File | null>(null)
  const [newTag, setNewTag] = useState('')
  const form = useForm<LiteratureFormValues>({
    resolver: zodResolver(literatureFormSchema),
    defaultValues: literatureFormDefaults,
  })
  const {
    register,
    handleSubmit,
    reset,
    setValue,
    getValues,
    control,
    formState: { errors, isSubmitting },
  } = form
  const selectedTags = useWatch({ control, name: 'tag_ids' }),
    selectedFolders = useWatch({ control, name: 'folder_ids' })
  useEffect(() => {
    if (detail.data) reset(literatureToForm(detail.data))
  }, [detail.data, reset])
  const createTag = useMutation({
    mutationFn: () => tagApi.create({ name: newTag.trim(), color: '#2563eb' }),
    onSuccess: async (tag) => {
      await client.invalidateQueries({ queryKey: ['tags'] })
      setValue('tag_ids', [...getValues('tag_ids'), String(tag.id)])
      setNewTag('')
      toast.success('标签已创建')
    },
  })
  const submit = handleSubmit(async (values) => {
    try {
      const payload = normalizeLiteraturePayload(values)
      const saved = isEdit
        ? await literatureApi.update(id!, payload)
        : await literatureApi.create(payload)
      if (pdf) await literatureApi.uploadPdf(saved.id, pdf)
      await client.invalidateQueries({ queryKey: ['literatures'] })
      toast.success(isEdit ? '文献已更新' : '文献已创建')
      await navigate({ to: '/literatures/$id', params: { id: String(saved.id) } })
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '保存失败')
    }
  })
  if ((isEdit && detail.isLoading) || tags.isLoading || folders.isLoading) return <LoadingState />
  if (detail.error || tags.error || folders.error)
    return <ErrorState error={detail.error || tags.error || folders.error} />
  return (
    <div className="page-shell">
      <PageHero
        eyebrow="Library Record · Editor"
        title={isEdit ? '编辑文献' : '添加文献'}
        description="维护题录、分类、阅读状态和 PDF 原件。"
        metrics={[
          { label: 'Mode', value: isEdit ? 'Edit' : 'Create' },
          { label: 'Tags', value: selectedTags.length },
          { label: 'Folders', value: selectedFolders.length },
          { label: 'PDF', value: pdf?.name || detail.data?.pdf_path ? 'Ready' : 'None' },
        ]}
      />
      <form onSubmit={(event) => void submit(event)} className="page-shell">
        <Card>
          <PanelHeader title="核心元数据" />
          <div className="form-grid">
            <Field className="span-12" label="文献标题">
              <Input {...register('title')} aria-invalid={Boolean(errors.title)} />
              {errors.title && <span className="field-error">{errors.title.message}</span>}
            </Field>
            <Field className="span-12" label="作者">
              <Input {...register('authors')} placeholder="多个作者以逗号分隔" />
              {errors.authors && <span className="field-error">{errors.authors.message}</span>}
            </Field>
            <Field className="span-6" label="来源期刊 / 会议">
              <Input {...register('journal')} />
            </Field>
            <Field className="span-3" label="发表年份">
              <Input
                type="number"
                min="1900"
                max="2100"
                {...register('year', {
                  setValueAs: (value) => (value === '' ? '' : Number(value)),
                })}
              />
            </Field>
            <Field className="span-3" label="文献类型">
              <Select {...register('literature_type')}>
                <option value="journal">期刊文章</option>
                <option value="conference">会议论文</option>
                <option value="thesis">学位论文</option>
                <option value="book">图书章节</option>
              </Select>
            </Field>
            <Field className="span-6" label="使用语言">
              <Select {...register('language')}>
                <option value="zh">中文</option>
                <option value="en">英文</option>
              </Select>
            </Field>
            <Field className="span-6" label="阅读状态">
              <Select {...register('status')}>
                {statuses.map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </Select>
            </Field>
            <Field className="span-12" label="内容摘要">
              <Textarea {...register('abstract')} rows={6} />
            </Field>
            <Field className="span-12" label="关键词">
              <Input {...register('keywords')} placeholder="多个关键词以逗号分隔" />
            </Field>
          </div>
        </Card>
        <div className="content-grid-2">
          <Card>
            <PanelHeader title="知识标签" />
            <Field label="选择标签">
              <Select
                multiple
                value={selectedTags}
                onChange={(e) =>
                  setValue(
                    'tag_ids',
                    Array.from(e.target.selectedOptions, (o) => o.value),
                  )
                }
              >
                {(tags.data || []).map((row) => (
                  <option value={row.tag.id} key={row.tag.id}>
                    {row.tag.name}
                  </option>
                ))}
              </Select>
            </Field>
            <div className="actions mt-4">
              <Input
                value={newTag}
                placeholder="新标签名称"
                onChange={(e) => setNewTag(e.target.value)}
              />
              <Button
                type="button"
                variant="secondary"
                disabled={!newTag.trim() || createTag.isPending}
                onClick={() => createTag.mutate()}
              >
                创建
              </Button>
            </div>
          </Card>
          <Card>
            <PanelHeader title="文件夹" />
            <Field label="关联文件夹">
              <Select
                multiple
                value={selectedFolders}
                onChange={(e) =>
                  setValue(
                    'folder_ids',
                    Array.from(e.target.selectedOptions, (o) => o.value),
                  )
                }
              >
                {flattenFolders(folders.data || []).map((folder) => (
                  <option key={folder.id} value={folder.id}>
                    {folder.label}
                  </option>
                ))}
              </Select>
            </Field>
          </Card>
        </div>
        <Card>
          <PanelHeader title="附件与高级信息" />
          <div className="form-grid">
            <Field className="span-12" label="PDF 原件">
              <Input
                type="file"
                accept="application/pdf,.pdf"
                onChange={(e) => setPdf(e.target.files?.[0] || null)}
              />
              <span className="field__hint">
                {pdf?.name || detail.data?.pdf_path || '尚未选择附件'}
              </span>
            </Field>
            <Field className="span-6" label="DOI">
              <Input {...register('doi')} />
            </Field>
            <Field className="span-6" label="在线链接">
              <Input type="url" {...register('url')} />
            </Field>
            <Field className="span-3" label="卷">
              <Input {...register('volume')} />
            </Field>
            <Field className="span-3" label="期">
              <Input {...register('issue')} />
            </Field>
            <Field className="span-3" label="页码">
              <Input {...register('pages')} />
            </Field>
            <Field className="span-3" label="出版方 / 学校">
              <Input {...register('publisher')} />
            </Field>
          </div>
        </Card>
        <div className="actions justify-end">
          <Button type="button" variant="secondary" onClick={() => history.back()}>
            取消
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? '保存中...' : isEdit ? '保存更新' : '建立档案'}
          </Button>
        </div>
      </form>
    </div>
  )
}

interface NoteDraft {
  type: string
  title: string
  content: string
  page_number: string
  position_info: string
  excerpt_type: string
  rating: string
  action_required: string
}
const emptyNote = (type = 'idea'): NoteDraft => ({
  type,
  title: '',
  content: '',
  page_number: '',
  position_info: '',
  excerpt_type: '',
  rating: '0',
  action_required: '',
})

export function LiteratureDetailPage() {
  const id = useParams({ strict: false }).id || ''
  const navigate = useNavigate(),
    client = useQueryClient()
  const detail = useQuery({
    queryKey: ['literature', id],
    queryFn: () => literatureApi.get(id),
    enabled: Boolean(id),
  })
  const notes = useQuery({
    queryKey: ['notes', id],
    queryFn: () => noteApi.list(id),
    enabled: Boolean(id),
  })
  const [noteType, setNoteType] = useState('all'),
    [noteOpen, setNoteOpen] = useState(false),
    [editing, setEditing] = useState<Note | null>(null),
    [draft, setDraft] = useState<NoteDraft>(emptyNote())
  const refresh = async () => {
    await Promise.all([
      client.invalidateQueries({ queryKey: ['literature', id] }),
      client.invalidateQueries({ queryKey: ['notes', id] }),
      client.invalidateQueries({ queryKey: ['literatures'] }),
    ])
  }
  const status = useMutation({
    mutationFn: (value: string) => literatureApi.update(id, { status: value }),
    onSuccess: async () => {
      toast.success('阅读状态已保存')
      await refresh()
    },
  })
  const saveNote = useMutation({
    mutationFn: () => {
      const payload = {
        literature_id: Number(id),
        ...draft,
        page_number: draft.page_number ? Number(draft.page_number) : null,
        rating: Number(draft.rating) || 0,
      }
      return editing ? noteApi.update(editing.id, payload) : noteApi.create(payload)
    },
    onSuccess: async () => {
      toast.success(editing ? '笔记已更新' : '笔记已创建')
      setNoteOpen(false)
      await refresh()
    },
    onError: (error) => toast.error(error.message),
  })
  const deleteNote = useMutation({
    mutationFn: noteApi.remove,
    onSuccess: async () => {
      toast.success('笔记已删除')
      await refresh()
    },
  })
  const deleteLiterature = useMutation({
    mutationFn: () => literatureApi.remove(id),
    onSuccess: async () => {
      toast.success('文献已删除')
      await navigate({ to: '/literatures' })
    },
  })
  const uploadPdf = useMutation({
    mutationFn: (file: File) => literatureApi.uploadPdf(id, file),
    onSuccess: async () => {
      toast.success('PDF 已上传')
      await refresh()
    },
  })
  const deletePdf = useMutation({
    mutationFn: () => literatureApi.deletePdf(id),
    onSuccess: async () => {
      toast.success('PDF 已移除')
      await refresh()
    },
  })
  if (detail.isLoading || notes.isLoading) return <LoadingState />
  if (detail.error || notes.error || !detail.data)
    return <ErrorState error={detail.error || notes.error} />
  const literature = detail.data,
    filtered = (notes.data || []).filter((note) => noteType === 'all' || note.type === noteType)
  const showNote = (type: string, note?: Note) => {
    setEditing(note || null)
    setDraft(
      note
        ? {
            type: note.type,
            title: note.title || '',
            content: note.content,
            page_number: note.page_number ? String(note.page_number) : '',
            position_info: note.position_info || '',
            excerpt_type: note.excerpt_type || '',
            rating: String(note.rating || 0),
            action_required: note.action_required || '',
          }
        : emptyNote(type),
    )
    setNoteOpen(true)
  }
  return (
    <div className="page-shell">
      <PageHero
        eyebrow="Library Record · Detail"
        title={literature.title}
        description={`${literature.authors || '未填写作者'}${literature.journal ? ` · ${literature.journal}` : ''}${literature.year ? ` · ${literature.year}` : ''}`}
        metrics={[
          { label: 'Status', value: literature.status || '未读' },
          { label: 'Tags', value: literature.tags?.length || 0 },
          { label: 'Notes', value: notes.data?.length || 0 },
          { label: 'PDF', value: literature.pdf_path ? 'Yes' : 'No' },
        ]}
      />
      <div className="actions justify-between">
        <Button variant="secondary" asChild>
          <Link to="/literatures">返回文献库</Link>
        </Button>
        <div className="actions">
          <Button variant="secondary" asChild>
            <Link to="/literatures/$id/edit" params={{ id }}>
              <Pencil size={16} />
              编辑
            </Link>
          </Button>
          <Button
            variant="danger"
            disabled={deleteLiterature.isPending}
            onClick={() => {
              if (confirm('这篇文献及其笔记将被彻底删除，确定继续吗？')) deleteLiterature.mutate()
            }}
          >
            <Trash2 size={16} />
            删除
          </Button>
        </div>
      </div>
      <Card>
        <div className="detail-grid">
          <div>
            <PanelHeader title="摘要" />
            <p className="prose whitespace-pre-wrap">{literature.abstract || '暂无摘要'}</p>
            {literature.keywords && (
              <>
                <h3>关键词</h3>
                <p className="muted">{literature.keywords}</p>
              </>
            )}
          </div>
          <div className="metadata-list">
            <div>
              <span>阅读状态</span>
              <Select
                value={literature.status || '未读'}
                disabled={status.isPending}
                onChange={(e) => status.mutate(e.target.value)}
              >
                {statuses.map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </Select>
            </div>
            {[
              ['DOI', literature.doi],
              ['类型', literature.literature_type],
              ['语言', literature.language === 'zh' ? '中文' : '英文'],
              ['卷 / 期', [literature.volume, literature.issue].filter(Boolean).join(' / ')],
              ['页码', literature.pages],
              ['出版方', literature.publisher],
            ]
              .filter(([, value]) => value)
              .map(([label, value]) => (
                <div key={label}>
                  <span>{label}</span>
                  <strong>{value}</strong>
                </div>
              ))}
            {literature.url && (
              <a href={literature.url} target="_blank" rel="noreferrer">
                打开来源页面
              </a>
            )}
          </div>
        </div>
      </Card>
      <Card>
        <PanelHeader
          title="PDF 原件"
          actions={
            literature.pdf_path ? (
              <div className="actions">
                <Button onClick={() => window.open(`/${literature.pdf_path}`, '_blank')}>
                  <BookOpen size={16} />
                  阅读 PDF
                </Button>
                <Button
                  variant="danger"
                  onClick={() => {
                    if (confirm('确定移除 PDF 附件吗？')) deletePdf.mutate()
                  }}
                >
                  移除
                </Button>
              </div>
            ) : undefined
          }
        />
        {!literature.pdf_path && (
          <Field label="上传 PDF">
            <Input
              type="file"
              accept="application/pdf,.pdf"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) uploadPdf.mutate(file)
              }}
            />
          </Field>
        )}
      </Card>
      <Card>
        <PanelHeader
          title="阅读笔记"
          caption="记录想法、摘录、结构梳理和批判评价。"
          actions={
            <Button onClick={() => showNote('idea')}>
              <Plus size={16} />
              记录笔记
            </Button>
          }
        />
        <div className="tabs">
          {[['all', '全部'], ...noteTypes].map(([value, label]) => (
            <button
              type="button"
              className={noteType === value ? 'tab active' : 'tab'}
              key={value}
              onClick={() => setNoteType(value)}
            >
              {label}
            </button>
          ))}
        </div>
        {filtered.length ? (
          <div className="note-list">
            {filtered.map((note) => (
              <article className={`note-card note-card--${note.type}`} key={note.id}>
                <div className="actions justify-between">
                  <div className="actions">
                    <Badge
                      tone={
                        note.type === 'critique'
                          ? 'danger'
                          : note.type === 'excerpt'
                            ? 'success'
                            : note.type === 'structure'
                              ? 'warning'
                              : 'info'
                      }
                    >
                      {noteTypes.find(([value]) => value === note.type)?.[1] || note.type}
                    </Badge>
                    {note.page_number && <span className="muted">P{note.page_number}</span>}
                    {note.rating ? <span className="muted">评分 {note.rating}/5</span> : null}
                  </div>
                  <span className="muted">{formatDate(note.created_at)}</span>
                </div>
                {note.title && <h3>{note.title}</h3>}
                <p className="whitespace-pre-wrap">{note.content}</p>
                {note.action_required && (
                  <div className="alert alert--warning">下一步行动：{note.action_required}</div>
                )}
                <div className="actions justify-end">
                  <Button variant="ghost" onClick={() => showNote(note.type, note)}>
                    编辑
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => {
                      if (confirm('确定删除这条笔记吗？')) deleteNote.mutate(note.id)
                    }}
                  >
                    删除
                  </Button>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState>当前筛选下暂无笔记</EmptyState>
        )}
      </Card>
      <Modal
        open={noteOpen}
        onOpenChange={setNoteOpen}
        title={editing ? '编辑笔记' : '记录笔记'}
        wide
        footer={
          <>
            <Button variant="secondary" onClick={() => setNoteOpen(false)}>
              取消
            </Button>
            <Button
              disabled={!draft.content.trim() || saveNote.isPending}
              onClick={() => saveNote.mutate()}
            >
              保存
            </Button>
          </>
        }
      >
        <div className="form-grid">
          <Field className="span-4" label="类型">
            <Select
              value={draft.type}
              onChange={(e) => setDraft((v) => ({ ...v, type: e.target.value }))}
            >
              {noteTypes.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
          </Field>
          <Field className="span-8" label="标题">
            <Input
              value={draft.title}
              onChange={(e) => setDraft((v) => ({ ...v, title: e.target.value }))}
            />
          </Field>
          <Field className="span-3" label="页码">
            <Input
              type="number"
              min="1"
              value={draft.page_number}
              onChange={(e) => setDraft((v) => ({ ...v, page_number: e.target.value }))}
            />
          </Field>
          <Field className="span-9" label="位置说明">
            <Input
              value={draft.position_info}
              onChange={(e) => setDraft((v) => ({ ...v, position_info: e.target.value }))}
            />
          </Field>
          {draft.type === 'excerpt' && (
            <Field className="span-6" label="摘录类型">
              <Select
                value={draft.excerpt_type}
                onChange={(e) => setDraft((v) => ({ ...v, excerpt_type: e.target.value }))}
              >
                <option value="">请选择</option>
                {['核心观点', '研究方法', '数据结果', '重要结论', '关键定义', '其他'].map(
                  (item) => (
                    <option key={item}>{item}</option>
                  ),
                )}
              </Select>
            </Field>
          )}
          {draft.type === 'critique' && (
            <Field className="span-6" label="评分">
              <Select
                value={draft.rating}
                onChange={(e) => setDraft((v) => ({ ...v, rating: e.target.value }))}
              >
                {[0, 1, 2, 3, 4, 5].map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </Select>
            </Field>
          )}
          <Field className="span-12" label="内容">
            <Textarea
              rows={8}
              value={draft.content}
              onChange={(e) => setDraft((v) => ({ ...v, content: e.target.value }))}
            />
          </Field>
          {draft.type === 'idea' && (
            <Field className="span-12" label="行动项">
              <Input
                value={draft.action_required}
                onChange={(e) => setDraft((v) => ({ ...v, action_required: e.target.value }))}
              />
            </Field>
          )}
        </div>
      </Modal>
    </div>
  )
}
