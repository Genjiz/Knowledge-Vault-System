// 该文件是从主项目共享 E2E 测试中抽出的非执行片段。
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

const videoApiMocks = {
  'POST /api/video-note-tasks': {
    ...sampleVideoTask,
    profile_id: 1,
    model_name: 'gemini-test',
  },
  'GET /api/video-note-tasks': [sampleVideoTask],
  'GET /api/video-note-tasks/1/logs': [
    { id: 1, level: 'info', message: '任务完成', created_at: '2026-09-05T08:30:00Z' },
  ],
  'GET /api/video-note-tasks/1': sampleVideoTask,
}

const videoRoutes = [
  ['/video-notes', '视频转笔记'],
  ['/video-notes/tasks', '视频任务列表'],
  ['/video-notes/tasks/1', '视频任务验证'],
]

async function videoTaskModelSelectionTest(page: any, expect: any) {
  await page.goto('/video-notes')
  await page.getByLabel('B 站视频链接').fill('https://www.bilibili.com/video/BV1TEST')
  await expect(page.getByRole('button', { name: '创建任务' })).toBeDisabled()
  await page.getByLabel('笔记生成模型').selectOption('1')
  const requestPromise = page.waitForRequest(
    (request: any) =>
      new URL(request.url()).pathname === '/api/video-note-tasks' && request.method() === 'POST',
  )
  await page.getByRole('button', { name: '创建任务' }).click()
  expect((await requestPromise).postDataJSON()).toMatchObject({ profile_id: 1 })
}
