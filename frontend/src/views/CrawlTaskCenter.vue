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

        <el-alert
          v-if="journalHint"
          type="warning"
          show-icon
          :closable="false"
          :title="journalHint"
          class="rounded-2xl"
        >
          <el-button text type="primary" @click="$router.push('/crawler/journals')">前往配置采集源</el-button>
        </el-alert>

        <el-form label-position="top" :model="form" class="space-y-4">
          <div class="grid grid-cols-1 gap-4 lg:grid-cols-12">
            <el-form-item class="lg:col-span-5" label="期刊">
              <el-select
                v-model="form.journal_name"
                class="w-full"
                filterable
                clearable
                placeholder="选择已配置的期刊"
                @change="handleJournalChange"
              >
                <el-option
                  v-for="journal in journalOptions"
                  :key="journal.id"
                  :label="journal.name"
                  :value="journal.name"
                />
              </el-select>
            </el-form-item>

            <el-form-item class="lg:col-span-4" label="采集源">
              <el-select
                v-model="form.source_type"
                class="w-full"
                placeholder="选择该期刊已启用的采集源"
                :disabled="!form.journal_name"
                @change="handleSourceChange"
              >
                <el-option
                  v-for="source in availableSources"
                  :key="source.source_id"
                  :label="source.display_name"
                  :value="source.source_id"
                >
                  <span>{{ source.display_name }}</span>
                  <span v-if="source.is_default" class="ml-2 text-xs text-emerald-600">默认</span>
                </el-option>
              </el-select>
            </el-form-item>

            <el-form-item class="lg:col-span-3" label="年份">
              <el-input-number v-model="form.year" :min="1990" :max="2035" class="w-full" @change="resetProbe" />
            </el-form-item>
          </div>

          <el-form-item label="期号">
            <div class="flex w-full flex-col gap-3">
              <div class="flex flex-wrap items-center gap-2">
                <el-input v-model="form.issue" class="w-32" placeholder="例如 2" @input="form.issuePicked = false" />
                <el-button
                  plain
                  :loading="probing"
                  :disabled="!canProbeIssues"
                  @click="probeIssues"
                >
                  探测期号
                </el-button>
                <span v-if="!canProbeIssues" class="text-xs text-slate-400">
                  {{ probeHint }}
                </span>
              </div>
              <div v-if="probeIssuesList.length" class="flex flex-wrap gap-2">
                <el-tag
                  v-for="item in probeIssuesList"
                  :key="item.issue"
                  effect="plain"
                  round
                  class="cursor-pointer"
                  :type="String(form.issue) === String(item.issue) ? 'success' : 'info'"
                  @click="pickIssue(item)"
                >
                  第 {{ item.issue }} 期<template v-if="item.volume"> · Vol.{{ item.volume }}</template>
                  <template v-if="item.published_at"> · {{ item.published_at }}</template>
                </el-tag>
              </div>
              <p v-else-if="probed" class="text-xs text-slate-400">
                {{ probeHint }}
              </p>
            </div>
          </el-form-item>

          <el-form-item class="!mb-0">
            <el-button
              type="primary"
              size="large"
              class="w-full rounded-2xl border-0 bg-slate-950 text-white shadow-[0_18px_50px_-22px_rgba(15,23,42,0.7)] hover:bg-slate-800"
              :loading="crawlerStore.submitting"
              :disabled="!canSubmit"
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
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useCrawlerStore } from '@/stores/crawler'
import { getJournals, getSources, probeJournalIssues } from '@/api/journal'

const route = useRoute()
const crawlerStore = useCrawlerStore()
const tasks = ref([])
const rawIssues = ref([])
const lastResult = ref(null)
const loadError = ref('')

const journals = ref([])
const sources = ref([])
const probing = ref(false)
const probed = ref(false)
const probeIssuesList = ref([])

const form = reactive({
  source_type: '',
  journal_name: '',
  year: new Date().getFullYear(),
  issue: ''
})

const sourceMap = computed(() => {
  const map = {}
  for (const source of sources.value) map[source.source_id] = source
  return map
})

const currentJournal = computed(() => journals.value.find(item => item.name === form.journal_name) || null)

