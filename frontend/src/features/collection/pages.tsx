import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from '@tanstack/react-router'
import { BrainCircuit, Download, Play, RefreshCw, Settings2, Trash2 } from 'lucide-react'
import { useMemo, useState } from 'react'
import { toast } from 'sonner'
import type { FullTextTask, Journal, ProbeIssue, RawIssue, SourceMeta } from '@/api/types'
import { crawlApi, fulltextApi, journalApi } from '@/api/resources'
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
} from '@/components/ui'
import { formatDate } from '@/lib/utils'

type SourceRow = SourceMeta & {
  enabled: boolean
  is_default: boolean
  config: Record<string, string>
  testStatus?: string
  testMessage?: string
}
interface JournalDraft {
  id?: number
  name: string
  issn: string
  publisher: string
  region: string
  rows: SourceRow[]
}

function regionLabel(region?: string) {
  return region === 'domestic' ? '国内' : region === 'foreign' ? '国外' : '未设置'
}
function statusTone(status?: string): 'neutral' | 'success' | 'warning' | 'danger' | 'info' {
  if (['completed', 'ok'].includes(status || '')) return 'success'
  if (['failed', 'error'].includes(status || '')) return 'danger'
  if (['running', 'pending', 'partial'].includes(status || '')) return 'warning'
  return 'neutral'
}
function isFullTextRunning(task?: FullTextTask) {
  return task?.status === 'pending' || task?.status === 'running'
}
function fullTextStatusLabel(status?: string) {
  if (status === 'completed') return '已完成'
  if (status === 'partial') return '部分完成'
  if (status === 'failed') return '失败'
  if (status === 'running') return '下载中'
  return '等待开始'
}
function FullTextTaskSummary({ task }: { task?: FullTextTask }) {
  if (!task) return null
  const failures = task.items.filter((item) => item.status === 'failed')
  return (
    <div className={`alert mt-4 ${task.failed_count ? 'alert--warning' : ''}`}>
      <div className="actions justify-between">
        <strong>全文任务：{fullTextStatusLabel(task.status)}</strong>
        <Badge tone={statusTone(task.status)}>{task.progress_message || task.status}</Badge>
      </div>
      <p className="muted mt-2">
        共 {task.total_count} 篇 · 成功 {task.succeeded_count} · 失败 {task.failed_count} · 跳过{' '}
        {task.skipped_count}
      </p>
      {failures.slice(0, 5).map((item) => (
        <p className="muted mt-2" key={item.id}>
          {item.literature_title || `文献 #${item.literature_id || '-'}`}：
          {item.error_message || '下载失败'}
        </p>
      ))}
    </div>
  )
}
function sourceRows(sources: SourceMeta[], journal?: Journal, region = '') {
  const configured = new Map((journal?.sources || []).map((item) => [item.source_id, item]))
  return sources
    .filter((source) => source.region === region)
    .map((source) => {
      const item = configured.get(source.source_id)
      const config = (() => {
        try {
          return item?.config_json ? (JSON.parse(item.config_json) as Record<string, string>) : {}
        } catch {
          return {}
        }
      })()
      return {
        ...source,
        enabled: Boolean(item?.enabled),
        is_default: Boolean(item?.is_default),
        config,
        testStatus: item?.last_check_status,
        testMessage: item?.last_check_message,
      }
    })
}

