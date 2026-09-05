import { expect, test, type Page } from '@playwright/test'

const sampleLiterature = {
  id: 1,
  title: 'React 迁移验证文献',
  authors: 'Ada Lovelace',
  journal: 'Knowledge Systems',
  year: 2026,
  abstract: '用于验证列表、详情和编辑流程。',
  keywords: 'React, TypeScript',
  language: 'zh',
  literature_type: 'journal',
  status: '已读完',
  created_at: '2026-09-05T08:00:00Z',
  tags: [{ id: 1, name: '前端', color: '#2563eb' }],
  folder_ids: [1],
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

function envelope(data: unknown) {
  return JSON.stringify({ code: 200, data, message: 'ok' })
}

async function installApiMocks(page: Page) {
  let literature = { ...sampleLiterature }

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
    } else if (path === '/api/literatures/1') {
      data = literature
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
          capabilities: { list_issues: true, needs_browser: false },
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
    } else if (path === '/api/raw-issues/1/analysis') {
      data = { id: 1, status: 'completed', content_markdown: '# 分析结论\n\n内容安全可渲染。' }
    } else if (path === '/api/raw-issues/1') {
      data = sampleIssue
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

test('移动端布局不产生页面级横向溢出', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/literatures')
  await expect(page.getByRole('heading', { level: 1, name: '文献列表' })).toBeVisible()
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
  )
  expect(overflow).toBe(false)
})
