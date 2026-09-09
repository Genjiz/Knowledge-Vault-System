import { expect, test, type Page } from '@playwright/test'

const sampleLiterature = {
  id: 1,
  title: 'React 迁移验证文献',
  authors: 'Ada Lovelace',
  journal: 'Knowledge Systems',
  journal_id: 1,
  year: 2026,
  issue: '3',
  abstract: '用于验证列表、详情和编辑流程。',
  keywords: 'React, TypeScript',
  language: 'zh',
  literature_type: 'journal',
  status: '已读完',
  created_at: '2026-09-05T08:00:00Z',
  tags: [{ id: 1, name: '前端', color: '#2563eb' }],
  folder_ids: [1],
  collection_sources: [{ id: 1, raw_paper_id: 1, source_type: 'magtech' }],
}

const sampleIssue = {
  id: 1,
  journal_name: '情报学报',
  source_type: 'magtech',
  region: 'domestic',
  year: 2026,
  issue: '3',
  volume: '45',
  source_url: 'https://example.com/issue',
  paper_count: 1,
  expected_paper_count: 2,
  title_collected_count: 1,
  abstract_collected_count: 1,
  fulltext_collected_count: 1,
  translation_status: 'completed',
  analysis_status: 'completed',
  papers: [
    {
      id: 1,
      title: 'Knowledge Graph Study',
      title_zh: '知识图谱研究',
      authors: '研究者',
      abstract: 'Abstract',
      abstract_zh: '摘要',
      pages: '1-10',
      detail_url: 'https://example.com/paper',
      literature_id: 1,
      pdf_path: 'uploads/pdfs/1.pdf',
    },
  ],
}

const sampleVideoTask = {
  id: 1,
  source_url: 'https://www.bilibili.com/video/BV1TEST',
  bvid: 'BV1TEST',
  video_title: '视频任务验证',
  status: 'completed',
  current_step: 'done',
  progress_message: '处理完成',
  updated_at: '2026-09-05T08:30:00Z',
  transcript_content: '1\n00:00:00,000 --> 00:00:02,000\n测试字幕',
  note_content: '# 测试笔记\n\n迁移验证完成。',
  transcript_path: 'backend/data/artifacts/video/1/transcript.srt',
  note_path: 'backend/data/artifacts/video/1/note.md',
}

interface MockModelProfile {
  id: number
  name: string
  protocol: string
  base_url: string | null
  model_name: string
  enabled: boolean
  has_api_key: boolean
  last_check_status?: string
}

interface MockAnalysis {
  id: number
  title: string
  status: string
  profile_id: number
  model_name: string
  paper_count: number
  content_markdown: string | null
  created_at: string
  items: Array<{ id: number; literature_id: number; title: string }>
}

function envelope(data: unknown) {
  return JSON.stringify({ code: 200, data, message: 'ok' })
}

function pendingFulltextTask(id: number, mode: 'single' | 'issue' | 'after_ingestion') {
  return {
    id,
    mode,
    source_type: 'magtech',
    raw_issue_id: 1,
    status: 'pending',
    replace_existing: false,
    total_count: 1,
    succeeded_count: 0,
    failed_count: 0,
    skipped_count: 0,
    progress_message: '等待下载',
    items: [
      {
        id,
        literature_id: 1,
        literature_title: sampleLiterature.title,
        raw_paper_id: 1,
        source_type: 'magtech',
        status: 'pending',
      },
    ],
  }
}

