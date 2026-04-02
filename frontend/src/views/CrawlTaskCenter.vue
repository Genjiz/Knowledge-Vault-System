<template>
  <section v-loading="crawlerStore.loading" class="space-y-6">
    <el-alert v-if="loadError" type="error" show-icon :closable="false" :title="loadError" class="rounded-2xl" />

    <header
      class="relative overflow-hidden rounded-[28px] border border-slate-200/70 bg-[radial-gradient(circle_at_top_left,_rgba(34,197,94,0.12),_transparent_28%),linear-gradient(135deg,_rgba(255,255,255,0.98),_rgba(241,245,249,0.94))] px-8 py-8 shadow-[0_30px_80px_-36px_rgba(15,23,42,0.3)]"
    >
      <div class="absolute inset-y-0 right-0 w-48 bg-[linear-gradient(135deg,transparent,rgba(15,23,42,0.08))]" />
      <div class="relative flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div class="max-w-2xl space-y-3">
          <p class="text-xs uppercase tracking-[0.4em] text-slate-500">Collection Desk</p>
          <h2 class="text-4xl font-black tracking-tight text-slate-950">采集任务台</h2>
          <p class="text-sm leading-7 text-slate-600">在统一工作台发起采集，结果写入原始库并导出结构化快照。</p>
        </div>
        <div class="grid grid-cols-2 gap-3 rounded-[24px] border border-white/70 bg-white/70 p-4 backdrop-blur">
          <div>
            <div class="text-xs uppercase tracking-[0.3em] text-slate-400">任务数</div>
            <div class="mt-1 text-2xl font-bold text-slate-900">{{ taskCards.length }}</div>
          </div>
          <div>
            <div class="text-xs uppercase tracking-[0.3em] text-slate-400">采集期号</div>
            <div class="mt-1 text-2xl font-bold text-slate-900">{{ rawIssues.length }}</div>
          </div>
        </div>
      </div>
    </header>

    <div class="grid gap-6 xl:grid-cols-[0.92fr_1.08fr]">
      <el-card class="rounded-[28px] border border-slate-200/70 !shadow-[0_24px_64px_-36px_rgba(15,23,42,0.28)]">
        <template #header>
          <div class="flex items-center justify-between">
            <div>
              <div class="text-xs uppercase tracking-[0.35em] text-slate-400">Launch</div>
              <div class="mt-1 text-xl font-bold text-slate-900">新建采集任务</div>
            </div>
            <div class="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
              同步执行
            </div>
          </div>
        </template>

        <el-form label-position="top" :model="form" class="space-y-4">
          <el-form-item label="数据源">
            <el-radio-group v-model="form.source_type" size="large">
              <el-radio-button v-for="option in sourceOptions" :key="option.value" :label="option.value">
                {{ option.label }}
              </el-radio-button>
            </el-radio-group>
          </el-form-item>

          <div class="grid grid-cols-1 gap-4 lg:grid-cols-12">
            <el-form-item class="lg:col-span-7" label="期刊名称">
              <el-select
                v-model="form.journal_name"
                class="w-full"
                filterable
                allow-create
                default-first-option
                clearable
                placeholder="选择历史期刊或输入新期刊"
              >
                <el-option v-for="name in filteredJournalOptions" :key="name" :label="name" :value="name" />
              </el-select>
            </el-form-item>

            <el-form-item class="lg:col-span-3" label="年份">
              <el-input-number v-model="form.year" :min="1990" :max="2035" class="w-full" />
            </el-form-item>

            <el-form-item class="lg:col-span-2" label="期号">
              <el-input v-model="form.issue" placeholder="例如 2" />
            </el-form-item>
          </div>

          <el-form-item class="!mb-0">
            <el-button
              type="primary"
              size="large"
              class="w-full rounded-2xl border-0 bg-slate-950 text-white shadow-[0_18px_50px_-22px_rgba(15,23,42,0.7)] hover:bg-slate-800"
              :loading="crawlerStore.submitting"
              @click="submitTask"
            >
              发起采集
            </el-button>
          </el-form-item>
        </el-form>

        <div v-if="lastResult" class="mt-6 rounded-[24px] border border-slate-200 bg-slate-50/80 p-5">
          <div class="flex items-center justify-between gap-4">
            <div>
              <div class="text-xs uppercase tracking-[0.3em] text-slate-400">Latest Result</div>
              <div class="mt-1 text-lg font-semibold text-slate-900">{{ lastResult?.raw_issue?.journal_name || '采集完成' }}</div>
              <div class="text-sm text-slate-500">
                {{ lastResult?.raw_issue?.year || '-' }} / 第 {{ lastResult?.raw_issue?.issue || '-' }} 期
              </div>
            </div>
            <el-button v-if="lastResult?.raw_issue?.id" text @click="$router.push(`/crawler/issues/${lastResult.raw_issue.id}`)">
              查看结果
            </el-button>
          </div>
        </div>
      </el-card>

      <el-card class="rounded-[28px] border border-slate-200/70 !shadow-[0_24px_64px_-36px_rgba(15,23,42,0.28)]">
        <template #header>
          <div>
            <div class="text-xs uppercase tracking-[0.35em] text-slate-400">Recent Activity</div>
            <div class="mt-1 text-xl font-bold text-slate-900">任务记录</div>
          </div>
        </template>

        <div class="max-h-[540px] space-y-3 overflow-y-auto pr-1">
          <article
            v-for="task in taskCards"
            :key="task.key"
            class="rounded-2xl border border-slate-200 bg-white px-4 py-4 shadow-[0_10px_30px_-24px_rgba(15,23,42,0.45)]"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0 flex-1">
                <div class="truncate text-sm font-semibold text-slate-900">{{ task.journalName }}</div>
                <div class="mt-1 text-xs uppercase tracking-[0.2em] text-slate-400">{{ task.sourceType }}</div>
                <div class="mt-2 text-sm text-slate-500">{{ task.year }} / {{ task.issue }}</div>
                <p v-if="task.errorMessage" class="mt-2 break-words text-xs leading-6 text-rose-600">
                  {{ task.errorMessage }}
                </p>
              </div>
              <el-tag :type="statusType(task.displayStatus)" effect="dark" round>{{ task.displayStatus }}</el-tag>
            </div>
          </article>
          <el-empty v-if="!taskCards.length" description="还没有采集任务" />
        </div>
      </el-card>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useCrawlerStore } from '@/stores/crawler'

