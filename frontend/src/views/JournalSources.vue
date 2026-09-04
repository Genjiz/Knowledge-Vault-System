<template>
  <div class="page-shell">
    <section v-loading="loading" class="page-hero">
      <div class="page-hero__body lg:grid-cols-[1.4fr_1fr]">
        <div>
          <div class="page-eyebrow">
            <span>Collection Setup</span>
            <span class="h-1 w-1 rounded-full bg-slate-400"></span>
            <span>Sources</span>
          </div>
          <h2 class="page-title">期刊与采集源</h2>
          <p class="page-subtitle">
            维护支持批量采集的期刊清单：为每个期刊配置可用采集源、测试连通性，默认源会在采集台自动选中。
            采集任务本身在采集任务台发起。
          </p>
        </div>

        <div class="hero-meta-grid self-start">
          <div class="hero-meta-tile">
            <div class="hero-meta-label">支持期刊</div>
            <div class="hero-meta-value">{{ journals.length }}</div>
          </div>
          <div class="hero-meta-tile">
            <div class="hero-meta-label">已启用源组合</div>
            <div class="hero-meta-value">{{ enabledPairCount }}</div>
          </div>
          <div class="hero-meta-tile">
            <div class="hero-meta-label">已采集期数</div>
            <div class="hero-meta-value">{{ totalIssueCount }}</div>
          </div>
          <div class="hero-meta-tile">
            <div class="hero-meta-label">待测试源</div>
            <div class="hero-meta-value">{{ untestedCount }}</div>
          </div>
        </div>
      </div>
    </section>

    <section class="surface-panel">
      <div class="surface-panel__header">
        <div>
          <h3 class="surface-panel__title">期刊清单</h3>
          <p class="surface-panel__caption">卡片上的标签即该期刊可用的采集源，高亮标签为默认源。</p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <el-button plain @click="handleImportKnown">导入内置清单</el-button>
          <el-button type="primary" size="large" @click="openDrawer()">新增期刊</el-button>
        </div>
      </div>

      <div v-if="journals.length" class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <article
          v-for="journal in journals"
          :key="journal.id"
          class="flex flex-col gap-4 rounded-[24px] border border-slate-200/80 bg-white/85 p-5 shadow-[0_16px_40px_-32px_rgba(15,23,42,0.5)]"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <h4 class="truncate text-lg font-bold text-slate-900">{{ journal.name }}</h4>
              <p class="mt-1 truncate text-xs text-slate-500">
                {{ journal.issn || '未填写 ISSN' }}<template v-if="journal.publisher"> · {{ journal.publisher }}</template>
              </p>
            </div>
            <el-tag :type="regionTagType(journal.region)" effect="plain" round size="small">
              {{ regionLabel(journal.region) }}
            </el-tag>
          </div>

          <div class="flex flex-wrap gap-2">
            <el-tag
              v-for="source in journal.sources"
              :key="source.source_id"
              :type="sourceTagType(source)"
              effect="dark"
              round
              size="small"
            >
              {{ sourceDisplayName(source.source_id) }}{{ source.is_default ? ' · 默认' : '' }}
            </el-tag>
            <span v-if="!journal.sources.length" class="text-xs text-slate-400">尚未配置采集源</span>
          </div>

          <div class="flex items-center gap-4 text-xs text-slate-500">
            <span>已采集 <strong class="text-slate-800">{{ journal.stats?.issue_count ?? 0 }}</strong> 期</span>
            <span v-if="journal.stats?.last_collected_at">最近 {{ formatDate(journal.stats.last_collected_at) }}</span>
          </div>

          <div class="mt-auto flex items-center gap-2 border-t border-slate-100 pt-4">
            <el-button plain size="small" @click="openDrawer(journal)">配置</el-button>
            <el-button
              plain
              size="small"
              :disabled="!journal.sources.some(source => source.enabled)"
              @click="goCollect(journal)"
            >
              去采集
            </el-button>
            <el-button plain size="small" type="danger" @click="handleDelete(journal)">删除</el-button>
          </div>
        </article>
      </div>

      <el-empty v-else description="还没有期刊。新增期刊并配置采集源后，采集任务台即可发起采集。">
        <div class="flex flex-wrap items-center justify-center gap-2">
          <el-button type="primary" @click="openDrawer()">新增期刊</el-button>
          <el-button plain @click="handleImportKnown">导入内置清单</el-button>
        </div>
      </el-empty>
    </section>

    <el-drawer
      v-model="drawerVisible"
      :title="drawerForm.id ? `配置《${drawerForm.name}》` : '新增期刊'"
      size="640px"
      :close-on-click-modal="false"
    >
      <div v-loading="saving" class="flex h-full flex-col">
        <div class="flex-1 space-y-6 overflow-y-auto pr-1">
          <section class="space-y-3">
            <h4 class="text-sm font-bold uppercase tracking-[0.2em] text-slate-400">基本信息</h4>
            <el-form label-position="top">
              <el-form-item label="期刊名称" required>
                <el-input v-model="drawerForm.name" placeholder="例如：情报学报" />
              </el-form-item>
              <el-form-item label="区域" required>
                <el-radio-group v-model="drawerForm.region">
                  <el-radio-button value="domestic">国内期刊</el-radio-button>
                  <el-radio-button value="foreign">国外期刊</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <div class="grid grid-cols-2 gap-4">
                <el-form-item label="ISSN">
                  <el-input v-model="drawerForm.issn" placeholder="例如：1000-0135" />
                </el-form-item>
                <el-form-item label="出版方">
                  <el-input v-model="drawerForm.publisher" placeholder="例如：中国科学技术信息研究所" />
                </el-form-item>
              </div>
            </el-form>
          </section>

          <section v-if="drawerForm.region" class="space-y-3">
            <div class="flex items-center justify-between">
              <h4 class="text-sm font-bold uppercase tracking-[0.2em] text-slate-400">采集源配置</h4>
              <span class="text-xs text-slate-400">未提交的源视为不可用</span>
            </div>

            <article
              v-for="row in drawerForm.rows"
              :key="row.source_id"
              class="rounded-[20px] border p-4"
              :class="row.enabled ? 'border-slate-200 bg-white' : 'border-slate-200/70 bg-slate-50'"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="font-semibold text-slate-900">{{ row.display_name }}</span>
                    <el-tag size="small" effect="plain" round>{{ regionLabel(row.region) }}</el-tag>
                  </div>
                  <div class="mt-1 flex flex-wrap gap-1 text-[11px] text-slate-500">
                    <span v-if="row.capabilities.list_issues" class="rounded-full bg-slate-100 px-2 py-0.5">支持列期号</span>
                    <span v-if="row.capabilities.needs_browser" class="rounded-full bg-slate-100 px-2 py-0.5">需要浏览器</span>
                    <span v-if="!row.config_fields.length" class="rounded-full bg-slate-100 px-2 py-0.5">无需额外配置</span>
                  </div>
                </div>
                <el-switch v-model="row.enabled" />
              </div>

              <div v-if="row.config_fields.length && row.enabled" class="mt-3 space-y-3">
                <div v-for="field in row.config_fields" :key="field.key">
                  <label class="mb-1 block text-xs font-medium text-slate-600">
                    {{ field.label }}
                    <span v-if="field.required" class="text-rose-500">*</span>
                  </label>
                  <el-input
                    v-model="row.config[field.key]"
                    :placeholder="field.placeholder"
                    :class="{ 'is-error': row.error }"
                    @input="row.error = false"
                  />
                  <p v-if="field.help" class="mt-1 text-xs text-slate-400">{{ field.help }}</p>
                </div>
              </div>

              <div v-if="row.enabled" class="mt-3 flex flex-wrap items-center gap-2">
                <el-radio v-model="defaultSourceId" :value="row.source_id">设为默认源</el-radio>
                <el-button
                  size="small"
                  plain
                  :loading="row.testing"
                  :disabled="!drawerForm.id"
                  @click="handleTest(row)"
                >
                  测试连接
                </el-button>
                <el-button size="small" text @click="goCollectWithSource(row)">去采集</el-button>
              </div>

              <p v-if="row.testMessage" class="mt-2 text-xs leading-6" :class="testMessageClass(row.testStatus)">
                {{ row.testMessage }}
              </p>
              <p v-else-if="!drawerForm.id" class="mt-2 text-xs text-slate-400">保存期刊后可测试源连通性</p>
            </article>
          </section>

          <el-alert
            v-else
            type="info"
            show-icon
            :closable="false"
            title="请先选择期刊区域，采集源按区域匹配（国内：国家哲社文献中心 / 期刊官网；国外：Elsevier）"
          />
        </div>

        <div class="mt-6 flex items-center justify-end gap-2 border-t border-slate-100 pt-4">
          <el-button @click="drawerVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createJournal,
  deleteJournal,
  getJournals,
  getSources,
  importKnownJournals,
  replaceJournalSources,
  testJournalSource,
  updateJournal
} from '@/api/journal'