async function installApiMocks(page: Page) {
  let literature = { ...sampleLiterature }
  let literatureFulltextTasks: ReturnType<typeof pendingFulltextTask>[] = []
  let issueFulltextTasks: ReturnType<typeof pendingFulltextTask>[] = []
  let modelProfiles: MockModelProfile[] = [
    {
      id: 1,
      name: 'Gemini 论文工作',
      protocol: 'gemini',
      base_url: null,
      model_name: 'gemini-test',
      enabled: true,
      has_api_key: true,
      last_check_status: 'ok',
    },
  ]
  let analyses: MockAnalysis[] = [
    {
      id: 1,
      title: '既有分析',
      status: 'completed',
      profile_id: 1,
      model_name: 'gemini-test',
      paper_count: 1,
      content_markdown: '# 分析结论\n\n已有内容。',
      created_at: '2026-09-07T08:00:00Z',
      items: [{ id: 1, literature_id: 1, title: sampleLiterature.title }],
    },
  ]

  await page.route(/^https?:\/\/[^/]+\/api\/.*/, async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname
    const method = request.method()
    let data: unknown

    if (path === '/api/literatures/statistics') {
      data = {
        total: 1,
        by_status: { 已读完: 1 },
        by_language: { zh: 1, en: 0 },
        monthly: [{ month: '2026-09', count: 1 }],
      }
    } else if (path === '/api/literatures' && method === 'GET') {
      data = { items: [literature], total: 1, page: 1, per_page: 10 }
    } else if (path === '/api/literatures' && method === 'POST') {
      const payload = request.postDataJSON() as Record<string, unknown>
      literature = { ...literature, ...payload, id: 1 }
      data = literature
    } else if (path === '/api/literatures/1/fulltext-tasks' && method === 'POST') {
      const task = pendingFulltextTask(101, 'single')
      literatureFulltextTasks = [task]
      data = task
    } else if (path === '/api/literatures/1') {
      data = literature
    } else if (path === '/api/fulltext-tasks') {
      data = url.searchParams.has('literature_id') ? literatureFulltextTasks : issueFulltextTasks
    } else if (path === '/api/tags') {
      data = [{ tag: { id: 1, name: '前端', color: '#2563eb' }, literature_count: 1 }]
    } else if (path === '/api/folders') {
      data = [{ id: 1, name: '技术研究', parent_id: null, children: [] }]
    } else if (path === '/api/notes') {
      data = [
        {
          id: 1,
          literature_id: 1,
          type: 'idea',
          title: '迁移笔记',
          content: '验证笔记展示。',
          created_at: '2026-09-05T08:10:00Z',
        },
      ]
    } else if (path === '/api/collection/sources') {
      data = [
        {
          source_id: 'magtech',
          display_name: 'Magtech',
          region: 'domestic',
          capabilities: { list_issues: true, download_pdf: true, needs_browser: false },
          config_fields: [],
        },
      ]
    } else if (path === '/api/journals') {
      data = [
        {
          id: 1,
          name: '情报学报',
          issn: '1000-0135',
          publisher: '测试出版方',
          region: 'domestic',
          sources: [{ source_id: 'magtech', enabled: true, is_default: true }],
          stats: { issue_count: 1, last_collected_at: '2026-09-05T08:00:00Z' },
        },
      ]
    } else if (path === '/api/crawl-tasks' && method === 'POST') {
      const task = pendingFulltextTask(103, 'after_ingestion')
      issueFulltextTasks = [task]
      data = {
        task: {
          id: 2,
          journal_name: '情报学报',
          source_type: 'magtech',
          year: 2026,
          issue: '3',
          status: 'completed',
        },
        raw_issue: sampleIssue,
        fulltext_task: task,
      }
    } else if (path === '/api/crawl-tasks') {
      data = [
        {
          id: 1,
          journal_name: '情报学报',
          source_type: 'magtech',
          year: 2026,
          issue: '3',
          status: 'completed',
          created_at: '2026-09-05T08:00:00Z',
        },
      ]
    } else if (path === '/api/raw-issues') {
      data = { items: [sampleIssue], total: 1, page: 1, per_page: 20 }
    } else if (path === '/api/raw-issues/1/fulltext-tasks' && method === 'POST') {
      const task = pendingFulltextTask(102, 'issue')
      issueFulltextTasks = [task]
      data = task
    } else if (path === '/api/raw-issues/1') {
      data = sampleIssue
    } else if (path === '/api/llm/profiles' && method === 'GET') {
      data = modelProfiles
    } else if (path === '/api/llm/profiles' && method === 'POST') {
      const payload = request.postDataJSON() as Record<string, unknown>
      const created = {
        id: 2,
        name: String(payload.name),
        protocol: String(payload.protocol),
        base_url: String(payload.base_url),
        model_name: String(payload.model_name),
        enabled: true,
        has_api_key: true,
      }
      modelProfiles = [...modelProfiles, created]
      data = created
    } else if (path === '/api/llm/scenes' && method === 'GET') {
      data = [
        { scene: 'paper_analysis', label: '论文分析', profile_id: 1, model_name: 'gemini-test' },
        { scene: 'paper_translation', label: '论文翻译', profile_id: 1, model_name: 'gemini-test' },
        { scene: 'video_note', label: '视频笔记', profile_id: 1, model_name: 'gemini-test' },
      ]
    } else if (path === '/api/paper-analyses/issues') {
      data = [
        { journal_id: 1, journal: 'Knowledge Systems', year: 2026, issue: '3', paper_count: 1 },
      ]
    } else if (path === '/api/paper-analyses/selection-preview') {
      data = [literature]
    } else if (path === '/api/paper-analyses' && method === 'POST') {
      const created = {
        ...analyses[0],
        id: 2,
        title: '新分析',
        status: 'queued',
        content_markdown: null,
        created_at: '2026-09-07T09:00:00Z',
      }
      analyses = [created, ...analyses]
      data = created
    } else if (path === '/api/paper-analyses' && method === 'GET') {
      data = { items: analyses, total: analyses.length, page: 1, per_page: 20 }
    } else if (/^\/api\/paper-analyses\/\d+$/.test(path)) {
      data = analyses.find((item) => item.id === Number(path.split('/').pop())) || null
    } else if (path === '/api/video-note-tasks') {
      data = [sampleVideoTask]
    } else if (path === '/api/video-note-tasks/1/logs') {
      data = [{ id: 1, level: 'info', message: '任务完成', created_at: '2026-09-05T08:30:00Z' }]
    } else if (path === '/api/video-note-tasks/1') {
      data = sampleVideoTask
    } else {
      data = null
    }

    await route.fulfill({ status: 200, contentType: 'application/json', body: envelope(data) })
  })
}

