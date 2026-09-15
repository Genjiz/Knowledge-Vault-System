import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  BrainCircuit,
  ChevronLeft,
  ChevronRight,
  FileText,
  History,
  Play,
  RefreshCw,
  Search,
  Trash2,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import type { PaperAnalysis } from '@/api/types'
import { literatureApi, llmApi, paperAnalysisApi } from '@/api/resources'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Field,
  Input,
  LoadingState,
  PageHero,
  PanelHeader,
  Select,
  Textarea,
} from '@/components/ui'
import { collectionPeriodLabel, collectionVolumeLabel, isUnassignedIssue } from '@/lib/collection'
import { renderMarkdownToHtml } from '@/lib/markdown'
import { formatDate } from '@/lib/utils'
import { analysisPageCount, groupAnalysisIssues, issueKey, toggleSelectedPaper } from './model'

const PAPER_PAGE_SIZE = 30

function statusTone(status?: string): 'neutral' | 'success' | 'warning' | 'danger' {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'queued' || status === 'running') return 'warning'
  return 'neutral'
}

function statusLabel(status?: string) {
  return (
    { queued: '等待中', running: '分析中', completed: '已完成', failed: '失败' }[status || ''] ||
    status
  )
}

export function PaperAnalysisPage() {
  const requestedIssueKeys = (() => {
    const params = new URLSearchParams(location.search)
    const journal = params.get('journal')
    const year = params.get('year')
    const volume = params.get('volume') || 'unknown'
    const issue = params.get('issue')
    return journal && year && issue ? [`${journal}:${year}:${volume}:${issue}`] : []
  })()
  const client = useQueryClient()
  const issues = useQuery({ queryKey: ['paper-analysis-issues'], queryFn: paperAnalysisApi.issues })
  const promptTemplate = useQuery({
    queryKey: ['paper-analysis-prompt-template'],
    queryFn: paperAnalysisApi.promptTemplate,
  })
  const profiles = useQuery({ queryKey: ['llm-profiles'], queryFn: llmApi.profiles })
  const history = useQuery({
    queryKey: ['paper-analyses'],
    queryFn: paperAnalysisApi.list,
    refetchInterval: (query) =>
      query.state.data?.items.some((item) => ['queued', 'running'].includes(item.status))
        ? 2000
        : false,
  })
  const [mode, setMode] = useState<'issues' | 'papers'>('issues')
  const [selectedIssueKeys, setSelectedIssueKeys] = useState<string[]>(requestedIssueKeys)
  const [selectedPaperIds, setSelectedPaperIds] = useState<number[]>([])
  const [search, setSearch] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [paperPage, setPaperPage] = useState(1)
  const [title, setTitle] = useState('')
  const [profileId, setProfileId] = useState('')
  const [customInstruction, setCustomInstruction] = useState('')
  const [includeFulltext, setIncludeFulltext] = useState(false)
  const [activeId, setActiveId] = useState<number | null>(null)
  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearchQuery(search.trim())
      setPaperPage(1)
    }, 300)
    return () => window.clearTimeout(timer)
  }, [search])
  const papers = useQuery({
    queryKey: ['analysis-literatures', searchQuery, paperPage],
    queryFn: () =>
      literatureApi.list({
        page: paperPage,
        per_page: PAPER_PAGE_SIZE,
        q: searchQuery || undefined,
      }),
    enabled: mode === 'papers',
  })
  const issueGroups = useMemo(() => groupAnalysisIssues(issues.data || []), [issues.data])
  const selectedIssues = useMemo(
    () =>
      mode === 'issues'
        ? (issues.data || []).filter((item) => selectedIssueKeys.includes(issueKey(item)))
        : [],
    [issues.data, mode, selectedIssueKeys],
  )
  const selectionPayload = useMemo(
    () => ({
      literature_ids: mode === 'papers' ? selectedPaperIds : [],
      issues: mode === 'issues' ? selectedIssues : [],
    }),
    [mode, selectedPaperIds, selectedIssues],
  )
  const hasSelection = Boolean(
    selectionPayload.literature_ids.length || selectionPayload.issues.length,
  )
  const preview = useQuery({
    queryKey: ['paper-analysis-preview', selectionPayload],
    queryFn: () => paperAnalysisApi.preview(selectionPayload),
    enabled: hasSelection,
  })
  const detail = useQuery({
    queryKey: ['paper-analysis', activeId],
    queryFn: () => paperAnalysisApi.get(activeId!),
    enabled: activeId !== null,
    refetchInterval: (query) =>
      query.state.data && ['queued', 'running'].includes(query.state.data.status) ? 2000 : false,
  })
  const refreshHistory = async () => {
    await client.invalidateQueries({ queryKey: ['paper-analyses'] })
  }
  const create = useMutation({
    mutationFn: () =>
      paperAnalysisApi.create({
        ...selectionPayload,
        title: title.trim() || undefined,
        profile_id: profileId ? Number(profileId) : undefined,
        custom_instruction: customInstruction.trim() || undefined,
        include_fulltext: includeFulltext,
      }),
    onSuccess: async (analysis) => {
      setActiveId(analysis.id)
      toast.success('分析任务已创建')
      await refreshHistory()
    },
    onError: (error) => toast.error(error.message),
  })
  const rerun = useMutation({
    mutationFn: (analysis: PaperAnalysis) =>
      paperAnalysisApi.rerun(analysis.id, profileId ? Number(profileId) : undefined),
    onSuccess: async (analysis) => {
      setActiveId(analysis.id)
      toast.success('重新分析任务已创建')
      await refreshHistory()
    },
    onError: (error) => toast.error(error.message),
  })
  const remove = useMutation({
    mutationFn: paperAnalysisApi.remove,
    onSuccess: async (_, removedId) => {
      if (activeId === removedId) setActiveId(null)
      toast.success('分析记录已删除')
      await refreshHistory()
    },
    onError: (error) => toast.error(error.message),
  })
  const changeMode = (nextMode: 'issues' | 'papers') => {
    setMode(nextMode)
    if (nextMode === 'issues') setSelectedPaperIds([])
    else setSelectedIssueKeys([])
  }

  if (issues.isLoading || promptTemplate.isLoading || profiles.isLoading || history.isLoading)
    return <LoadingState />
  if (issues.error || promptTemplate.error || profiles.error || history.error)
    return (
      <ErrorState error={issues.error || promptTemplate.error || profiles.error || history.error} />
    )

  const selectedPapers = hasSelection ? preview.data || [] : []
  const missingAbstracts = selectedPapers.filter((paper) => !paper.abstract).length
  const availableFulltexts = selectedPapers.filter((paper) => paper.pdf_path).length
  const paperPageCount = analysisPageCount(papers.data?.total || 0, PAPER_PAGE_SIZE)

  return (
    <div className="page-shell">
      <PageHero
        eyebrow="Analysis · Papers"
        title="论文分析"
        description="按卷期或自选论文生成综合研究报告。"
        metrics={[
          { label: 'Selected Papers', value: selectedPapers.length },
          { label: 'Available Full Text', value: availableFulltexts },
          { label: 'Missing Abstracts', value: missingAbstracts },
          { label: 'Analysis Runs', value: history.data?.total || 0 },
        ]}
      />
      <Card>
        <PanelHeader
          title="选择分析范围"
          actions={
            <div className="segmented-control" aria-label="分析范围模式">
              <button
                className={mode === 'issues' ? 'active' : ''}
                onClick={() => changeMode('issues')}
              >
                整期分析
              </button>
              <button
                className={mode === 'papers' ? 'active' : ''}
                onClick={() => changeMode('papers')}
              >
                自选论文
              </button>
            </div>
          }
        />
        <div className="analysis-selector-grid">
          <div className="selection-pane">
            {mode === 'papers' && (
              <div className="selection-toolbar">
                <label className="search-field">
                  <Search size={16} />
                  <Input
                    aria-label="搜索论文"
                    placeholder="搜索标题、作者、期刊或关键词"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                  />
                </label>
              </div>
            )}
            <div className="selection-scroll">
              {mode === 'issues' ? (
                <div className="analysis-issue-tree">
                  {issueGroups.map((journalGroup) => (
                    <details open className="analysis-tree-node" key={journalGroup.journal}>
                      <summary>{journalGroup.journal}</summary>
                      {journalGroup.years.map((yearGroup) => (
                        <details
                          open
                          className="analysis-tree-node analysis-tree-node--year"
                          key={yearGroup.year}
                        >
                          <summary>{yearGroup.year} 年</summary>
                          {yearGroup.volumes.map((volumeGroup) => (
                            <div className="analysis-volume-group" key={volumeGroup.volume}>
                              <h3>{collectionVolumeLabel(volumeGroup.volume)}</h3>
                              {volumeGroup.issues.map((item) => {
                                const key = issueKey(item)
                                return (
                                  <label className="selection-row" key={key}>
                                    <input
                                      type="checkbox"
                                      aria-label={`${item.journal} ${collectionVolumeLabel(item.volume)} ${collectionPeriodLabel(item.year, item.issue)}`}
                                      checked={selectedIssueKeys.includes(key)}
                                      onChange={(event) =>
                                        setSelectedIssueKeys((current) =>
                                          event.target.checked
                                            ? [...current, key]
                                            : current.filter((value) => value !== key),
                                        )
                                      }
                                    />
                                    <span>
                                      <strong>
                                        {isUnassignedIssue(item.issue)
                                          ? '未分期'
                                          : `第 ${item.issue} 期`}
                                      </strong>
                                      <small>{item.paper_count} 篇论文</small>
                                    </span>
                                  </label>
                                )
                              })}
                            </div>
                          ))}
                        </details>
                      ))}
                    </details>
                  ))}
                  {!issueGroups.length && <EmptyState>暂无可分析卷期</EmptyState>}
                </div>
              ) : papers.isLoading ? (
                <LoadingState />
              ) : papers.error ? (
                <ErrorState error={papers.error} />
              ) : (
                <>
                  {(papers.data?.items || []).map((paper) => (
                    <label className="selection-row" key={paper.id}>
                      <input
                        type="checkbox"
                        aria-label={`选择论文：${paper.title}`}
                        checked={selectedPaperIds.includes(paper.id)}
                        onChange={(event) =>
                          setSelectedPaperIds((current) =>
                            toggleSelectedPaper(current, paper.id, event.target.checked),
                          )
                        }
                      />
                      <span>
                        <strong>{paper.title}</strong>
                        <small>
                          {paper.authors || '未填写作者'} · {paper.journal || '未填写期刊'} ·{' '}
                          {paper.year || '年份未知'}
                        </small>
                      </span>
                    </label>
                  ))}
                  {!papers.data?.items.length && <EmptyState>没有匹配的论文</EmptyState>}
                </>
              )}
            </div>
            {mode === 'papers' && !papers.isLoading && !papers.error && (
              <div className="selection-pagination">
                <span>
                  共 {papers.data?.total || 0} 篇 · 第 {paperPage}/{paperPageCount} 页
                </span>
                <div className="actions">
                  <button
                    className="icon-button"
                    aria-label="上一页论文"
                    title="上一页"
                    disabled={paperPage <= 1 || papers.isFetching}
                    onClick={() => setPaperPage((current) => Math.max(1, current - 1))}
                  >
                    <ChevronLeft size={17} />
                  </button>
                  <button
                    className="icon-button"
                    aria-label="下一页论文"
                    title="下一页"
                    disabled={paperPage >= paperPageCount || papers.isFetching}
                    onClick={() => setPaperPage((current) => Math.min(paperPageCount, current + 1))}
                  >
                    <ChevronRight size={17} />
                  </button>
                </div>
              </div>
            )}
          </div>
          <div className="selection-summary">
            <h3>已选论文</h3>
            <div className="selection-count">{selectedPapers.length}</div>
            <p className="muted">
              摘要缺失 {missingAbstracts} 篇 · 可用全文 {availableFulltexts} 篇
            </p>
            <div className="selected-paper-list">
              {selectedPapers.slice(0, 12).map((paper) => (
                <span key={paper.id}>{paper.title}</span>
              ))}
              {selectedPapers.length > 12 && <span>另有 {selectedPapers.length - 12} 篇</span>}
            </div>
          </div>
        </div>
      </Card>
      <Card>
        <PanelHeader title="分析任务配置" />
        <div className="analysis-config-grid">
          <div className="analysis-config-fields">
            <Field label="分析标题">
              <Input value={title} onChange={(event) => setTitle(event.target.value)} />
            </Field>
            <Field label="运行模型">
              <Select value={profileId} onChange={(event) => setProfileId(event.target.value)}>
                <option value="" disabled>
                  请选择模型
                </option>
                {(profiles.data || [])
                  .filter((profile) => profile.enabled)
                  .map((profile) => (
                    <option value={profile.id} key={profile.id}>
                      {profile.name} · {profile.model_name}
                    </option>
                  ))}
              </Select>
            </Field>
            <Field label="用户自定义分析要求">
              <Textarea
                rows={5}
                maxLength={10000}
                value={customInstruction}
                onChange={(event) => setCustomInstruction(event.target.value)}
              />
            </Field>
            <label className="switch-label analysis-fulltext-option">
              <input
                type="checkbox"
                aria-label="分析时包含可用全文"
                checked={includeFulltext}
                onChange={(event) => setIncludeFulltext(event.target.checked)}
              />
              <span>
                <strong>包含可用全文</strong>
                <small>当前选择中有 {availableFulltexts} 篇已关联 PDF</small>
              </span>
            </label>
            <Button
              disabled={!selectedPapers.length || !profileId || create.isPending}
              onClick={() => create.mutate()}
            >
              <Play size={16} />
              {create.isPending ? '创建中...' : '开始分析'}
            </Button>
          </div>
          <div className="prompt-panel">
            <div className="prompt-panel__heading">
              <span>默认 Prompt</span>
              <Badge>{promptTemplate.data?.version}</Badge>
            </div>
            <pre>{promptTemplate.data?.content}</pre>
          </div>
        </div>
      </Card>
      <div className="analysis-results-grid">
        <Card>
          <PanelHeader title="分析记录" actions={<History size={18} />} />
          <div className="task-list">
            {(history.data?.items || []).map((analysis) => (
              <button
                className={
                  activeId === analysis.id ? 'analysis-history-row active' : 'analysis-history-row'
                }
                key={analysis.id}
                onClick={() => setActiveId(analysis.id)}
              >
                <span>
                  <strong>{analysis.title}</strong>
                  <small>
                    {analysis.paper_count} 篇 · {formatDate(analysis.created_at)}
                  </small>
                </span>
                <Badge tone={statusTone(analysis.status)}>{statusLabel(analysis.status)}</Badge>
              </button>
            ))}
            {!history.data?.items.length && <EmptyState>暂无分析记录</EmptyState>}
          </div>
        </Card>
        <Card>
          <PanelHeader
            title={detail.data?.title || '分析结果'}
            actions={
              detail.data && (
                <div className="actions">
                  <Button
                    variant="secondary"
                    disabled={!profileId || rerun.isPending}
                    onClick={() => rerun.mutate(detail.data)}
                  >
                    <RefreshCw size={15} />
                    重新分析
                  </Button>
                  <button
                    className="icon-button"
                    aria-label="删除分析记录"
                    title="删除"
                    onClick={() => {
                      if (confirm('确定删除这条分析记录吗？')) remove.mutate(detail.data.id)
                    }}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              )
            }
          />
          {detail.data?.include_fulltext && (
            <div className="analysis-fulltext-summary">
              <FileText size={17} />
              已使用 {detail.data.fulltext_count || 0} 篇全文
              {detail.data.fulltext_failed_count ? (
                <span className="text-danger">
                  ，{detail.data.fulltext_failed_count} 篇解析失败
                </span>
              ) : null}
            </div>
          )}
          {detail.data?.fulltext_error_message && (
            <div className="alert alert--warning whitespace-pre-wrap">
              {detail.data.fulltext_error_message}
            </div>
          )}
          {detail.isLoading ? (
            <LoadingState />
          ) : detail.data?.content_markdown ? (
            <article
              className="prose analysis-markdown analysis-result"
              dangerouslySetInnerHTML={{
                __html: renderMarkdownToHtml(detail.data.content_markdown),
              }}
            />
          ) : detail.data ? (
            <div className={`alert ${detail.data.status === 'failed' ? 'alert--danger' : ''}`}>
              <BrainCircuit size={18} />
              {detail.data.error_message || statusLabel(detail.data.status)}
            </div>
          ) : (
            <EmptyState>选择一条分析记录查看结果</EmptyState>
          )}
        </Card>
      </div>
    </div>
  )
}