const router = useRouter()

const journals = ref([])
const sources = ref([])
const loading = ref(false)
const saving = ref(false)
const drawerVisible = ref(false)
const defaultSourceId = ref('')

const drawerForm = reactive({
  id: null,
  name: '',
  issn: '',
  publisher: '',
  region: '',
  rows: []
})

// 区域切换意味着可选源集合整体变化，重建源行避免残留另一区域的配置
watch(
  () => drawerForm.region,
  () => {
    if (drawerVisible.value) rebuildRows()
  }
)

const sourceMap = computed(() => {
  const map = {}
  for (const source of sources.value) map[source.source_id] = source
  return map
})

const enabledPairCount = computed(() =>
  journals.value.reduce(
    (sum, journal) => sum + (journal.sources || []).filter(source => source.enabled).length,
    0
  )
)

const totalIssueCount = computed(() =>
  journals.value.reduce((sum, journal) => sum + (journal.stats?.issue_count || 0), 0)
)

const untestedCount = computed(() =>
  journals.value.reduce(
    (sum, journal) =>
      sum + (journal.sources || []).filter(source => source.enabled && !source.last_check_status).length,
    0
  )
)

function sourceDisplayName(sourceId) {
  return sourceMap.value[sourceId]?.display_name || sourceId
}

function regionLabel(region) {
  if (region === 'domestic') return '国内'
  if (region === 'foreign') return '国外'
  return '未设置'
}