function trackBrowserErrors(page: Page) {
  const errors: string[] = []
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text())
  })
  page.on('pageerror', (error) => errors.push(error.message))
  page.on('requestfailed', (request) =>
    errors.push(request.url() + ': ' + (request.failure()?.errorText || 'request failed')),
  )
  return errors
}

const routes = [
  ['/', '文献工作台'],
  ['/literatures', '文献列表'],
  ['/literatures/new', '添加文献'],
  ['/literatures/1', 'React 迁移验证文献'],
  ['/literatures/1/edit', '编辑文献'],
  ['/paper-analysis', '论文分析'],
  ['/tags', '标签管理'],
  ['/folders', '文件夹管理'],
  ['/statistics', '统计分析'],
  ['/import', '导入文献'],
  ['/backup', '备份与恢复'],
  ['/crawler/journals', '期刊与采集源'],
  ['/crawler/tasks', '采集任务台'],
  ['/crawler/issues', '采集期号库'],
  ['/crawler/issues/1', '情报学报'],
  ['/video-notes', '视频转笔记'],
  ['/video-notes/tasks', '视频任务列表'],
  ['/video-notes/tasks/1', '视频任务验证'],
  ['/settings/models', '模型配置'],
] as const

test.beforeEach(async ({ page }) => {
  await installApiMocks(page)
})

test('全部路由都能渲染且没有浏览器错误', async ({ page }) => {
  const errors = trackBrowserErrors(page)

  for (const [path, title] of routes) {
    await page.goto(path)
    await expect(page.getByRole('heading', { level: 1, name: title })).toBeVisible()
  }

  expect(errors).toEqual([])
})

