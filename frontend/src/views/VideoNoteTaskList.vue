<template>
  <section v-loading="videoNotesStore.loading" class="space-y-6">
    <header
      class="rounded-[28px] border border-slate-200/70 bg-[linear-gradient(135deg,_rgba(255,255,255,0.98),_rgba(241,245,249,0.94))] px-8 py-8 shadow-[0_30px_80px_-36px_rgba(15,23,42,0.3)]"
    >
      <div class="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p class="text-xs uppercase tracking-[0.4em] text-slate-500">Task Ledger</p>
          <h2 class="mt-2 text-4xl font-black tracking-tight text-slate-950">视频任务列表</h2>
          <p class="mt-2 text-sm leading-7 text-slate-600">查看每个视频任务当前执行到哪一步，以及最终是否成功生成笔记。</p>
        </div>
        <el-button
          type="primary"
          class="rounded-2xl border-0 bg-slate-950 px-5 py-3 text-white shadow-[0_18px_50px_-22px_rgba(15,23,42,0.7)] hover:bg-slate-800"
          @click="$router.push('/video-notes')"
        >
          新建任务
        </el-button>
      </div>
    </header>

    <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <el-card
        v-for="task in tasks"
        :key="task.id"
        class="rounded-[26px] border border-slate-200/70 !shadow-[0_24px_64px_-36px_rgba(15,23,42,0.28)]"
      >
        <div class="space-y-4">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <div class="truncate text-lg font-bold text-slate-900">{{ task.video_title || task.bvid }}</div>
              <div class="mt-1 text-xs uppercase tracking-[0.25em] text-slate-400">{{ task.bvid }}</div>
            </div>
            <el-tag :type="statusType(task.status)" effect="dark" round>{{ statusLabel(task.status) }}</el-tag>
          </div>

          <div class="rounded-2xl bg-slate-50/80 px-4 py-3 text-sm text-slate-600">
            <div><span class="font-semibold text-slate-900">步骤：</span>{{ stepLabel(task.current_step) }}</div>
            <div class="mt-2 line-clamp-2 break-all"><span class="font-semibold text-slate-900">链接：</span>{{ task.source_url }}</div>
            <div v-if="task.error_message" class="mt-2 text-rose-600">{{ task.error_message }}</div>
          </div>

          <div class="flex items-center justify-between">
            <div class="text-xs text-slate-400">更新时间 {{ formatDate(task.updated_at) }}</div>
            <el-button text @click="$router.push(`/video-notes/tasks/${task.id}`)">查看详情</el-button>
          </div>
        </div>
      </el-card>
    </div>

    <el-empty v-if="!tasks.length" description="还没有视频任务" />
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useVideoNotesStore } from '@/stores/videoNotes'

const videoNotesStore = useVideoNotesStore()
let timerId = null

const tasks = computed(() => videoNotesStore.tasks)

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

function formatDate(value) {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

async function loadTasks() {
  await videoNotesStore.fetchTasks()
}

onMounted(() => {
  loadTasks().catch(() => {})
  timerId = window.setInterval(() => {
    loadTasks().catch(() => {})
  }, 5000)
})

onUnmounted(() => {
  if (timerId) window.clearInterval(timerId)
})
</script>