function regionTagType(region) {
  if (region === 'domestic') return 'danger'
  if (region === 'foreign') return 'primary'
  return 'info'
}

function sourceTagType(source) {
  if (!source.enabled) return 'info'
  return source.is_default ? 'success' : 'warning'
}

function testMessageClass(status) {
  if (status === 'ok') return 'text-emerald-600'
  if (status === 'failed') return 'text-rose-600'
  return 'text-amber-600'
}

function formatDate(value) {
  if (!value) return '-'
  return String(value).replace('T', ' ').slice(0, 16)
}

/** 期刊的区域由用户在基本信息里维护，决定可选采集源范围与论文语言语义。 */
function withJournalRegion(journal) {
  return { ...journal }
}

async function loadData() {
  loading.value = true
  try {
    const [sourceList, journalList] = await Promise.all([getSources(), getJournals()])
    sources.value = Array.isArray(sourceList) ? sourceList : []
    journals.value = (Array.isArray(journalList) ? journalList : []).map(withJournalRegion)
  } catch (error) {
    ElMessage.error(`加载失败：${error.message}`)
  } finally {
    loading.value = false
  }
}

function buildRows(journal, region) {
  const configured = new Map((journal?.sources || []).map(source => [source.source_id, source]))
  return sources.value
    .filter(source => source.region === region)
    .map(source => {
      const row = configured.get(source.source_id)
      let config = {}
      try {
        config = row?.config_json ? JSON.parse(row.config_json) : {}
      } catch {
        config = {}
      }
      return {
        source_id: source.source_id,
        display_name: source.display_name,
        region: source.region,
        capabilities: source.capabilities || {},
        config_fields: source.config_fields || [],
        enabled: row ? Boolean(row.enabled) : false,
        config,
        testing: false,
        error: false,
        testStatus: row?.last_check_status || '',
        testMessage: row?.last_check_message || ''
      }
    })
}