const crawlerStore = useCrawlerStore()
const tasks = ref([])
const rawIssues = ref([])
const lastResult = ref(null)
const loadError = ref('')

const form = reactive({
  source_type: 'foreign',
  journal_name: 'Information Processing & Management',
  year: 2024,
  issue: '6'
})

const sourceOptions = [
  { label: '国外期刊', value: 'foreign' },
  { label: '国内期刊', value: 'domestic' }
]

const defaultJournals = {
  foreign: ['Information Processing & Management'],
  domestic: ['情报学报', '图书情报工作', '情报理论与实践']
}

const allJournalsBySource = computed(() => {
  const grouped = { foreign: new Set(defaultJournals.foreign), domestic: new Set(defaultJournals.domestic) }
  for (const item of Array.isArray(tasks.value) ? tasks.value : []) {
    if (item?.source_type && item?.journal_name && grouped[item.source_type]) grouped[item.source_type].add(item.journal_name)
  }
  for (const item of Array.isArray(rawIssues.value) ? rawIssues.value : []) {
    if (item?.source_type && item?.journal_name && grouped[item.source_type]) grouped[item.source_type].add(item.journal_name)
  }
  return {
    foreign: Array.from(grouped.foreign).sort((a, b) => a.localeCompare(b)),
    domestic: Array.from(grouped.domestic).sort((a, b) => a.localeCompare(b))
  }
})

