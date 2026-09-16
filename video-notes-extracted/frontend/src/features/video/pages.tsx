import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from '@tanstack/react-router'
import { Clipboard, Download, Plus, Video } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import type { VideoTask } from '@/api/types'
import { llmApi, videoApi } from '@/api/resources'
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
import { downloadText, formatDate } from '@/lib/utils'

function statusLabel(status?: string) {
  return (
    (
      { pending: '待执行', running: '运行中', completed: '已完成', failed: '失败' } as Record<
        string,
        string
      >
    )[status || ''] ||
    status ||
    '未知'
  )
}
function stepLabel(step?: string) {
  return (
    (
      {
        download_audio: '下载音频',
        transcribe_srt: '转写字幕',
        generate_note: '生成笔记',
        done: '已完成',
        error: '执行失败',
      } as Record<string, string>
    )[step || ''] || '等待开始'
  )
}
function statusTone(status?: string): 'neutral' | 'success' | 'warning' | 'danger' {
  if (status === 'completed') return 'success'
  if (status === 'running') return 'warning'
  if (status === 'failed') return 'danger'
  return 'neutral'
}
const shouldPoll = (task?: VideoTask) =>
  Boolean(task && ['pending', 'running'].includes(task.status))

export function VideoNoteHomePage() {
  const navigate = useNavigate(),
    client = useQueryClient(),
    tasks = useQuery({
      queryKey: ['video-tasks'],
      queryFn: videoApi.list,
      refetchInterval: (query) => (query.state.data?.some(shouldPoll) ? 5000 : false),
    }),
    profiles = useQuery({ queryKey: ['llm-profiles'], queryFn: llmApi.profiles })
  const [url, setUrl] = useState(''),
    [model, setModel] = useState('large-v3-turbo'),
    [language, setLanguage] = useState('zh'),
    [device, setDevice] = useState('cuda'),
    [compute, setCompute] = useState('int8_float16'),
    [vad, setVad] = useState(true),
    [profileId, setProfileId] = useState('')
  const create = useMutation({
    mutationFn: () =>
      videoApi.create({
        source_url: url.trim(),
        whisper_model: model,
        language,
        device,
        compute_type: compute,
        use_vad: vad,
        profile_id: Number(profileId),
      }),
    onSuccess: async (task) => {
      toast.success('任务已创建，正在后台处理')
      await client.invalidateQueries({ queryKey: ['video-tasks'] })
      await navigate({ to: '/video-notes/tasks/$id', params: { id: String(task.id) } })
    },
    onError: (error) => toast.error(error.message),
  })
  if (tasks.isLoading || profiles.isLoading) return <LoadingState />
  if (tasks.error || profiles.error) return <ErrorState error={tasks.error || profiles.error} />
  const recent = tasks.data || []
  return (
    <div className="page-shell">
      <PageHero
        eyebrow="Media Notes Lab · Video"
        title="视频转笔记"
        description="输入 B 站视频链接，后台执行音频下载、Whisper 字幕转写和 Gemini 笔记生成。"
        metrics={[
          { label: 'Tasks', value: recent.length },
          { label: 'Running', value: recent.filter((task) => shouldPoll(task)).length },
          { label: 'Pipeline', value: '3 Steps' },
        ]}
      />
      <div className="content-grid-2">
        <Card>
          <PanelHeader title="新建视频任务" />
          <div className="form-grid">
            <Field className="span-12" label="B 站视频链接">
              <Input
                value={url}
                placeholder="https://www.bilibili.com/video/BV..."
                onChange={(e) => setUrl(e.target.value)}
              />
            </Field>
            <Field className="span-6" label="Whisper 模型">
              <Select value={model} onChange={(e) => setModel(e.target.value)}>
                {['large-v3-turbo', 'large-v3', 'medium', 'small'].map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </Select>
            </Field>
            <Field className="span-6" label="笔记生成模型">
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
            <Field className="span-6" label="语言">
              <Select value={language} onChange={(e) => setLanguage(e.target.value)}>
                <option value="zh">中文</option>
                <option value="en">英文</option>
                <option value="auto">自动识别</option>
              </Select>
            </Field>
            <Field className="span-4" label="设备">
              <Select value={device} onChange={(e) => setDevice(e.target.value)}>
                <option value="cuda">cuda</option>
                <option value="cpu">cpu</option>
              </Select>
            </Field>
            <Field className="span-4" label="计算精度">
              <Select value={compute} onChange={(e) => setCompute(e.target.value)}>
                <option value="int8_float16">int8_float16</option>
                <option value="float16">float16</option>
                <option value="int8">int8</option>
              </Select>
            </Field>
            <Field className="span-4" label="VAD 过滤">
              <label className="switch-label">
                <input type="checkbox" checked={vad} onChange={(e) => setVad(e.target.checked)} />
                {vad ? '开启' : '关闭'}
              </label>
            </Field>
          </div>
          <Button
            className="mt-4 w-full"
            disabled={!url.trim() || !profileId || create.isPending}
            onClick={() => create.mutate()}
          >
            <Plus size={16} />
            {create.isPending ? '创建中...' : '创建任务'}
          </Button>
        </Card>
        <Card>
          <PanelHeader title="运行准备" />
          <div className="preparation-list">
            <article>
              <strong>必备工具</strong>
              <p>当前模块依赖 FFmpeg、yt-dlp 和 whisper 环境。</p>
            </article>
            <article>
              <strong>模型与网络</strong>
              <p>首次运行 faster-whisper 可能下载模型；笔记生成使用任务中选择的大模型。</p>
            </article>
            <article>
              <strong>任务产物</strong>
              <p>音频、SRT、Markdown 和元数据写入统一运行数据目录。</p>
            </article>
          </div>
        </Card>
      </div>
      <Card>
        <PanelHeader
          title="最近任务"
          actions={
            <Button variant="ghost" asChild>
              <Link to="/video-notes/tasks">查看全部</Link>
            </Button>
          }
        />
        {recent.length ? (
          <div className="task-list">
            {recent.slice(0, 4).map((task) => (
              <VideoTaskRow task={task} key={task.id} />
            ))}
          </div>
        ) : (
          <EmptyState>还没有视频任务</EmptyState>
        )}
      </Card>
    </div>
  )
}

function VideoTaskRow({ task }: { task: VideoTask }) {
  return (
    <article className="task-row">
      <div className="min-w-0">
        <strong>{task.video_title || task.bvid || `任务 #${task.id}`}</strong>
        <p className="muted">
          {task.bvid || '-'} · {task.progress_message || stepLabel(task.current_step)}
        </p>
        {task.error_message && <p className="text-danger">{task.error_message}</p>}
      </div>
      <div className="actions">
        <Badge tone={statusTone(task.status)}>{statusLabel(task.status)}</Badge>
        <Button variant="ghost" asChild>
          <Link to="/video-notes/tasks/$id" params={{ id: String(task.id) }}>
            详情
          </Link>
        </Button>
      </div>
    </article>
  )
}

export function VideoNoteListPage() {
  const query = useQuery({
    queryKey: ['video-tasks'],
    queryFn: videoApi.list,
    refetchInterval: (query) => (query.state.data?.some(shouldPoll) ? 5000 : false),
  })
  if (query.isLoading) return <LoadingState />
  if (query.error) return <ErrorState error={query.error} />
  const tasks = query.data || []
  return (
    <div className="page-shell">
      <PageHero
        eyebrow="Task Ledger · Video"
        title="视频任务列表"
        description="查看每个视频任务的当前步骤、执行结果和更新时间。"
        metrics={[
          { label: 'Total', value: tasks.length },
          { label: 'Running', value: tasks.filter(shouldPoll).length },
          { label: 'Completed', value: tasks.filter((task) => task.status === 'completed').length },
          { label: 'Failed', value: tasks.filter((task) => task.status === 'failed').length },
        ]}
      />
      <Card>
        <PanelHeader
          title="全部任务"
          actions={
            <Button asChild>
              <Link to="/video-notes">
                <Plus size={16} />
                新建任务
              </Link>
            </Button>
          }
        />
        {tasks.length ? (
          <div className="cards-grid">
            {tasks.map((task) => (
              <article className="item-card video-card" key={task.id}>
                <div className="actions justify-between">
                  <Video size={19} />
                  <Badge tone={statusTone(task.status)}>{statusLabel(task.status)}</Badge>
                </div>
                <h3>{task.video_title || task.bvid || `任务 #${task.id}`}</h3>
                <p className="muted">步骤：{stepLabel(task.current_step)}</p>
                <p className="muted break-all">{task.source_url}</p>
                {task.error_message && <p className="text-danger">{task.error_message}</p>}
                <div className="actions justify-between mt-auto">
                  <span className="muted">{formatDate(task.updated_at, true)}</span>
                  <Button variant="ghost" asChild>
                    <Link to="/video-notes/tasks/$id" params={{ id: String(task.id) }}>
                      查看详情
                    </Link>
                  </Button>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState>还没有视频任务</EmptyState>
        )}
      </Card>
    </div>
  )
}

export function VideoNoteDetailPage() {
  const id = useParams({ strict: false }).id || '',
    client = useQueryClient()
  const task = useQuery({
    queryKey: ['video-task', id],
    queryFn: () => videoApi.get(id),
    enabled: Boolean(id),
    refetchInterval: (query) => (shouldPoll(query.state.data) ? 5000 : false),
  })
  const logs = useQuery({
    queryKey: ['video-task-logs', id],
    queryFn: () => videoApi.logs(id),
    enabled: Boolean(id),
    refetchInterval: () => (shouldPoll(task.data) ? 5000 : false),
  })
  const refresh = async () =>
    Promise.all([
      client.invalidateQueries({ queryKey: ['video-task', id] }),
      client.invalidateQueries({ queryKey: ['video-task-logs', id] }),
      client.invalidateQueries({ queryKey: ['video-tasks'] }),
    ])
  if (task.isLoading || logs.isLoading) return <LoadingState />
  if (task.error || logs.error || !task.data) return <ErrorState error={task.error || logs.error} />
  const item = task.data,
    stepIndex =
      (
        { download_audio: 1, transcribe_srt: 2, generate_note: 3, done: 3 } as Record<
          string,
          number
        >
      )[item.current_step || ''] || 0
  const copy = async (text?: string, message = '内容已复制') => {
    if (!text) return
    try {
      await navigator.clipboard.writeText(text)
      toast.success(message)
    } catch {
      toast.error('复制失败，请检查浏览器权限')
    }
  }
  return (
    <div className="page-shell">
      <PageHero
        eyebrow="Task Detail · Video"
        title={item.video_title || item.bvid || `任务 #${id}`}
        description={item.source_url}
        metrics={[
          { label: 'Status', value: statusLabel(item.status) },
          { label: 'Step', value: stepLabel(item.current_step) },
          { label: 'BVID', value: item.bvid || '-' },
          { label: 'Logs', value: logs.data?.length || 0 },
        ]}
      />
      <div className="actions justify-between">
        <Button variant="secondary" asChild>
          <Link to="/video-notes/tasks">返回列表</Link>
        </Button>
        <Button variant="ghost" onClick={() => void refresh()}>
          <span>刷新</span>
        </Button>
      </div>
      <div className="content-grid-2">
        <div className="page-shell">
          <Card>
            <PanelHeader title="执行状态" />
            <div className="alert">
              <strong>当前步骤：</strong>
              {stepLabel(item.current_step)}
              <br />
              <strong>进度说明：</strong>
              {item.progress_message || '等待开始'}
              {item.error_message && <p className="text-danger">{item.error_message}</p>}
            </div>
            <div className="step-track">
              {['下载音频', '转写字幕', '生成笔记'].map((label, index) => (
                <div className={stepIndex >= index + 1 ? 'step done' : 'step'} key={label}>
                  <span>{index + 1}</span>
                  <strong>{label}</strong>
                </div>
              ))}
            </div>
          </Card>
          <Card>
            <PanelHeader title="任务产物" />
            <div className="metadata-list">
              {[
                ['音频路径', item.audio_path],
                ['字幕路径', item.transcript_path],
                ['笔记路径', item.note_path],
                ['元数据路径', item.metadata_path],
              ].map(([label, value]) => (
                <div key={label}>
                  <span>{label}</span>
                  <strong className="break-all">{value || '--'}</strong>
                </div>
              ))}
            </div>
          </Card>
          <Card>
            <PanelHeader title="日志时间线" />
            {logs.data?.length ? (
              <div className="timeline">
                {logs.data.map((log) => (
                  <article
                    className={log.level === 'error' ? 'timeline-item error' : 'timeline-item'}
                    key={log.id}
                  >
                    <span>{formatDate(log.created_at, true)}</span>
                    <p>{log.message}</p>
                  </article>
                ))}
              </div>
            ) : (
              <EmptyState>还没有任务日志</EmptyState>
            )}
          </Card>
        </div>
        <div className="page-shell">
          <Card>
            <PanelHeader
              title="SRT 预览"
              actions={
                <Button
                  variant="ghost"
                  disabled={!item.transcript_content}
                  onClick={() => void copy(item.transcript_content, '字幕内容已复制')}
                >
                  <Clipboard size={15} />
                  复制字幕
                </Button>
              }
            />
            <pre className="code-block video-transcript">
              {item.transcript_content || '字幕尚未生成'}
            </pre>
          </Card>
          <Card>
            <PanelHeader
              title="Markdown 笔记"
              actions={
                <div className="actions">
                  <Button
                    variant="ghost"
                    disabled={!item.note_content}
                    onClick={() => void copy(item.note_content, '笔记内容已复制')}
                  >
                    <Clipboard size={15} />
                    复制
                  </Button>
                  <Button
                    variant="ghost"
                    disabled={!item.note_content}
                    onClick={() =>
                      item.note_content &&
                      downloadText(
                        item.note_content,
                        `${item.bvid || `video-note-${id}`}.md`,
                        'text/markdown;charset=utf-8',
                      )
                    }
                  >
                    <Download size={15} />
                    下载
                  </Button>
                </div>
              }
            />
            <pre className="note-preview">{item.note_content || '笔记尚未生成'}</pre>
          </Card>
        </div>
      </div>
    </div>
  )
}
