<template>
  <section class="space-y-6">
    <header
      class="relative overflow-hidden rounded-[28px] border border-slate-200/70 bg-[radial-gradient(circle_at_top_left,_rgba(34,197,94,0.12),_transparent_28%),linear-gradient(135deg,_rgba(255,255,255,0.98),_rgba(241,245,249,0.94))] px-8 py-8 shadow-[0_30px_80px_-36px_rgba(15,23,42,0.3)]"
    >
      <div class="absolute inset-y-0 right-0 w-48 bg-[linear-gradient(135deg,transparent,rgba(15,23,42,0.08))]" />
      <div class="relative flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div class="max-w-2xl space-y-3">
          <p class="text-xs uppercase tracking-[0.4em] text-slate-500">Collection Archive</p>
          <h2 class="text-4xl font-black tracking-tight text-slate-950">采集期号库</h2>
          <p class="text-sm leading-7 text-slate-600">
            按“期刊 → 年份 → 期号”分层管理采集结果，便于持续追踪翻译和分析状态。
          </p>
        </div>
        <div class="grid grid-cols-2 gap-3 rounded-[24px] border border-white/70 bg-white/70 p-4 backdrop-blur">
          <div>
            <div class="text-xs uppercase tracking-[0.3em] text-slate-400">总期号</div>
            <div class="mt-1 text-2xl font-bold text-slate-900">{{ issues.length }}</div>
          </div>
          <div>
            <div class="text-xs uppercase tracking-[0.3em] text-slate-400">筛选结果</div>
            <div class="mt-1 text-2xl font-bold text-slate-900">{{ filteredIssues.length }}</div>
          </div>
        </div>
      </div>
    </header>

    <el-card class="rounded-[28px] border border-slate-200/70 !shadow-[0_24px_64px_-36px_rgba(15,23,42,0.28)]">
      <template #header>
        <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div class="text-xs uppercase tracking-[0.3em] text-slate-400">Archive Index</div>
            <div class="mt-1 text-xl font-bold text-slate-900">按期刊和年份浏览</div>
          </div>
          <div class="flex flex-wrap items-center gap-3">
            <el-radio-group v-model="sourceFilter" size="small">
              <el-radio-button label="all">全部</el-radio-button>
              <el-radio-button label="domestic">国内</el-radio-button>
              <el-radio-button label="foreign">国外</el-radio-button>
            </el-radio-group>
            <el-button class="rounded-2xl border-slate-300 bg-white/85" @click="router.push('/crawler/tasks')">
              返回采集任务台
            </el-button>
          </div>
        </div>
      </template>

      <div class="grid gap-5 xl:grid-cols-[320px_1fr]">
        <aside class="rounded-2xl border border-slate-200/80 bg-slate-50/55 p-4">
          <div class="mb-3 flex items-center justify-between">
            <div>
              <div class="text-xs uppercase tracking-[0.28em] text-slate-400">Hierarchy</div>
              <div class="mt-1 text-sm font-semibold text-slate-900">期刊 / 年份</div>
            </div>
            <el-tag round type="info">{{ journalCount }} 刊</el-tag>
          </div>

          <el-empty v-if="treeData.length === 0" description="暂无可展示期号" />
          <el-tree
            v-else
            class="archive-tree"
            :data="treeData"
            node-key="id"
            :props="treeProps"
            highlight-current
            :expand-on-click-node="false"
            :default-expand-all="false"
            :current-node-key="selectedNodeId"
            @node-click="handleNodeClick"
          >
            <template #default="{ data }">
              <div class="flex w-full items-center justify-between gap-2 py-1">
                <div class="min-w-0">
                  <div
                    class="truncate"
                    :class="data.type === 'journal' ? 'text-[13px] font-semibold text-slate-900' : 'text-[13px] text-slate-700'"
                  >
                    {{ data.type === 'journal' ? data.journal_name : `${data.year} 年` }}
                  </div>
                  <div
                    v-if="data.type === 'journal'"
                    class="mt-0.5 text-[11px]"
                    :class="data.source_type === 'domestic' ? 'text-cyan-700' : 'text-violet-700'"
                  >
                    {{ data.source_type === 'domestic' ? '国内期刊' : '国外期刊' }}
                  </div>
                </div>
                <span class="rounded-full bg-white px-2 py-0.5 text-[11px] font-semibold text-slate-600">
                  {{ data.issue_count }}
                </span>
              </div>
            </template>
          </el-tree>
        </aside>

        <section class="rounded-2xl border border-slate-200/80 bg-white p-4 lg:p-5">
          <div v-if="!selectedNode" class="py-16">
            <el-empty description="请选择左侧期刊或年份查看期号列表" />
          </div>

          <template v-else>
            <div class="mb-4 flex flex-col gap-2 border-b border-slate-200 pb-4 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <div class="text-xs uppercase tracking-[0.28em] text-slate-400">Selected Node</div>
                <div class="mt-1 text-xl font-bold text-slate-900">{{ selectedTitle }}</div>
                <div class="mt-1 text-sm text-slate-500">{{ selectedSubtitle }}</div>
              </div>
              <div class="text-sm text-slate-500">
                共 <span class="font-semibold text-slate-900">{{ selectedIssues.length }}</span> 期
              </div>
            </div>

            <el-empty v-if="selectedIssues.length === 0" description="该节点下暂无期号" />
            <div v-else class="grid gap-3 md:grid-cols-2">
              <article
                v-for="issue in selectedIssues"
                :key="issue.id"
                class="rounded-2xl border border-slate-200/80 bg-[linear-gradient(135deg,#ffffff,#f8fafc)] p-4 shadow-[0_12px_28px_-24px_rgba(15,23,42,0.6)]"
              >
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0">
                    <div class="line-clamp-1 text-sm font-semibold text-slate-900">{{ issue.journal_name }}</div>
                    <div class="mt-1 text-xs text-slate-500">{{ issue.year }} 年 · 第 {{ issue.issue }} 期</div>
                  </div>
                  <el-tag class="status-chip" :class="issue.source_type === 'domestic' ? 'status-chip--source-domestic' : 'status-chip--source-foreign'" round>
                    {{ issue.source_type === 'domestic' ? '国内' : '国外' }}
                  </el-tag>
                </div>

                <div class="mt-3 flex flex-wrap gap-2">
                  <el-tag class="status-chip" :class="translationTagClass(issue)" round>
                    翻译：{{ translationStatusLabel(issue) }}
                  </el-tag>
                  <el-tag class="status-chip" :class="analysisTagClass(issue)" round>
                    分析：{{ issue.analysis_status === 'completed' ? '已完成' : '未完成' }}
                  </el-tag>
                  <el-tag class="status-chip status-chip--paper-count" round>论文 {{ issue.paper_count || 0 }} 篇</el-tag>
                </div>

                <div class="mt-4 flex justify-end">
                  <el-button text @click="router.push(`/crawler/issues/${issue.id}`)">查看详情</el-button>
                </div>
              </article>
            </div>
          </template>
        </section>
      </div>
    </el-card>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useCrawlerStore } from '@/stores/crawler'