test('文献导航、筛选和详情跳转保持可用', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('link', { name: '文献列表' }).click()
  await expect(page.getByRole('heading', { level: 1, name: '文献列表' })).toBeVisible()

  await page.getByLabel('标题').fill('React')
  await page.getByLabel('状态').selectOption('已读完')
  const filteredRequest = page.waitForRequest((request) => {
    const url = new URL(request.url())
    return url.pathname === '/api/literatures' && url.searchParams.get('title') === 'React'
  })
  await page.getByRole('button', { name: '应用筛选' }).click()
  const url = new URL((await filteredRequest).url())
  expect(url.searchParams.get('status')).toBe('已读完')

  await page.getByRole('link', { name: 'React 迁移验证文献' }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'React 迁移验证文献' })).toBeVisible()
  await page.getByRole('link', { name: '编辑' }).click()
  await expect(page.getByRole('heading', { level: 1, name: '编辑文献' })).toBeVisible()
})

test('文献表单先校验再创建并进入详情', async ({ page }) => {
  await page.goto('/literatures/new')
  await page.getByRole('button', { name: '建立档案' }).click()
  await expect(page.getByText('请输入文献标题')).toBeVisible()
  await expect(page.getByText('请填写至少一名作者')).toBeVisible()

  await page.getByLabel('文献标题').fill('新建测试文献')
  await page.getByLabel('作者').fill('测试作者')
  await page.getByRole('button', { name: '建立档案' }).click()
  await expect(page.getByRole('heading', { level: 1, name: '新建测试文献' })).toBeVisible()
})

test('文献和期号入口可以分别发起官网全文采集', async ({ page }) => {
  await page.goto('/literatures/1')
  const singleRequest = page.waitForRequest(
    (request) =>
      new URL(request.url()).pathname === '/api/literatures/1/fulltext-tasks' &&
      request.method() === 'POST',
  )
  await page.getByRole('button', { name: '从官网下载' }).click()
  expect((await singleRequest).postDataJSON()).toEqual({ replace_existing: false })
  await expect(page.getByRole('button', { name: '下载中' })).toBeDisabled()

  await page.goto('/crawler/issues/1')
  const issueRequest = page.waitForRequest(
    (request) =>
      new URL(request.url()).pathname === '/api/raw-issues/1/fulltext-tasks' &&
      request.method() === 'POST',
  )
  await page.getByRole('button', { name: '补采本期全文' }).click()
  await issueRequest
  await expect(page.getByRole('button', { name: '全文下载中' })).toBeDisabled()
})

test('题录采集可以选择完成后补采全文', async ({ page }) => {
  await page.goto('/crawler/tasks')
  await page.getByLabel('期刊').selectOption('情报学报')
  await page.getByLabel('采集源').selectOption('magtech')
  await page.getByLabel('期号').fill('3')
  await page.getByRole('checkbox', { name: '题录完成后补采全文' }).check()
  const requestPromise = page.waitForRequest(
    (request) =>
      new URL(request.url()).pathname === '/api/crawl-tasks' && request.method() === 'POST',
  )

  await page.getByRole('button', { name: '发起采集' }).click()
  const payload = (await requestPromise).postDataJSON()
  expect(payload.download_fulltext).toBe(true)
})

test('模型配置可以新增 OpenAI Compatible 档案且不回显密钥', async ({ page }) => {
  await page.goto('/settings/models')
  await page.getByRole('button', { name: '新增模型' }).click()
  await page.getByLabel('显示名称').fill('本地模型')
  await page.getByLabel('协议').selectOption('openai')
  await page.getByLabel('Base URL').fill('http://127.0.0.1:11434/v1')
  await page.getByLabel('模型名称').fill('qwen-test')
  await page.getByLabel('API Key').fill('browser-test-secret')
  const requestPromise = page.waitForRequest(
    (request) =>
      new URL(request.url()).pathname === '/api/llm/profiles' && request.method() === 'POST',
  )
  await page.getByRole('button', { name: '保存', exact: true }).click()
  const payload = (await requestPromise).postDataJSON()
  expect(payload).toMatchObject({
    protocol: 'openai',
    base_url: 'http://127.0.0.1:11434/v1',
    model_name: 'qwen-test',
    api_key: 'browser-test-secret',
  })
  await expect(page.getByText('本地模型', { exact: true })).toBeVisible()
  await expect(page.getByText('browser-test-secret')).toHaveCount(0)
})