/** 只允许选择该期刊已启用的源，默认源排在首位。 */
const availableSources = computed(() =>
  (currentJournal.value?.sources || [])
    .filter(source => source.enabled)
    .map(source => ({
      ...source,
      display_name: sourceMap.value[source.source_id]?.display_name || source.source_id
    }))
    .sort((a, b) => Number(Boolean(b.is_default)) - Number(Boolean(a.is_default)))
)

const currentSourceMeta = computed(() => sourceMap.value[form.source_type] || null)

const journalHint = computed(() => {
  if (!form.journal_name) return ''
  if (!availableSources.value.length) return '该期刊未配置可用采集源，请先在「期刊与采集源」中启用并测试。'
  return ''
})

const canSubmit = computed(() => Boolean(form.journal_name && form.source_type && form.issue) && !journalHint.value)

const canProbeIssues = computed(() =>
  Boolean(currentJournal.value && form.source_type && form.year && currentSourceMeta.value?.capabilities?.list_issues)
)

const probeHint = computed(() => {
  if (!form.journal_name || !form.source_type) return '先选择期刊与采集源'
  if (!currentSourceMeta.value?.capabilities?.list_issues) return '该采集源不支持列期号，请手工填写期号'
  if (probed.value && !probeIssuesList.value.length) return '未探测到可用期号，请手工填写'
  return ''
})

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
    const sourceId = task?.source_type || task?.sourceType || '-'
    return {
      key: task?.id ?? task?.task_id ?? `task-${index}`,
      journalName: task?.journal_name || task?.journalName || task?.journal || '未命名期刊',
      sourceType: sourceMap.value[sourceId]?.display_name || sourceId,
      year: task?.year ?? '-',
      issue: task?.issue ?? '-',
      errorMessage,
      displayStatus: statusRaw === 'running' && errorMessage ? 'failed' : statusRaw
    }
  })
)

function statusType(status) {
  if (status === 'completed') return 'success'
  if (status === 'running') return 'warning'
  if (status === 'failed') return 'danger'
  return 'info'
}

function resetProbe() {
  probed.value = false
  probeIssuesList.value = []
}

function handleJournalChange() {
  const preferred = availableSources.value.find(source => source.is_default) || availableSources.value[0]
  form.source_type = preferred?.source_id || ''
  resetProbe()
}

function pickIssue(item) {
  form.issue = String(item.issue)
}

async function probeIssues() {
  probing.value = true
  try {
    const payload = await probeJournalIssues(currentJournal.value.id, form.source_type, form.year)
    probeIssuesList.value = Array.isArray(payload?.issues) ? payload.issues : []
    probed.value = true
    if (!probeIssuesList.value.length) ElMessage.warning('未探测到该年份的期号，请手工填写')
  } catch (error) {
    ElMessage.error(`探测期号失败：${error.message}`)
  } finally {
    probing.value = false
  }
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

async function loadJournalOptions() {
  try {
    const [sourceList, journalList] = await Promise.all([getSources(), getJournals()])
    sources.value = Array.isArray(sourceList) ? sourceList : []
    journals.value = Array.isArray(journalList) ? journalList : []

    const requested = route.query.journal
    const target = journals.value.find(item => item.name === requested) || journals.value[0]
    if (target) {
      form.journal_name = target.name
      const enabled = (target.sources || []).filter(source => source.enabled)
      const preferred = enabled.find(source => source.source_id === route.query.source)
        || enabled.find(source => source.is_default)
        || enabled[0]
      form.source_type = preferred?.source_id || ''
    }
  } catch (error) {
    loadError.value = `采集源配置加载失败：${error.message}`
  }
}

async function submitTask() {
  try {
    lastResult.value = await crawlerStore.createTask({
      source_type: form.source_type,
      journal_name: form.journal_name,
      year: form.year,
      issue: String(form.issue)
    })
    ElMessage.success('采集任务完成并已写入原始数据库')
    await loadTaskData()
  } catch (error) {
    console.error(error)
  }
}

onMounted(async () => {
  await loadJournalOptions()
  await loadTaskData()
  setTimeout(() => {
    loadTaskData().catch(() => {})
  }, 1200)
})
</script>