const router = useRouter()
const crawlerStore = useCrawlerStore()
const sourceFilter = ref('all')
const treeProps = { children: 'children', label: 'label' }
const selectedNodeId = ref('')
const selectedNode = ref(null)

const issues = computed(() => crawlerStore.rawIssues)

function parseIssueNumber(issueValue) {
  const matched = String(issueValue ?? '').match(/\d+/)
  return matched ? Number(matched[0]) : Number.NaN
}

function sortIssuesByPeriod(a, b) {
  if (a.year !== b.year) return Number(b.year || 0) - Number(a.year || 0)
  const aNum = parseIssueNumber(a.issue)
  const bNum = parseIssueNumber(b.issue)
  if (!Number.isNaN(aNum) && !Number.isNaN(bNum) && aNum !== bNum) {
    return bNum - aNum
  }
  return String(b.issue || '').localeCompare(String(a.issue || ''), 'zh-Hans-CN')
}

const filteredIssues = computed(() => {
  const source = sourceFilter.value
  const base = source === 'all'
    ? issues.value
    : issues.value.filter(item => item.source_type === source)
  return [...base].sort((a, b) => {
    if (a.journal_name !== b.journal_name) {
      return String(a.journal_name || '').localeCompare(String(b.journal_name || ''), 'zh-Hans-CN')
    }
    return sortIssuesByPeriod(a, b)
  })
})

const groupedJournals = computed(() => {
  const journalMap = new Map()
  filteredIssues.value.forEach(issue => {
    const sourceType = issue.source_type || 'unknown'
    const journalName = issue.journal_name || '未命名期刊'
    const journalKey = `${sourceType}::${journalName}`
    if (!journalMap.has(journalKey)) {
      journalMap.set(journalKey, {
        key: journalKey,
        source_type: sourceType,
        journal_name: journalName,
        issues: [],
        yearMap: new Map()
      })
    }

    const journalEntry = journalMap.get(journalKey)
    journalEntry.issues.push(issue)

    const yearKey = Number(issue.year || 0)
    if (!journalEntry.yearMap.has(yearKey)) {
      journalEntry.yearMap.set(yearKey, [])
    }
    journalEntry.yearMap.get(yearKey).push(issue)
  })

  return [...journalMap.values()]
    .map(entry => {
      const years = [...entry.yearMap.entries()]
        .sort((a, b) => b[0] - a[0])
        .map(([year, yearIssues]) => ({
          id: `year:${entry.key}:${year}`,
          type: 'year',
          year,
          source_type: entry.source_type,
          journal_name: entry.journal_name,
          issue_count: yearIssues.length,
          issues: [...yearIssues].sort(sortIssuesByPeriod),
          children: []
        }))

      return {
        id: `journal:${entry.key}`,
        type: 'journal',
        source_type: entry.source_type,
        journal_name: entry.journal_name,
        issue_count: entry.issues.length,
        issues: [...entry.issues].sort(sortIssuesByPeriod),
        children: years
      }
    })
    .sort((a, b) => {
      if (a.source_type !== b.source_type) {
        return a.source_type.localeCompare(b.source_type)
      }
      return a.journal_name.localeCompare(b.journal_name, 'zh-Hans-CN')
    })
})

