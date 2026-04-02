<template>
  <div class="page-shell">
    <section class="page-hero">
      <div class="page-hero__body lg:grid-cols-[1.5fr_0.9fr]">
        <div>
          <div class="page-eyebrow">
            <span>Research Desk</span>
            <span class="h-1 w-1 rounded-full bg-slate-400"></span>
            <span>Overview</span>
          </div>
          <h2 class="page-title">文献工作台</h2>
          <p class="page-subtitle">
            在一个视图里看清文献总量、阅读节奏、语言结构和近期新增。这个页面不只是概览，更是你继续推进阅读和整理的起点。
          </p>
        </div>

        <div class="hero-meta-grid self-start">
          <div class="hero-meta-tile">
            <div class="hero-meta-label">Library Size</div>
            <div class="hero-meta-value">{{ stats.total || 0 }}</div>
          </div>
          <div class="hero-meta-tile">
            <div class="hero-meta-label">Completed</div>
            <div class="hero-meta-value">{{ completedCount }}</div>
          </div>
          <div class="hero-meta-tile">
            <div class="hero-meta-label">In Progress</div>
            <div class="hero-meta-value">{{ readingCount }}</div>
          </div>
          <div class="hero-meta-tile">
            <div class="hero-meta-label">Unread</div>
            <div class="hero-meta-value">{{ unreadCount }}</div>
          </div>
        </div>
      </div>
    </section>

    <section class="stats-grid">
      <article class="stat-panel">
        <div class="stat-panel__label">文献总数</div>
        <div class="stat-panel__value">{{ stats.total || 0 }}</div>
        <p class="stat-panel__caption">当前数据库内全部正式文献记录。</p>
      </article>

      <article class="stat-panel">
        <div class="stat-panel__label">已读完成</div>
        <div class="stat-panel__value">{{ completedCount }}</div>
        <p class="stat-panel__caption">已经完成深读或整理的文献数量。</p>
      </article>

      <article class="stat-panel">
        <div class="stat-panel__label">正在阅读</div>
        <div class="stat-panel__value">{{ readingCount }}</div>
        <p class="stat-panel__caption">当前仍在推进中的阅读任务。</p>
      </article>

      <article class="stat-panel">
        <div class="stat-panel__label">摘要浏览/未读</div>
        <div class="stat-panel__value">{{ skimCount + unreadCount }}</div>
        <p class="stat-panel__caption">适合继续筛选和安排下一步阅读优先级。</p>
      </article>
    </section>

    <section class="surface-panel">
      <div class="surface-panel__header">
        <div>
          <h3 class="surface-panel__title">阅读节奏提示</h3>
          <p class="surface-panel__caption">从状态结构里直接看当前工作重心。</p>
        </div>
        <el-button type="primary" size="large" @click="$router.push('/literatures/new')">
          <template #icon>
            <el-icon><Plus /></el-icon>
          </template>
          添加文献
        </el-button>
      </div>

      <div class="insight-strip">
        <div class="insight-chip">
          <el-icon><Reading /></el-icon>
          <span>当前重点：<strong>{{ readingFocusText }}</strong></span>
        </div>
        <div class="insight-chip">
          <el-icon><CollectionTag /></el-icon>
          <span>语言分布：<strong>{{ languageMixText }}</strong></span>
        </div>
        <div class="insight-chip">
          <el-icon><Histogram /></el-icon>
          <span>近期新增：<strong>{{ latestMonthText }}</strong></span>
        </div>
      </div>
    </section>

    <section class="content-grid-2">
      <article class="surface-panel">
        <div class="surface-panel__header">
          <div>
            <h3 class="surface-panel__title">阅读状态分布</h3>
            <p class="surface-panel__caption">看清哪些文献已经完成，哪些还停留在筛选阶段。</p>
          </div>
        </div>
        <div ref="statusChartRef" class="chart-surface"></div>
      </article>

      <article class="surface-panel">
        <div class="surface-panel__header">
          <div>
            <h3 class="surface-panel__title">语言结构</h3>
            <p class="surface-panel__caption">中文与英文文献的占比，帮助判断检索和阅读路径。</p>
          </div>
        </div>
        <div ref="languageChartRef" class="chart-surface"></div>
      </article>
    </section>

    <section class="surface-panel table-shell">
      <div class="surface-panel__header">
        <div>
          <h3 class="surface-panel__title">最近新增文献</h3>
          <p class="surface-panel__caption">最近进入正式文献库的记录，适合快速继续处理。</p>
        </div>
        <el-button link type="primary" @click="$router.push('/literatures')">
          查看全部
          <el-icon class="ml-1"><ArrowRight /></el-icon>
        </el-button>
      </div>

      <el-table :data="recentLiteratures" style="width: 100%">
        <el-table-column prop="title" label="标题" min-width="320">
          <template #default="{ row }">
            <router-link
              :to="`/literatures/${row.id}`"
              class="line-clamp-2 text-[15px] font-semibold text-slate-900 no-underline transition-colors hover:text-slate-700"
            >
              {{ row.title }}
            </router-link>
          </template>
        </el-table-column>

        <el-table-column prop="authors" label="作者" min-width="220">
          <template #default="{ row }">
            <span class="line-clamp-1 text-sm text-slate-500">{{ row.authors || '未填写' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="year" label="年份" width="100" align="center">
          <template #default="{ row }">
            <span class="rounded-full bg-slate-100 px-3 py-1 text-sm font-semibold text-slate-700">
              {{ row.year || '-' }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="140" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" effect="light" round>
              {{ row.status || '未读' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="添加时间" width="150" align="right">
          <template #default="{ row }">
            <span class="text-sm text-slate-400">{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useLiteratureStore } from '@/stores/literature'
import {
  ArrowRight,
  CollectionTag,
  Histogram,
  Plus,
  Reading
} from '@element-plus/icons-vue'
import echarts from '@/lib/echarts'

const literatureStore = useLiteratureStore()
const stats = ref({})
const recentLiteratures = ref([])
const statusChartRef = ref(null)
const languageChartRef = ref(null)

let statusChart = null
let languageChart = null

const completedCount = computed(() => stats.value.by_status?.['已读完'] || 0)
const readingCount = computed(() => stats.value.by_status?.['正在阅读'] || 0)
const unreadCount = computed(() => stats.value.by_status?.['未读'] || 0)
const skimCount = computed(() => stats.value.by_status?.['摘要浏览'] || 0)
const zhCount = computed(() => stats.value.by_language?.zh || 0)
const enCount = computed(() => stats.value.by_language?.en || 0)

const readingFocusText = computed(() => {
  if (readingCount.value > completedCount.value) return '正在阅读占比较高'
  if (unreadCount.value > readingCount.value) return '待筛选文献仍然较多'
  return '已读积累更稳定'
})

const languageMixText = computed(() => `中文 ${zhCount.value} / 英文 ${enCount.value}`)

const latestMonthText = computed(() => {
  const latest = stats.value.monthly?.at?.(-1)
  if (!latest) return '暂无月度趋势数据'
  return `${latest.month} 新增 ${latest.count} 篇`
})

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

const getStatusType = (status) => {
  const types = {
    未读: 'info',
    摘要浏览: 'warning',
    正在阅读: 'primary',
    已读完: 'success',
    需要重读: 'danger'
  }
  return types[status] || 'info'
}

const buildChart = (target, option) => {
  if (!target) return null
  const chart = echarts.init(target)
  chart.setOption(option)
  return chart
}

const initStatusChart = () => {
  const statusData = Object.entries(stats.value.by_status || {}).map(([name, value]) => ({ name, value }))
  statusChart?.dispose()
  statusChart = buildChart(statusChartRef.value, {
    tooltip: { trigger: 'item' },
    legend: {
      bottom: 0,
      left: 'center',
      icon: 'circle',
      textStyle: { color: '#64748b' }
    },
    color: ['#0f172a', '#0f766e', '#2563eb', '#f59e0b', '#dc2626'],
    series: [
      {
        type: 'pie',
        radius: ['48%', '72%'],
        center: ['50%', '44%'],
        itemStyle: {
          borderRadius: 12,
          borderColor: '#f8fafc',
          borderWidth: 3
        },
        label: { show: false },
        emphasis: {
          label: {
            show: true,
            color: '#0f172a',
            fontWeight: 'bold',
            formatter: '{b}\n{c} 篇'
          }
        },
        labelLine: { show: false },
        data: statusData
      }
    ]
  })
}

const initLanguageChart = () => {
  const languageData = [
    { name: '中文', value: zhCount.value },
    { name: '英文', value: enCount.value }
  ].filter(item => item.value > 0)

  languageChart?.dispose()
  languageChart = buildChart(languageChartRef.value, {
    tooltip: { trigger: 'item' },
    legend: {
      bottom: 0,
      left: 'center',
      icon: 'circle',
      textStyle: { color: '#64748b' }
    },
    color: ['#14b8a6', '#334155'],
    series: [
      {
        type: 'pie',
        radius: ['34%', '70%'],
        center: ['50%', '44%'],
        itemStyle: {
          borderRadius: 12,
          borderColor: '#f8fafc',
          borderWidth: 3
        },
        label: {
          color: '#475569',
          formatter: '{b}\n{d}%'
        },
        data: languageData
      }
    ]
  })
}

const handleResize = () => {
  statusChart?.resize()
  languageChart?.resize()
}

onMounted(async () => {
  stats.value = await literatureStore.fetchStatistics()
  const result = await literatureStore.fetchLiteratures({ page: 1, per_page: 5 })
  recentLiteratures.value = result.items

  await nextTick()
  initStatusChart()
  initLanguageChart()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  statusChart?.dispose()
  languageChart?.dispose()
})
</script>
