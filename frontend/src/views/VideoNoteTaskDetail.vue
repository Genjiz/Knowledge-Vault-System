<template>
  <section v-loading="videoNotesStore.loading" class="space-y-6">
    <el-alert v-if="loadError" type="error" show-icon :closable="false" :title="loadError" class="rounded-2xl" />

    <header
      class="rounded-[28px] border border-slate-200/70 bg-[radial-gradient(circle_at_top_left,_rgba(14,165,233,0.12),_transparent_24%),linear-gradient(135deg,_rgba(255,255,255,0.98),_rgba(241,245,249,0.94))] px-8 py-8 shadow-[0_30px_80px_-36px_rgba(15,23,42,0.3)]"
    >
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div class="space-y-3">
          <p class="text-xs uppercase tracking-[0.4em] text-slate-500">Task Detail</p>
          <h2 class="text-3xl font-black tracking-tight text-slate-950">{{ taskTitle }}</h2>
          <div class="text-sm text-slate-500">{{ task?.bvid || '--' }}</div>
          <div class="max-w-3xl break-all text-sm leading-7 text-slate-600">{{ task?.source_url || '--' }}</div>
        </div>
        <div class="flex flex-wrap items-center gap-3">
          <el-tag :type="statusType(task?.status)" effect="dark" round>{{ statusLabel(task?.status) }}</el-tag>
          <el-button text @click="$router.push('/video-notes/tasks')">返回列表</el-button>
        </div>
      </div>
    </header>

    <div class="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
      <div class="space-y-6">
        <el-card class="rounded-[28px] border border-slate-200/70 !shadow-[0_24px_64px_-36px_rgba(15,23,42,0.28)]">
          <template #header>
            <div>
              <div class="text-xs uppercase tracking-[0.35em] text-slate-400">Execution</div>
              <div class="mt-1 text-xl font-bold text-slate-900">执行状态</div>
            </div>
          </template>

          <div class="space-y-4">
            <div class="rounded-2xl border border-slate-200 bg-slate-50/80 p-4 text-sm text-slate-600">
              <div><span class="font-semibold text-slate-900">当前步骤：</span>{{ stepLabel(task?.current_step) }}</div>
              <div class="mt-2"><span class="font-semibold text-slate-900">进度说明：</span>{{ task?.progress_message || '等待开始' }}</div>
              <div v-if="task?.error_message" class="mt-2 text-rose-600">{{ task.error_message }}</div>
            </div>

            <el-steps :active="stepIndex(task?.current_step)" finish-status="success" align-center>
              <el-step title="下载音频" />
              <el-step title="转写字幕" />
              <el-step title="生成笔记" />
            </el-steps>
          </div>
        </el-card>

        <el-card class="rounded-[28px] border border-slate-200/70 !shadow-[0_24px_64px_-36px_rgba(15,23,42,0.28)]">
          <template #header>
            <div>
              <div class="text-xs uppercase tracking-[0.35em] text-slate-400">Artifacts</div>
              <div class="mt-1 text-xl font-bold text-slate-900">任务产物</div>
            </div>
          </template>

          <el-descriptions :column="1" border>
            <el-descriptions-item label="音频路径">{{ task?.audio_path || '--' }}</el-descriptions-item>
            <el-descriptions-item label="字幕路径">{{ task?.transcript_path || '--' }}</el-descriptions-item>
            <el-descriptions-item label="笔记路径">{{ task?.note_path || '--' }}</el-descriptions-item>
            <el-descriptions-item label="元数据路径">{{ task?.metadata_path || '--' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card class="rounded-[28px] border border-slate-200/70 !shadow-[0_24px_64px_-36px_rgba(15,23,42,0.28)]">
          <template #header>
            <div>
              <div class="text-xs uppercase tracking-[0.35em] text-slate-400">Logs</div>
              <div class="mt-1 text-xl font-bold text-slate-900">日志时间线</div>
            </div>
          </template>

          <el-timeline>
            <el-timeline-item
              v-for="log in logs"
              :key="log.id"
              :type="log.level === 'error' ? 'danger' : 'primary'"
              :timestamp="formatDate(log.created_at)"
            >
              {{ log.message }}
            </el-timeline-item>
          </el-timeline>
          <el-empty v-if="!logs.length" description="还没有任务日志" />
        </el-card>
      </div>

      <div class="space-y-6">
        <el-card class="rounded-[28px] border border-slate-200/70 !shadow-[0_24px_64px_-36px_rgba(15,23,42,0.28)]">
          <template #header>
            <div class="flex items-center justify-between">
              <div>
                <div class="text-xs uppercase tracking-[0.35em] text-slate-400">Transcript</div>
                <div class="mt-1 text-xl font-bold text-slate-900">SRT 预览</div>
              </div>
              <el-button text :disabled="!task?.transcript_content" @click="copyText(task?.transcript_content, '字幕内容已复制')">
                复制字幕
              </el-button>
            </div>
          </template>

          <pre class="max-h-[360px] overflow-auto rounded-2xl bg-slate-950 p-5 text-xs leading-6 text-slate-100">{{ task?.transcript_content || '字幕尚未生成' }}</pre>
        </el-card>

        <el-card class="rounded-[28px] border border-slate-200/70 !shadow-[0_24px_64px_-36px_rgba(15,23,42,0.28)]">
          <template #header>
            <div class="flex items-center justify-between">
              <div>
                <div class="text-xs uppercase tracking-[0.35em] text-slate-400">Final Note</div>
                <div class="mt-1 text-xl font-bold text-slate-900">Markdown 笔记</div>
              </div>
              <div class="flex items-center gap-2">
                <el-button text :disabled="!task?.note_content" @click="copyText(task?.note_content, '笔记内容已复制')">复制笔记</el-button>
                <el-button text :disabled="!task?.note_content" @click="downloadNote">下载 Markdown</el-button>
              </div>
            </div>
          </template>

          <pre class="max-h-[560px] overflow-auto rounded-2xl bg-white p-5 text-sm leading-7 text-slate-700 shadow-inner">{{ task?.note_content || '笔记尚未生成' }}</pre>
        </el-card>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute } from 'vue-router'
import { useVideoNotesStore } from '@/stores/videoNotes'

const route = useRoute()
const videoNotesStore = useVideoNotesStore()
const loadError = ref('')
let timerId = null

const task = computed(() => videoNotesStore.currentTask)
const logs = computed(() => videoNotesStore.currentLogs)
const taskTitle = computed(() => task.value?.video_title || task.value?.bvid || `任务 #${route.params.id}`)

function statusType(status) {
  if (status === 'completed') return 'success'
  if (status === 'running') return 'warning'
  if (status === 'failed') return 'danger'
  return 'info'
}

function statusLabel(status) {
  return (
    {
      pending: '待执行',
      running: '运行中',
      completed: '已完成',
      failed: '失败'
    }[status] || status || '未知'
  )
}

function stepLabel(step) {
  return (
    {
      download_audio: '下载音频',
      transcribe_srt: '转写字幕',
      generate_note: '生成笔记',
      done: '已完成'
    }[step] || '等待开始'
  )
}

function stepIndex(step) {
  return (
    {
      download_audio: 1,
      transcribe_srt: 2,
      generate_note: 3,
      done: 3
    }[step] || 0
  )
}

function formatDate(value) {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

async function loadDetail() {
  loadError.value = ''
  try {
    await Promise.all([
      videoNotesStore.fetchTask(route.params.id),
      videoNotesStore.fetchTaskLogs(route.params.id)
    ])
  } catch (error) {
    loadError.value = '视频任务详情加载失败，请稍后重试。'
  }
}

async function copyText(text, message) {
  if (!text) return
  await navigator.clipboard.writeText(text)
  ElMessage.success(message)
}

function downloadNote() {
  if (!task.value?.note_content) return
  const blob = new Blob([task.value.note_content], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${task.value.bvid || `video-note-${route.params.id}`}.md`
  link.click()
  URL.revokeObjectURL(url)
}

function shouldPoll(currentTask) {
  return currentTask && ['pending', 'running'].includes(currentTask.status)
}

onMounted(async () => {
  await loadDetail()
  timerId = window.setInterval(() => {
    if (shouldPoll(task.value)) loadDetail().catch(() => {})
  }, 5000)
})

onUnmounted(() => {
  if (timerId) window.clearInterval(timerId)
})
</script>