const filteredJournalOptions = computed(() => allJournalsBySource.value[form.source_type] || [])

const sortedTasks = computed(() => {
  return [...(Array.isArray(tasks.value) ? tasks.value : [])].sort((a, b) => {
    const ta = Date.parse(a?.started_at || a?.created_at || a?.finished_at || '') || 0
    const tb = Date.parse(b?.started_at || b?.created_at || b?.finished_at || '') || 0
    if (tb !== ta) return tb - ta
    return (b?.id || 0) - (a?.id || 0)
  })
})

const taskCards = computed(() =>
  sortedTasks.value.map((task, index) => {
    const statusRaw = task?.status || task?.task_status || task?.state || 'unknown'
    const errorMessage = task?.error_message || task?.errorMessage || ''
    return {
      key: task?.id ?? task?.task_id ?? `task-${index}`,
      journalName: task?.journal_name || task?.journalName || task?.journal || '未命名期刊',
      sourceType: task?.source_type || task?.sourceType || '-',
      year: task?.year ?? '-',
      issue: task?.issue ?? '-',
      errorMessage,
      displayStatus: statusRaw === 'running' && errorMessage ? 'failed' : statusRaw
    }
  })
)

watch(
  () => form.source_type,
  sourceType => {
    const options = allJournalsBySource.value[sourceType] || []
    if (!options.includes(form.journal_name)) form.journal_name = options[0] || ''
  },
  { immediate: true }
)

function statusType(status) {
  if (status === 'completed') return 'success'
  if (status === 'running') return 'warning'
  if (status === 'failed') return 'danger'
  return 'info'
}

function unwrapApiPayload(payload) {
  if (payload && typeof payload === 'object' && payload.code === 200) return payload.data
  return payload?.data ?? payload
}

async function fetchTasksDirect() {
  const response = await fetch(`/api/crawl-tasks?_t=${Date.now()}`, {
    method: 'GET',
    cache: 'no-store',
    headers: { Accept: 'application/json' }
  })
  if (!response.ok) throw new Error(`Fetch tasks failed: ${response.status}`)
  const payload = unwrapApiPayload(await response.json())
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.items)) return payload.items
  return []
}

async function fetchRawIssuesDirect() {
  const response = await fetch(`/api/raw-issues?_t=${Date.now()}`, {
    method: 'GET',
    cache: 'no-store',
    headers: { Accept: 'application/json' }
  })
  if (!response.ok) throw new Error(`Fetch raw issues failed: ${response.status}`)
  const payload = unwrapApiPayload(await response.json())
  if (Array.isArray(payload?.items)) return payload.items
  if (Array.isArray(payload)) return payload
  return []
}

async function loadTaskData() {
  loadError.value = ''
  const maxAttempts = 5
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    const [taskResult, issueResult] = await Promise.allSettled([fetchTasksDirect(), fetchRawIssuesDirect()])
    if (taskResult.status === 'fulfilled') tasks.value = taskResult.value
    if (issueResult.status === 'fulfilled') rawIssues.value = issueResult.value
    const bothFulfilled = taskResult.status === 'fulfilled' && issueResult.status === 'fulfilled'
    const hasAnyData = taskCards.value.length > 0 || rawIssues.value.length > 0
    if (bothFulfilled && hasAnyData) return
    if (attempt < maxAttempts) await new Promise(resolve => setTimeout(resolve, attempt * 900))
  }
  loadError.value = '采集任务台加载失败，请稍后重试或检查后端服务。'
}

async function submitTask() {
  try {
    lastResult.value = await crawlerStore.createTask({ ...form })
    ElMessage.success('采集任务完成并已写入原始数据库')
    await loadTaskData()
  } catch (error) {
    console.error(error)
  }
}

onMounted(async () => {
  await loadTaskData()
  setTimeout(() => {
    loadTaskData().catch(() => {})
  }, 1200)
})
</script>