function openDrawer(journal = null) {
  drawerForm.id = journal?.id ?? null
  drawerForm.name = journal?.name ?? ''
  drawerForm.issn = journal?.issn ?? ''
  drawerForm.publisher = journal?.publisher ?? ''
  drawerForm.region = journal?.region ?? ''
  rebuildRows(journal)
  drawerVisible.value = true
}

/** 区域决定可选源集合：切换区域时按新区域重建源行，跨区域的旧配置由保存时的整体替换清掉。 */
function rebuildRows(journal = null) {
  drawerForm.rows = buildRows(journal, drawerForm.region)
  const defaultRow = (journal?.sources || []).find(source => source.is_default && source.enabled)
  defaultSourceId.value =
    drawerForm.rows.find(row => row.source_id === defaultRow?.source_id)?.source_id
    || drawerForm.rows.find(row => row.enabled)?.source_id
    || ''
}

async function handleTest(row) {
  row.testing = true
  try {
    const result = await testJournalSource(drawerForm.id, row.source_id)
    row.testStatus = result.last_check_status
    row.testMessage = `${result.last_check_message || '无返回信息'}（${formatDate(result.last_checked_at)}）`
  } catch (error) {
    row.testStatus = 'failed'
    row.testMessage = `测试失败：${error.message}`
  } finally {
    row.testing = false
  }
}

function goCollect(journal) {
  const defaultSource = (journal.sources || []).find(source => source.is_default && source.enabled)
  router.push({
    path: '/crawler/tasks',
    query: { journal: journal.name, source: defaultSource?.source_id || '' }
  })
}

/** 从抽屉内带着当前源直奔采集台，省去重新选一遍。 */
function goCollectWithSource(row) {
  drawerVisible.value = false
  router.push({ path: '/crawler/tasks', query: { journal: drawerForm.name, source: row.source_id } })
}

function rowsPayload() {
  return drawerForm.rows.map(row => ({
    source_id: row.source_id,
    enabled: row.enabled,
    is_default: row.enabled && row.source_id === defaultSourceId.value,
    config: row.config
  }))
}

function validateRows() {
  let valid = true
  for (const row of drawerForm.rows) {
    row.error = false
    if (!row.enabled) continue
    const missing = row.config_fields.some(
      field => field.required && !String(row.config[field.key] || '').trim()
    )
    if (missing) {
      row.error = true
      valid = false
    }
  }
  return valid
}

async function handleSave() {
  if (!drawerForm.name.trim()) {
    ElMessage.warning('请填写期刊名称')
    return
  }
  if (!drawerForm.region) {
    ElMessage.warning('请选择期刊区域')
    return
  }
  if (!validateRows()) {
    ElMessage.warning('已启用的采集源存在未填写的必填配置')
    return
  }

  saving.value = true
  try {
    const payload = {
      name: drawerForm.name.trim(),
      issn: drawerForm.issn || null,
      publisher: drawerForm.publisher || null,
      region: drawerForm.region
    }
    let journalId = drawerForm.id
    if (journalId) {
      await updateJournal(journalId, payload)
    } else {
      const created = await createJournal(payload)
      journalId = created?.id
    }
    await replaceJournalSources(journalId, rowsPayload())
    ElMessage.success('已保存')
    drawerVisible.value = false
    await loadData()
  } catch (error) {
    ElMessage.error(`保存失败：${error.message}`)
  } finally {
    saving.value = false
  }
}

async function handleDelete(journal) {
  try {
    await ElMessageBox.confirm(
      `删除《${journal.name}》会同时移除其采集源配置，已采集的数据不受影响。确定删除吗？`,
      '删除确认',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  try {
    await deleteJournal(journal.id)
    ElMessage.success('已删除')
    await loadData()
  } catch (error) {
    ElMessage.error(`删除失败：${error.message}`)
  }
}

async function handleImportKnown() {
  try {
    const result = await importKnownJournals()
    const created = result?.created?.length || 0
    const updated = result?.updated?.length || 0
    ElMessage.success(`导入完成：新增 ${created} 个期刊，补充 ${updated} 个期刊的源配置`)
    await loadData()
  } catch (error) {
    ElMessage.error(`导入失败：${error.message}`)
  }
}

onMounted(async () => {
  await loadData()
})
</script>