test('论文分析可以按期号选择并创建任务', async ({ page }) => {
  await page.goto('/paper-analysis')
  await page.getByRole('checkbox', { name: /Knowledge Systems/ }).check()
  await expect(page.locator('.selection-count')).toHaveText('1')
  const requestPromise = page.waitForRequest(
    (request) =>
      new URL(request.url()).pathname === '/api/paper-analyses' && request.method() === 'POST',
  )
  await page.getByRole('button', { name: '开始分析' }).click()
  const payload = (await requestPromise).postDataJSON()
  expect(payload.issues).toHaveLength(1)
  expect(payload.profile_id).toBeUndefined()
})

test('期刊页不再暴露内置清单，期号详情提供独立分析入口', async ({ page }) => {
  await page.goto('/crawler/journals')
  await expect(page.getByRole('button', { name: '导入内置清单' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: '配置' })).toHaveClass(/button--secondary/)
  await expect(page.getByRole('button', { name: '去采集' })).toHaveClass(/button--secondary/)
  await expect(page.getByRole('button', { name: '删除 情报学报' })).toHaveClass(/button--danger/)

  await page.goto('/crawler/issues')
  await expect(page.getByText('应有 2 篇')).toBeVisible()
  await expect(page.getByText('1/2', { exact: true })).toHaveCount(3)
  await expect(page.getByLabel('标题已采集 1 篇，应有 2 篇')).toBeVisible()
  await expect(page.getByLabel('摘要已采集 1 篇，应有 2 篇')).toBeVisible()
  await expect(page.getByLabel('全文已采集 1 篇，应有 2 篇')).toBeVisible()
  await expect(page.locator('.issue-coverage__item--title .issue-coverage__fill')).toHaveAttribute(
    'style',
    'width: 50%;',
  )
  await expect(page.getByText('翻译：不需要')).toHaveCount(0)
  await expect(page.getByRole('link', { name: '查看详情' })).toHaveText('查看详情')
  await expect(page.getByRole('main').getByRole('link', { name: '论文分析' })).toHaveClass(
    /button--secondary/,
  )
  await expect(page.getByRole('link', { name: '分析本期' })).toHaveClass(/button--secondary/)

  await page.goto('/crawler/issues/1')
  await expect(page.getByRole('link', { name: '分析本期' })).toHaveAttribute(
    'href',
    /paper-analysis/,
  )
  await expect(page.getByRole('link', { name: '分析本期' })).toHaveClass(/button--secondary/)
  await expect(page.getByRole('button', { name: '补采本期全文' })).toHaveClass(/button--secondary/)
  await page.locator('.paper-item summary').click()
  await expect(page.getByRole('link', { name: '打开期刊原文页' })).toHaveAttribute(
    'href',
    'https://example.com/paper',
  )
  await expect(page.getByRole('link', { name: '阅读全文 PDF' })).toHaveAttribute(
    'href',
    '/uploads/pdfs/1.pdf',
  )
  await expect(page.getByText('打开论文页面')).toHaveCount(0)
  await expect(page.getByRole('button', { name: '生成分析' })).toHaveCount(0)
})

test('移动端布局不产生页面级横向溢出', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/literatures')
  await expect(page.getByRole('heading', { level: 1, name: '文献列表' })).toBeVisible()
  let overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
  )
  expect(overflow).toBe(false)

  await page.goto('/settings/models')
  await expect(page.getByRole('heading', { level: 1, name: '模型配置' })).toBeVisible()
  const editButton = page.getByRole('button', { name: /编辑/ }).first()
  await expect(editButton).toBeVisible()
  const editButtonBox = await editButton.boundingBox()
  expect(editButtonBox).not.toBeNull()
  expect(editButtonBox!.x).toBeGreaterThanOrEqual(0)
  expect(editButtonBox!.x + editButtonBox!.width).toBeLessThanOrEqual(390)
  overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
  )
  expect(overflow).toBe(false)
})
