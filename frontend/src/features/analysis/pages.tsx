import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BrainCircuit, History, Play, RefreshCw, Search, Trash2 } from 'lucide-react'
import { useMemo, useState } from 'react'
import { toast } from 'sonner'
import type { AnalysisIssueOption, PaperAnalysis } from '@/api/types'
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
} from '@/components/ui'
import { renderMarkdownToHtml } from '@/lib/markdown'
import { formatDate } from '@/lib/utils'
import { issueKey } from './model'

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
    const issue = params.get('issue')
    return journal && year && issue ? [`${journal}:${year}:${issue}`] : []
  })()
  const client = useQueryClient()
  const issues = useQuery({ queryKey: ['paper-analysis-issues'], queryFn: paperAnalysisApi.issues })
  const profiles = useQuery({ queryKey: ['llm-profiles'], queryFn: llmApi.profiles })
  const scenes = useQuery({ queryKey: ['llm-scenes'], queryFn: llmApi.scenes })
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
  const [title, setTitle] = useState('')
  const [profileId, setProfileId] = useState('')
  const [activeId, setActiveId] = useState<number | null>(null)
  const papers = useQuery({
    queryKey: ['analysis-literatures', search],
    queryFn: () => literatureApi.list({ page: 1, per_page: 100, title: search || undefined }),
  })
  const selectedIssues = useMemo(
    () => (issues.data || []).filter((item) => selectedIssueKeys.includes(issueKey(item))),
    [issues.data, selectedIssueKeys],
  )
  const selectionPayload = useMemo(
    () => ({ literature_ids: selectedPaperIds, issues: selectedIssues }),
    [selectedPaperIds, selectedIssues],
  )
  const preview = useQuery({
    queryKey: ['paper-analysis-preview', selectionPayload],
    queryFn: () => paperAnalysisApi.preview(selectionPayload),
    enabled: Boolean(selectedPaperIds.length || selectedIssues.length),
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
  if (issues.isLoading || profiles.isLoading || scenes.isLoading || history.isLoading)
    return <LoadingState />
  if (issues.error || profiles.error || scenes.error || history.error)
    return <ErrorState error={issues.error || profiles.error || scenes.error || history.error} />
  const selectedPapers = preview.data || []
  const missingAbstracts = selectedPapers.filter((paper) => !paper.abstract).length
  return (
    <div className="page-shell">
      <PageHero
        eyebrow="Workspace · Analysis"
        title="论文分析"
        description="从统一文献库选择论文并生成综合研究报告。"
        metrics={[
          { label: 'Selected Papers', value: selectedPapers.length },
          { label: 'Selected Issues', value: selectedIssues.length },
          { label: 'Missing Abstracts', value: missingAbstracts },
          { label: 'Analysis Runs', value: history.data?.total || 0 },
        ]}
      />
      <Card>
        <PanelHeader
          title="选择论文"
          actions={
            <div className="segmented-control" aria-label="选择方式">
              <button
                className={mode === 'issues' ? 'active' : ''}
                onClick={() => setMode('issues')}
              >
                按期号
              </button>
              <button
                className={mode === 'papers' ? 'active' : ''}
                onClick={() => setMode('papers')}
              >
                按论文
              </button>
            </div>
          }
        />
        <div className="analysis-selector-grid">
          <div className="selection-list">
            {mode === 'issues' ? (
              (issues.data || []).map((item: AnalysisIssueOption) => {
                const key = issueKey(item)
                return (
                  <label className="selection-row" key={key}>
                    <input
                      type="checkbox"
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
                      <strong>{item.journal || '未命名期刊'}</strong>
                      <small>
                        {item.year} 年第 {item.issue} 期 · {item.paper_count} 篇
                      </small>
                    </span>
                  </label>
                )
              })
            ) : (
              <>
                <label className="search-field">
                  <Search size={16} />
                  <Input
                    aria-label="搜索论文"
                    placeholder="按标题搜索"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                  />
                </label>
                {(papers.data?.items || []).map((paper) => (
                  <label className="selection-row" key={paper.id}>
                    <input
                      type="checkbox"
                      checked={selectedPaperIds.includes(paper.id)}
                      onChange={(event) =>
                        setSelectedPaperIds((current) =>
                          event.target.checked
                            ? [...current, paper.id]
                            : current.filter((value) => value !== paper.id),
                        )
                      }
                    />
                    <span>
                      <strong>{paper.title}</strong>
                      <small>
                        {paper.journal || '未填写期刊'} · {paper.year || '年份未知'}
                      </small>
                    </span>
                  </label>
                ))}
              </>
            )}
          </div>
          <div className="selection-summary">
            <h3>已选论文</h3>
            <div className="selection-count">{selectedPapers.length}</div>
            <p className="muted">其中 {missingAbstracts} 篇缺少摘要</p>
            <div className="selected-paper-list">
              {selectedPapers.slice(0, 12).map((paper) => (
                <span key={paper.id}>{paper.title}</span>
              ))}
              {selectedPapers.length > 12 && <span>另有 {selectedPapers.length - 12} 篇</span>}
            </div>
          </div>
        </div>
        <div className="analysis-runbar">
          <Field label="分析标题">
            <Input value={title} onChange={(event) => setTitle(event.target.value)} />
          </Field>
          <Field label="运行模型">
            <Select value={profileId} onChange={(event) => setProfileId(event.target.value)}>
              <option value="">场景默认模型</option>
              {(profiles.data || [])
                .filter((profile) => profile.enabled)
                .map((profile) => (
                  <option value={profile.id} key={profile.id}>
                    {profile.name} · {profile.model_name}
                  </option>
                ))}
            </Select>
          </Field>
          <Button
            disabled={!selectedPapers.length || create.isPending}
            onClick={() => create.mutate()}
          >
            <Play size={16} />
            {create.isPending ? '创建中...' : '开始分析'}
          </Button>
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
                    disabled={rerun.isPending}
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
