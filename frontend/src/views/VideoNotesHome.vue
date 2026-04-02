<template>
  <section v-loading="videoNotesStore.loading" class="space-y-6">
    <header
      class="relative overflow-hidden rounded-[28px] border border-slate-200/70 bg-[radial-gradient(circle_at_top_left,_rgba(244,114,182,0.14),_transparent_28%),radial-gradient(circle_at_bottom_right,_rgba(56,189,248,0.12),_transparent_24%),linear-gradient(135deg,_rgba(255,255,255,0.98),_rgba(241,245,249,0.94))] px-8 py-8 shadow-[0_30px_80px_-36px_rgba(15,23,42,0.3)]"
    >
      <div class="absolute inset-y-0 right-0 w-56 bg-[linear-gradient(135deg,transparent,rgba(15,23,42,0.08))]" />
      <div class="relative flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div class="max-w-3xl space-y-3">
          <p class="text-xs uppercase tracking-[0.4em] text-slate-500">Media Notes Lab</p>
          <h2 class="text-4xl font-black tracking-tight text-slate-950">视频转笔记</h2>
          <p class="text-sm leading-7 text-slate-600">
            输入 B 站视频链接，系统会自动执行音频下载、Whisper 字幕转写和 Gemini 笔记生成，并把中间产物保存在项目里。
          </p>
        </div>
        <div class="grid grid-cols-2 gap-3 rounded-[24px] border border-white/70 bg-white/70 p-4 backdrop-blur">
          <div>
            <div class="text-xs uppercase tracking-[0.3em] text-slate-400">任务数</div>
            <div class="mt-1 text-2xl font-bold text-slate-900">{{ recentTasks.length }}</div>
          </div>
          <div>
            <div class="text-xs uppercase tracking-[0.3em] text-slate-400">默认流程</div>
            <div class="mt-1 text-sm font-semibold text-slate-900">yt-dlp → Whisper → Gemini</div>
          </div>
        </div>
      </div>
    </header>

    <div class="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
      <el-card class="rounded-[28px] border border-slate-200/70 !shadow-[0_24px_64px_-36px_rgba(15,23,42,0.28)]">
        <template #header>
          <div class="flex items-center justify-between">
            <div>
              <div class="text-xs uppercase tracking-[0.35em] text-slate-400">Launch</div>
              <div class="mt-1 text-xl font-bold text-slate-900">新建视频任务</div>
            </div>
            <el-tag round effect="dark" type="danger">后台任务</el-tag>
          </div>
        </template>

        <el-form label-position="top" :model="form" class="space-y-4">
          <el-form-item label="B 站视频链接">
            <el-input
              v-model="form.source_url"
              size="large"
              placeholder="https://www.bilibili.com/video/BVxxxxxxxxxxx/"
              clearable
            />
          </el-form-item>

          <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
            <el-form-item label="Whisper 模型">
              <el-select v-model="form.whisper_model" class="w-full">
                <el-option label="large-v3-turbo" value="large-v3-turbo" />
                <el-option label="large-v3" value="large-v3" />
                <el-option label="medium" value="medium" />
                <el-option label="small" value="small" />
              </el-select>
            </el-form-item>

            <el-form-item label="语言">
              <el-select v-model="form.language" class="w-full">
                <el-option label="中文" value="zh" />
                <el-option label="英文" value="en" />
                <el-option label="自动识别" value="auto" />
              </el-select>
            </el-form-item>
          </div>

          <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
            <el-form-item label="设备">
              <el-select v-model="form.device" class="w-full">
                <el-option label="cuda" value="cuda" />
                <el-option label="cpu" value="cpu" />
              </el-select>
            </el-form-item>

            <el-form-item label="计算精度">
              <el-select v-model="form.compute_type" class="w-full">
                <el-option label="int8_float16" value="int8_float16" />
                <el-option label="float16" value="float16" />
                <el-option label="int8" value="int8" />
              </el-select>
            </el-form-item>

            <el-form-item label="VAD 过滤">
              <div class="flex h-10 items-center">
                <el-switch v-model="form.use_vad" inline-prompt active-text="开" inactive-text="关" />
              </div>
            </el-form-item>
          </div>

          <el-form-item class="!mb-0">
            <el-button
              type="primary"
              size="large"
              class="w-full rounded-2xl border-0 bg-slate-950 text-white shadow-[0_18px_50px_-22px_rgba(15,23,42,0.7)] hover:bg-slate-800"
              :loading="videoNotesStore.submitting"
              @click="submitTask"
            >
              创建任务
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <div class="space-y-6">
        <el-card class="rounded-[28px] border border-slate-200/70 !shadow-[0_24px_64px_-36px_rgba(15,23,42,0.28)]">
          <template #header>
            <div>
              <div class="text-xs uppercase tracking-[0.35em] text-slate-400">Preparation</div>
              <div class="mt-1 text-xl font-bold text-slate-900">前期准备</div>
            </div>
          </template>

          <div class="space-y-4 text-sm leading-7 text-slate-600">
            <article class="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
              <div class="font-semibold text-slate-900">1. 必备工具</div>
              <p class="mt-2">请确认本机已经安装 FFmpeg、<code>yt-dlp</code>，以及名为 <code>whisper</code> 的 conda 环境。</p>
            </article>
            <article class="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
              <div class="font-semibold text-slate-900">2. 转写环境</div>
              <p class="mt-2">首次运行 faster-whisper 可能需要下载模型；如果网络受限，请先配置代理后再发起任务。</p>
            </article>
            <article class="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
              <div class="font-semibold text-slate-900">3. Gemini 配置</div>
              <p class="mt-2">最终笔记由 Gemini 生成。请确保 <code>GEMINI_API_KEY</code> 或 <code>backend/gemini_api_key.txt</code> 已可用。</p>
              <p class="mt-2">如果当前机器无法访问 <code>generativelanguage.googleapis.com:443</code>，请在仓库根目录的 <code>.env</code> 中配置 <code>GEMINI_PROXY_URL=http://127.0.0.1:7890</code>。</p>
            </article>
            <article class="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
              <div class="font-semibold text-slate-900">4. 产物位置</div>
              <p class="mt-2">任务运行后，音频、SRT、Markdown 和元数据会保存在 <code>backend/artifacts/video-notes/&lt;task_id&gt;/</code> 下。</p>
            </article>
          </div>
        </el-card>

        <el-card class="rounded-[28px] border border-slate-200/70 !shadow-[0_24px_64px_-36px_rgba(15,23,42,0.28)]">
          <template #header>
            <div class="flex items-center justify-between">
              <div>
                <div class="text-xs uppercase tracking-[0.35em] text-slate-400">Recent Activity</div>
                <div class="mt-1 text-xl font-bold text-slate-900">最近任务</div>
              </div>
              <el-button text @click="$router.push('/video-notes/tasks')">查看全部</el-button>
            </div>
          </template>

          <div class="space-y-3">
            <article
              v-for="task in recentTasks.slice(0, 4)"
              :key="task.id"
              class="rounded-2xl border border-slate-200 bg-white px-4 py-4 shadow-[0_10px_30px_-24px_rgba(15,23,42,0.45)]"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0 flex-1">
                  <div class="truncate text-sm font-semibold text-slate-900">{{ task.video_title || task.bvid }}</div>
                  <div class="mt-1 text-xs uppercase tracking-[0.2em] text-slate-400">{{ task.bvid }}</div>
                  <div class="mt-2 text-sm text-slate-500">{{ task.progress_message || '等待执行' }}</div>
                </div>
                <div class="flex flex-col items-end gap-2">
                  <el-tag :type="statusType(task.status)" effect="dark" round>{{ statusLabel(task.status) }}</el-tag>
                  <el-button text @click="$router.push(`/video-notes/tasks/${task.id}`)">详情</el-button>
                </div>
              </div>
            </article>
            <el-empty v-if="!recentTasks.length" description="还没有视频任务" />
          </div>
        </el-card>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { useVideoNotesStore } from '@/stores/videoNotes'

const router = useRouter()
const videoNotesStore = useVideoNotesStore()

const form = reactive({
  source_url: '',
  whisper_model: 'large-v3-turbo',
  language: 'zh',
  device: 'cuda',
  compute_type: 'int8_float16',
  use_vad: true
})

const recentTasks = computed(() => [...videoNotesStore.tasks])

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

async function submitTask() {
  if (!form.source_url.trim()) {
    ElMessage.warning('请先填写 B 站视频链接')
    return
  }

  const task = await videoNotesStore.createTask({ ...form, source_url: form.source_url.trim() })
  ElMessage.success('任务已创建，正在后台处理')
  router.push(`/video-notes/tasks/${task.id}`)
}

onMounted(() => {
  videoNotesStore.fetchTasks().catch(() => {})
})
</script>