export function JournalSourcesPage() {
  const client = useQueryClient(),
    sources = useQuery({ queryKey: ['collection-sources'], queryFn: journalApi.sources }),
    journals = useQuery({ queryKey: ['journals'], queryFn: journalApi.list })
  const [open, setOpen] = useState(false),
    [draft, setDraft] = useState<JournalDraft>({
      name: '',
      issn: '',
      publisher: '',
      region: '',
      rows: [],
    })
  const rebuild = (region: string, journal?: Journal) =>
    setDraft((current) => ({
      ...current,
      region,
      rows: sourceRows(sources.data || [], journal, region),
    }))
  const show = (journal?: Journal) => {
    const region = journal?.region || 'domestic'
    setDraft({
      id: journal?.id,
      name: journal?.name || '',
      issn: journal?.issn || '',
      publisher: journal?.publisher || '',
      region,
      rows: sourceRows(sources.data || [], journal, region),
    })
    setOpen(true)
  }
  const save = useMutation({
    mutationFn: async () => {
      const missing = draft.rows.find(
        (row) =>
          row.enabled &&
          row.config_fields.some(
            (field) => field.required && !String(row.config[field.key] || '').trim(),
          ),
      )
      if (missing) throw new Error(`${missing.display_name} 存在未填写的必填配置`)
      const payload = {
        name: draft.name.trim(),
        issn: draft.issn || null,
        publisher: draft.publisher || null,
        region: draft.region,
      }
      const journal = draft.id
        ? await journalApi.update(draft.id, payload)
        : await journalApi.create(payload)
      await journalApi.replaceSources(
        journal.id,
        draft.rows.map((row) => ({
          source_id: row.source_id,
          enabled: row.enabled,
          is_default: row.enabled && row.is_default,
          config: row.config,
        })),
      )
      return journal
    },
    onSuccess: async () => {
      toast.success('期刊配置已保存')
      setOpen(false)
      await client.invalidateQueries({ queryKey: ['journals'] })
    },
    onError: (error) => toast.error(error.message),
  })
  const remove = useMutation({
    mutationFn: journalApi.remove,
    onSuccess: async () => {
      toast.success('期刊已删除')
      await client.invalidateQueries({ queryKey: ['journals'] })
    },
  })
  const testSource = useMutation({
    mutationFn: ({ id, sourceId }: { id: number; sourceId: string }) =>
      journalApi.testSource(id, sourceId),
    onSuccess: (result, variables) =>
      setDraft((current) => ({
        ...current,
        rows: current.rows.map((row) =>
          row.source_id === variables.sourceId
            ? {
                ...row,
                testStatus: result.last_check_status,
                testMessage: result.last_check_message,
              }
            : row,
        ),
      })),
    onError: (error) => toast.error(error.message),
  })
  if (sources.isLoading || journals.isLoading) return <LoadingState />
  if (sources.error || journals.error) return <ErrorState error={sources.error || journals.error} />
  const list = journals.data || [],
    enabled = list.reduce(
      (sum, journal) => sum + journal.sources.filter((source) => source.enabled).length,
      0,
    ),
    issues = list.reduce((sum, journal) => sum + (journal.stats?.issue_count || 0), 0),
    untested = list.reduce(
      (sum, journal) =>
        sum +
        journal.sources.filter((source) => source.enabled && !source.last_check_status).length,
      0,
    )
  const journalId = draft.id
  const updateRow = (sourceId: string, change: Partial<SourceRow>) =>
    setDraft((current) => ({
      ...current,
      rows: current.rows.map((row) => (row.source_id === sourceId ? { ...row, ...change } : row)),
    }))
  return (
    <div className="page-shell">
      <PageHero
        eyebrow="Collection Setup · Sources"
        title="期刊与采集源"
        description="维护支持批量采集的期刊，为每个期刊配置可用源并测试连接。"
        metrics={[
          { label: 'Journals', value: list.length },
          { label: 'Enabled Sources', value: enabled },
          { label: 'Collected Issues', value: issues },
          { label: 'Untested', value: untested },
        ]}
      />
      <Card>
        <PanelHeader
          title="期刊清单"
          caption="默认源会在采集任务台自动选中。"
          actions={<Button onClick={() => show()}>新增期刊</Button>}
        />
        {list.length ? (
          <div className="cards-grid">
            {list.map((journal) => (
              <article className="item-card collection-card" key={journal.id}>
                <div className="actions justify-between">
                  <h3>{journal.name}</h3>
                  <Badge tone={journal.region === 'domestic' ? 'danger' : 'info'}>
                    {regionLabel(journal.region)}
                  </Badge>
                </div>
                <p className="muted">
                  {journal.issn || '未填写 ISSN'}
                  {journal.publisher ? ` · ${journal.publisher}` : ''}
                </p>
                <div className="actions">
                  {journal.sources
                    .filter((source) => source.enabled)
                    .map((source) => (
                      <Badge
                        tone={source.is_default ? 'success' : 'warning'}
                        key={source.source_id}
                      >
                        {sources.data?.find((meta) => meta.source_id === source.source_id)
                          ?.display_name || source.source_id}
                        {source.is_default ? ' · 默认' : ''}
                      </Badge>
                    ))}
                </div>
                <p className="muted">
                  已采集 {journal.stats?.issue_count || 0} 期
                  {journal.stats?.last_collected_at
                    ? ` · 最近 ${formatDate(journal.stats.last_collected_at)}`
                    : ''}
                </p>
                <div className="actions mt-auto">
                  <Button variant="secondary" onClick={() => show(journal)}>
                    <Settings2 size={15} />
                    配置
                  </Button>
                  <Button
                    variant="ghost"
                    disabled={!journal.sources.some((source) => source.enabled)}
                    onClick={() =>
                      location.assign(
                        `/crawler/tasks?journal=${encodeURIComponent(journal.name)}&source=${encodeURIComponent(journal.sources.find((source) => source.is_default)?.source_id || '')}`,
                      )
                    }
                  >
                    <Play size={15} />
                    去采集
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => {
                      if (confirm(`确定删除《${journal.name}》吗？`)) remove.mutate(journal.id)
                    }}
                  >
                    <Trash2 size={15} />
                  </Button>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState>还没有期刊</EmptyState>
        )}
      </Card>
      <Modal
        open={open}
        onOpenChange={setOpen}
        title={draft.id ? `配置《${draft.name}》` : '新增期刊'}
        wide
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              取消
            </Button>
            <Button
              disabled={!draft.name.trim() || !draft.region || save.isPending}
              onClick={() => save.mutate()}
            >
              保存
            </Button>
          </>
        }
      >
        <div className="form-grid">
          <Field className="span-12" label="期刊名称">
            <Input
              value={draft.name}
              onChange={(e) => setDraft((v) => ({ ...v, name: e.target.value }))}
            />
          </Field>
          <Field className="span-4" label="区域">
            <Select
              value={draft.region}
              onChange={(e) =>
                rebuild(
                  e.target.value,
                  draft.id ? journals.data?.find((j) => j.id === draft.id) : undefined,
                )
              }
            >
              <option value="domestic">国内</option>
              <option value="foreign">国外</option>
            </Select>
          </Field>
          <Field className="span-4" label="ISSN">
            <Input
              value={draft.issn}
              onChange={(e) => setDraft((v) => ({ ...v, issn: e.target.value }))}
            />
          </Field>
          <Field className="span-4" label="出版方">
            <Input
              value={draft.publisher}
              onChange={(e) => setDraft((v) => ({ ...v, publisher: e.target.value }))}
            />
          </Field>
        </div>
        <div className="source-list">
          {draft.rows.map((row) => (
            <article
              className={row.enabled ? 'source-row active' : 'source-row'}
              key={row.source_id}
            >
              <div className="actions justify-between">
                <div>
                  <strong>{row.display_name}</strong>
                  <p className="muted">
                    {row.capabilities.list_issues ? '支持列期号' : '手工填写期号'}
                    {row.capabilities.needs_browser ? ' · 需要浏览器' : ''}
                  </p>
                </div>
                <label className="switch-label">
                  <input
                    type="checkbox"
                    checked={row.enabled}
                    onChange={(e) =>
                      updateRow(row.source_id, {
                        enabled: e.target.checked,
                        is_default: e.target.checked ? row.is_default : false,
                      })
                    }
                  />
                  启用
                </label>
              </div>
              {row.enabled && (
                <>
                  <label className="switch-label">
                    <input
                      type="radio"
                      name="default-source"
                      checked={row.is_default}
                      onChange={() =>
                        setDraft((current) => ({
                          ...current,
                          rows: current.rows.map((item) => ({
                            ...item,
                            is_default: item.source_id === row.source_id,
                          })),
                        }))
                      }
                    />
                    默认源
                  </label>
                  {row.config_fields.map((field) => (
                    <Field
                      key={field.key}
                      label={`${field.label}${field.required ? ' *' : ''}`}
                      hint={field.help}
                    >
                      <Input
                        value={row.config[field.key] || ''}
                        placeholder={field.placeholder}
                        onChange={(e) =>
                          updateRow(row.source_id, {
                            config: { ...row.config, [field.key]: e.target.value },
                          })
                        }
                      />
                    </Field>
                  ))}
                  {journalId !== undefined && (
                    <div className="actions">
                      <Button
                        variant="secondary"
                        disabled={testSource.isPending}
                        onClick={() =>
                          testSource.mutate({ id: journalId, sourceId: row.source_id })
                        }
                      >
                        <RefreshCw size={15} />
                        测试连接
                      </Button>
                      {row.testStatus && (
                        <Badge tone={statusTone(row.testStatus)}>
                          {row.testMessage || row.testStatus}
                        </Badge>
                      )}
                    </div>
                  )}
                </>
              )}
            </article>
          ))}
        </div>
      </Modal>
    </div>
  )
}

export function CrawlTaskPage() {
  const client = useQueryClient(),
    tasks = useQuery({ queryKey: ['crawl-tasks'], queryFn: crawlApi.tasks }),
    issues = useQuery({ queryKey: ['raw-issues'], queryFn: crawlApi.issues }),
    journals = useQuery({ queryKey: ['journals'], queryFn: journalApi.list }),
    sources = useQuery({ queryKey: ['collection-sources'], queryFn: journalApi.sources })
  const search = new URLSearchParams(location.search),
    requestedJournal = search.get('journal') || '',
    requestedSource = search.get('source') || ''
  const [first] = journals.data || []
  const [journalName, setJournalName] = useState(requestedJournal || first?.name || ''),
    [sourceId, setSourceId] = useState(requestedSource),
    [year, setYear] = useState(new Date().getFullYear()),
    [issue, setIssue] = useState(''),
    [downloadFulltext, setDownloadFulltext] = useState(false),
    [probed, setProbed] = useState<ProbeIssue[]>([]),
    [last, setLast] = useState<RawIssue | null>(null)
  const journal = (journals.data || []).find((item) => item.name === journalName),
    available = (journal?.sources || []).filter((source) => source.enabled),
    sourceMeta = sources.data?.find((source) => source.source_id === sourceId),
    canDownloadFulltext = Boolean(sourceMeta?.capabilities.download_pdf)
  const chooseJournal = (name: string) => {
    setJournalName(name)
    const next = (journals.data || []).find((item) => item.name === name)
    const preferred =
      next?.sources.find((source) => source.enabled && source.is_default) ||
      next?.sources.find((source) => source.enabled)
    setSourceId(preferred?.source_id || '')
    setDownloadFulltext(false)
    setProbed([])
  }
  const probe = useMutation({
    mutationFn: () => journalApi.probeIssues(journal!.id, sourceId, year),
    onSuccess: (result) => {
      setProbed(result.issues || [])
      if (!result.issues.length) toast.warning('未探测到可用期号，请手工填写')
    },
    onError: (error) => toast.error(error.message),
  })
  const create = useMutation({
    mutationFn: () =>
      crawlApi.create({
        source_type: sourceId,
        journal_name: journalName,
        year,
        issue,
        download_fulltext: downloadFulltext,
      }),
    onSuccess: async (result) => {
      setLast(result.raw_issue)
      toast.success(
        result.fulltext_task ? '题录采集完成，全文任务已开始' : '采集任务完成并已写入原始数据库',
      )
      if (result.fulltext_error) toast.warning(`全文任务未启动：${result.fulltext_error}`)
      await Promise.all([
        client.invalidateQueries({ queryKey: ['crawl-tasks'] }),
        client.invalidateQueries({ queryKey: ['raw-issues'] }),
      ])
    },
    onError: (error) => toast.error(error.message),
  })
  if (tasks.isLoading || issues.isLoading || journals.isLoading || sources.isLoading)
    return <LoadingState />
  if (tasks.error || issues.error || journals.error || sources.error)
    return <ErrorState error={tasks.error || issues.error || journals.error || sources.error} />
  const taskList = [...(tasks.data || [])].sort(
    (a, b) =>
      Date.parse(b.started_at || b.created_at || '') -
      Date.parse(a.started_at || a.created_at || ''),
  )
  return (
    <div className="page-shell">
      <PageHero
        eyebrow="Collection Desk · Launch"
        title="采集任务台"
        description="选择期刊、已启用采集源、年份和期号，发起同步采集。"
        metrics={[
          { label: 'Tasks', value: taskList.length },
          { label: 'Issues', value: issues.data?.total || 0 },
          { label: 'Mode', value: 'Synchronous' },
        ]}
      />
      <div className="content-grid-2">
        <Card>
          <PanelHeader title="新建采集任务" />
          <div className="form-grid">
            <Field className="span-6" label="期刊">
              <Select value={journalName} onChange={(e) => chooseJournal(e.target.value)}>
                <option value="">请选择</option>
                {(journals.data || []).map((item) => (
                  <option key={item.id}>{item.name}</option>
                ))}
              </Select>
            </Field>
            <Field className="span-6" label="采集源">
              <Select
                value={sourceId}
                disabled={!journalName}
                onChange={(e) => {
                  setSourceId(e.target.value)
                  setDownloadFulltext(false)
                  setProbed([])
                }}
              >
                <option value="">请选择</option>
                {available.map((source) => (
                  <option value={source.source_id} key={source.source_id}>
                    {sources.data?.find((meta) => meta.source_id === source.source_id)
                      ?.display_name || source.source_id}
                    {source.is_default ? '（默认）' : ''}
                  </option>
                ))}
              </Select>
            </Field>
            <Field className="span-4" label="年份">
              <Input
                type="number"
                min="1990"
                max="2100"
                value={year}
                onChange={(e) => {
                  setYear(Number(e.target.value))
                  setProbed([])
                }}
              />
            </Field>
            <Field className="span-4" label="期号">
              <Input value={issue} onChange={(e) => setIssue(e.target.value)} />
            </Field>
            <div className="span-4 flex items-end">
              <Button
                variant="secondary"
                disabled={
                  !journal || !sourceId || !sourceMeta?.capabilities.list_issues || probe.isPending
                }
                onClick={() => probe.mutate()}
              >
                探测期号
              </Button>
            </div>
            {canDownloadFulltext && (
              <Field className="span-12" label="采集内容">
                <label className="switch-label">
                  <input
                    type="checkbox"
                    checked={downloadFulltext}
                    onChange={(e) => setDownloadFulltext(e.target.checked)}
                  />
                  题录完成后补采全文
                </label>
              </Field>
            )}
          </div>
          {journalName && !available.length && (
            <div className="alert alert--warning mt-4">
              该期刊尚未配置可用源。<Link to="/crawler/journals">前往配置</Link>
            </div>
          )}
          {probed.length > 0 && (
            <div className="actions mt-4">
              {probed.map((item) => (
                <Button
                  variant={issue === String(item.issue) ? 'primary' : 'secondary'}
                  key={item.issue}
                  onClick={() => setIssue(String(item.issue))}
                >
                  第 {item.issue} 期{item.volume ? ` · Vol.${item.volume}` : ''}
                </Button>
              ))}
            </div>
          )}
          <Button
            className="mt-5 w-full"
            disabled={!journalName || !sourceId || !issue || create.isPending}
            onClick={() => create.mutate()}
          >
            {create.isPending ? '采集中...' : '发起采集'}
          </Button>
          {last && (
            <div className="alert mt-4">
              最近完成：{last.journal_name} {last.year} 年第 {last.issue} 期{' '}
              <Link to="/crawler/issues/$id" params={{ id: String(last.id) }}>
                查看结果
              </Link>
            </div>
          )}
        </Card>
        <Card>
          <PanelHeader title="任务记录" />
          <div className="task-list">
            {taskList.map((task) => (
              <article className="task-row" key={task.id}>
                <div>
                  <strong>{task.journal_name}</strong>
                  <p className="muted">
                    {sources.data?.find((meta) => meta.source_id === task.source_type)
                      ?.display_name || task.source_type}{' '}
                    · {task.year} / 第 {task.issue} 期
                  </p>
                  {task.error_message && <p className="text-danger">{task.error_message}</p>}
                </div>
                <Badge tone={statusTone(task.status)}>{task.status}</Badge>
              </article>
            ))}
            {!taskList.length && <EmptyState />}
          </div>
        </Card>
      </div>
    </div>
  )
}

interface IssueGroup {
  id: string
  title: string
  issues: RawIssue[]
}
function issueNumber(value: string) {
  const matched = value.match(/\d+/)
  return matched ? Number(matched[0]) : -1
}
export function RawIssueListPage() {
  const query = useQuery({ queryKey: ['raw-issues'], queryFn: crawlApi.issues }),
    [region, setRegion] = useState('all'),
    [selected, setSelected] = useState('')
  const filtered = useMemo(
    () =>
      [...(query.data?.items || [])]
        .filter((item) => region === 'all' || item.region === region)
        .sort(
          (a, b) =>
            a.journal_name.localeCompare(b.journal_name, 'zh-CN') ||
            b.year - a.year ||
            issueNumber(b.issue) - issueNumber(a.issue),
        ),
    [query.data, region],
  )
  const groups = useMemo<IssueGroup[]>(() => {
    const map = new Map<string, RawIssue[]>()
    filtered.forEach((item) => {
      const key = item.journal_name
      map.set(key, [...(map.get(key) || []), item])
    })
    return [...map].map(([title, items]) => ({ id: title, title, issues: items }))
  }, [filtered])
  const selectedIssues =
    groups.find((group) => group.id === selected)?.issues || groups[0]?.issues || []
  if (query.isLoading) return <LoadingState />
  if (query.error) return <ErrorState error={query.error} />
  return (
    <div className="page-shell">
      <PageHero
        eyebrow="Collection Archive · Issues"
        title="采集期号库"
        description="按期刊和年份浏览原始采集结果，追踪翻译与分析状态。"
        metrics={[
          { label: 'Total Issues', value: query.data?.total || 0 },
          { label: 'Filtered', value: filtered.length },
          { label: 'Journals', value: groups.length },
        ]}
      />
      <Card>
        <PanelHeader
          title="按期刊浏览"
          actions={
            <div className="actions">
              <Select
                value={region}
                onChange={(e) => {
                  setRegion(e.target.value)
                  setSelected('')
                }}
              >
                <option value="all">全部区域</option>
                <option value="domestic">国内</option>
                <option value="foreign">国外</option>
              </Select>
              <Button variant="secondary" asChild>
                <Link to="/crawler/tasks">返回任务台</Link>
              </Button>
              <Button asChild>
                <Link to="/paper-analysis">
                  <BrainCircuit size={16} />
                  论文分析
                </Link>
              </Button>
            </div>
          }
        />
        <div className="archive-grid">
          <aside className="archive-sidebar">
            {groups.map((group) => (
              <button
                type="button"
                className={
                  (selected || groups[0]?.id) === group.id ? 'archive-node active' : 'archive-node'
                }
                key={group.id}
                onClick={() => setSelected(group.id)}
              >
                <span>{group.title}</span>
                <Badge>{group.issues.length}</Badge>
              </button>
            ))}
          </aside>
          <section>
            {selectedIssues.length ? (
              <div className="cards-grid cards-grid--2">
                {selectedIssues.map((item) => (
                  <article className="item-card" key={item.id}>
                    <div className="actions justify-between">
                      <strong>
                        {item.year} 年第 {item.issue} 期
                      </strong>
                      <Badge>{regionLabel(item.region)}</Badge>
                    </div>
                    <p className="muted">
                      {item.source_type} · 论文 {item.paper_count || 0} 篇
                    </p>
                    <div className="actions">
                      <Badge
                        tone={
                          item.region === 'domestic' || item.translation_status === 'completed'
                            ? 'success'
                            : 'warning'
                        }
                      >
                        翻译：
                        {item.region === 'domestic'
                          ? '不需要'
                          : item.translation_status === 'completed'
                            ? '已完成'
                            : '未完成'}
                      </Badge>
                    </div>
                    <div className="actions mt-4">
                      <Button variant="secondary" asChild>
                        <Link to="/crawler/issues/$id" params={{ id: String(item.id) }}>
                          查看详情
                        </Link>
                      </Button>
                      <Button asChild>
                        <a
                          href={`/paper-analysis?journal=${encodeURIComponent(item.journal_name)}&year=${item.year}&issue=${encodeURIComponent(item.issue)}`}
                        >
                          <BrainCircuit size={16} />
                          分析本期
                        </a>
                      </Button>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <EmptyState>暂无可展示期号</EmptyState>
            )}
          </section>
        </div>
      </Card>
    </div>
  )
}

export function RawIssueDetailPage() {
  const id = useParams({ strict: false }).id || '',
    navigate = useNavigate(),
    client = useQueryClient(),
    issue = useQuery({
      queryKey: ['raw-issue', id],
      queryFn: () => crawlApi.issue(id),
      enabled: Boolean(id),
    }),
    fulltextTasks = useQuery({
      queryKey: ['fulltext-tasks', 'issue', id],
      queryFn: () => fulltextApi.list({ raw_issue_id: id, limit: 1 }),
      enabled: Boolean(id),
      refetchInterval: (query) => (isFullTextRunning(query.state.data?.[0]) ? 2000 : false),
    })
  const [lang, setLang] = useState<'zh' | 'en'>('en')
  const refresh = async () =>
    Promise.all([
      client.invalidateQueries({ queryKey: ['raw-issue', id] }),
      client.invalidateQueries({ queryKey: ['raw-issues'] }),
    ])
  const translate = useMutation({
    mutationFn: () => crawlApi.translate(id),
    onSuccess: async () => {
      toast.success('翻译完成')
      setLang('zh')
      await refresh()
    },
    onError: (error) => toast.error(error.message),
  })
  const remove = useMutation({
    mutationFn: () => crawlApi.removeIssue(id),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: ['raw-issues'] })
      toast.success('采集期号已删除，文献列表已按剩余来源更新')
      await navigate({ to: '/crawler/issues' })
    },
    onError: (error) => toast.error(error.message),
  })
  const acquireFulltext = useMutation({
    mutationFn: () => fulltextApi.createForIssue(id),
    onSuccess: async (task) => {
      client.setQueryData(['fulltext-tasks', 'issue', id], [task])
      toast.success('本期全文补采任务已开始')
      await client.invalidateQueries({ queryKey: ['fulltext-tasks', 'issue', id] })
    },
    onError: (error) => toast.error(error.message),
  })
  if (issue.isLoading || fulltextTasks.isLoading) return <LoadingState />
  if (issue.error || fulltextTasks.error || !issue.data)
    return <ErrorState error={issue.error || fulltextTasks.error} />
  const item = issue.data,
    isDomestic = item.region === 'domestic',
    displayLang = isDomestic ? 'zh' : lang,
    latestFulltextTask = fulltextTasks.data?.[0]
  return (
    <div className="page-shell">
      <PageHero
        eyebrow="Issue Workspace · Detail"
        title={item.journal_name}
        description={`${item.year} 年 · 第 ${item.issue} 期${item.volume ? ` · Vol.${item.volume}` : ''}`}
        metrics={[
          { label: 'Source', value: item.source_type },
          { label: 'Papers', value: item.paper_count || 0 },
          {
            label: 'Translation',
            value: isDomestic ? 'N/A' : item.translation_status || 'pending',
          },
        ]}
      />
      <div className="actions justify-between">
        <Button variant="secondary" asChild>
          <Link to="/crawler/issues">返回期号库</Link>
        </Button>
        <div className="actions">
          {item.source_url && (
            <Button variant="secondary" asChild>
              <a href={item.source_url} target="_blank" rel="noreferrer">
                打开来源页面
              </a>
            </Button>
          )}
          {item.source_type === 'magtech' && (
            <Button
              disabled={acquireFulltext.isPending || isFullTextRunning(latestFulltextTask)}
              onClick={() => acquireFulltext.mutate()}
            >
              <Download size={16} />
              {isFullTextRunning(latestFulltextTask) ? '全文下载中' : '补采本期全文'}
            </Button>
          )}
          <Button asChild>
            <a
              href={`/paper-analysis?journal=${encodeURIComponent(item.journal_name)}&year=${item.year}&issue=${encodeURIComponent(item.issue)}`}
            >
              <BrainCircuit size={16} />
              分析本期
            </a>
          </Button>
          <Button
            variant="danger"
            disabled={remove.isPending}
            onClick={() => {
              if (
                confirm(
                  `确定删除《${item.journal_name}》${item.year} 年第 ${item.issue} 期的 ${item.source_type} 采集记录吗？文献列表会保留，并按剩余来源重新计算。`,
                )
              )
                remove.mutate()
            }}
          >
            <Trash2 size={16} />
            {remove.isPending ? '删除中...' : '删除采集记录'}
          </Button>
        </div>
      </div>
      <FullTextTaskSummary task={latestFulltextTask} />
      <Card>
        <PanelHeader
          title="论文详情"
          actions={
            <div className="actions">
              {!isDomestic && (
                <>
                  <Button disabled={translate.isPending} onClick={() => translate.mutate()}>
                    {translate.isPending ? '翻译中...' : '翻译本期'}
                  </Button>
                  <Select
                    value={lang}
                    onChange={(e) => setLang(e.target.value === 'zh' ? 'zh' : 'en')}
                  >
                    <option value="zh">中文</option>
                    <option value="en">English</option>
                  </Select>
                </>
              )}
              <span className="muted">共 {item.papers?.length || 0} 篇</span>
            </div>
          }
        />
        <div className="paper-list">
          {item.papers?.map((paper, index) => {
            const title =
              displayLang === 'zh' ? paper.title_zh || paper.title : paper.title || paper.title_zh
            const abstract =
              displayLang === 'zh'
                ? paper.abstract_zh || paper.abstract
                : paper.abstract || paper.abstract_zh
            return (
              <details className="paper-item" key={paper.id}>
                <summary>
                  <span>#{index + 1}</span>
                  <strong>{title || '暂无标题'}</strong>
                </summary>
                <div className="paper-body">
                  <p className="muted">
                    {paper.authors || '未填写作者'}
                    {paper.pages ? ` · ${paper.pages}` : ''}
                    {paper.doi ? ` · DOI ${paper.doi}` : ''}
                  </p>
                  <p className="prose whitespace-pre-wrap">{abstract || '暂无摘要'}</p>
                  {paper.detail_url && (
                    <a href={paper.detail_url} target="_blank" rel="noreferrer">
                      打开论文页面
                    </a>
                  )}
                </div>
              </details>
            )
          })}
          {!item.papers?.length && <EmptyState />}
        </div>
      </Card>
    </div>
  )
}