const treeData = computed(() => groupedJournals.value)
const journalCount = computed(() => groupedJournals.value.length)

const selectedIssues = computed(() => {
  if (!selectedNode.value) return []
  return selectedNode.value.issues || []
})

const selectedTitle = computed(() => {
  if (!selectedNode.value) return ''
  if (selectedNode.value.type === 'journal') return selectedNode.value.journal_name
  return `${selectedNode.value.journal_name} · ${selectedNode.value.year} 年`
})

const selectedSubtitle = computed(() => {
  if (!selectedNode.value) return ''
  const sourceText = selectedNode.value.source_type === 'domestic' ? '国内期刊' : '国外期刊'
  if (selectedNode.value.type === 'journal') {
    return `${sourceText} · 共 ${selectedIssues.value.length} 期`
  }
  return `${sourceText} · 该年份共 ${selectedIssues.value.length} 期`
})

function findNodeById(nodes, id) {
  for (const node of nodes) {
    if (node.id === id) return node
    if (node.children?.length) {
      const found = findNodeById(node.children, id)
      if (found) return found
    }
  }
  return null
}

function handleNodeClick(data) {
  selectedNodeId.value = data.id
  selectedNode.value = data
}

function translationStatusLabel(issue) {
  if (issue?.source_type === 'domestic') return '不需要'
  return issue?.translation_status === 'completed' ? '已完成' : '未完成'
}

function translationTagClass(issue) {
  if (issue?.source_type === 'domestic') return 'status-chip--translation-na'
  return issue?.translation_status === 'completed'
    ? 'status-chip--translation-done'
    : 'status-chip--translation-pending'
}

function analysisTagClass(issue) {
  return issue?.analysis_status === 'completed'
    ? 'status-chip--analysis-done'
    : 'status-chip--analysis-pending'
}

watch([sourceFilter, treeData], () => {
  if (!selectedNodeId.value) return
  const next = findNodeById(treeData.value, selectedNodeId.value)
  if (!next) {
    selectedNodeId.value = ''
    selectedNode.value = null
    return
  }
  selectedNode.value = next
})

onMounted(async () => {
  await crawlerStore.fetchRawIssues()
})
</script>

<style scoped>
.archive-tree {
  background: transparent;
}

.archive-tree :deep(.el-tree-node__content) {
  height: auto;
  min-height: 44px;
  border-radius: 12px;
  margin-bottom: 4px;
  padding-right: 8px;
}

.archive-tree :deep(.el-tree-node__content:hover) {
  background: rgba(241, 245, 249, 0.9);
}

.archive-tree :deep(.is-current > .el-tree-node__content) {
  background: rgba(219, 234, 254, 0.82);
}

.status-chip {
  border: 1px solid transparent;
  font-weight: 600;
}

.status-chip--source-domestic {
  border-color: rgba(14, 116, 144, 0.28);
  background: rgba(103, 232, 249, 0.2);
  color: rgb(12, 74, 110);
}

.status-chip--source-foreign {
  border-color: rgba(109, 40, 217, 0.28);
  background: rgba(196, 181, 253, 0.2);
  color: rgb(91, 33, 182);
}

.status-chip--translation-na {
  border-color: rgba(100, 116, 139, 0.28);
  background: rgba(148, 163, 184, 0.16);
  color: rgb(71, 85, 105);
}

.status-chip--translation-done {
  border-color: rgba(5, 150, 105, 0.3);
  background: rgba(110, 231, 183, 0.2);
  color: rgb(4, 120, 87);
}

.status-chip--translation-pending {
  border-color: rgba(217, 119, 6, 0.34);
  background: rgba(253, 230, 138, 0.32);
  color: rgb(146, 64, 14);
}

.status-chip--analysis-done {
  border-color: rgba(30, 64, 175, 0.3);
  background: rgba(147, 197, 253, 0.22);
  color: rgb(30, 64, 175);
}

.status-chip--analysis-pending {
  border-color: rgba(220, 38, 38, 0.28);
  background: rgba(254, 202, 202, 0.28);
  color: rgb(153, 27, 27);
}

.status-chip--paper-count {
  border-color: rgba(51, 65, 85, 0.24);
  background: rgba(226, 232, 240, 0.44);
  color: rgb(51, 65, 85);
}
</style>
