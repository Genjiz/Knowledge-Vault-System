<template>
  <div class="page-shell">
    <section class="page-hero">
      <div class="page-hero__body lg:grid-cols-[1.4fr_1fr]">
        <div>
          <div class="page-eyebrow">
            <span>Insight Atlas</span>
            <span class="h-1 w-1 rounded-full bg-slate-400"></span>
            <span>Analytics</span>
          </div>
          <h2 class="page-title">统计分析</h2>
          <p class="page-subtitle">
            从阅读状态、语言结构和月度新增趋势三个角度看文献库的积累节奏，帮助你决定下一步检索、阅读和整理重点。
          </p>
        </div>

        <div class="hero-meta-grid self-start">
          <div class="hero-meta-tile">
            <div class="hero-meta-label">Total</div>
            <div class="hero-meta-value">{{ stats.total || 0 }}</div>
          </div>
          <div class="hero-meta-tile">
            <div class="hero-meta-label">Chinese</div>
            <div class="hero-meta-value">{{ zhCount }}</div>
          </div>
          <div class="hero-meta-tile">
            <div class="hero-meta-label">English</div>
            <div class="hero-meta-value">{{ enCount }}</div>
          </div>
          <div class="hero-meta-tile">
            <div class="hero-meta-label">Latest Month</div>
            <div class="hero-meta-value">{{ latestMonthCount }}</div>
          </div>
        </div>
      </div>
    </section>

    <section class="stats-grid">
      <article class="stat-panel">
        <div class="stat-panel__label">正式文献</div>
        <div class="stat-panel__value">{{ stats.total || 0 }}</div>
        <p class="stat-panel__caption">当前主文献库中的全部正式记录。</p>
      </article>

      <article class="stat-panel">
        <div class="stat-panel__label">已读完成</div>
        <div class="stat-panel__value">{{ completedCount }}</div>
        <p class="stat-panel__caption">完成深读并留在正式库中的文献。</p>
      </article>

      <article class="stat-panel">
        <div class="stat-panel__label">中文文献</div>
        <div class="stat-panel__value">{{ zhCount }}</div>
        <p class="stat-panel__caption">当前中文语料积累规模。</p>
      </article>

      <article class="stat-panel">
        <div class="stat-panel__label">英文文献</div>
        <div class="stat-panel__value">{{ enCount }}</div>
        <p class="stat-panel__caption">当前英文语料积累规模。</p>
      </article>
    </section>

    <section class="content-grid-2">
      <article class="surface-panel">
        <div class="surface-panel__header">
          <div>
            <h3 class="surface-panel__title">阅读状态分布</h3>
            <p class="surface-panel__caption">判断文献库更偏“积压待读”还是“已形成稳定消化”。</p>
          </div>
        </div>
        <div ref="statusChartRef" class="chart-surface"></div>
      </article>

      <article class="surface-panel">
        <div class="surface-panel__header">
          <div>
            <h3 class="surface-panel__title">语言结构</h3>
            <p class="surface-panel__caption">衡量中文与英文文献的覆盖比例。</p>
          </div>
        </div>
        <div ref="languageChartRef" class="chart-surface"></div>
      </article>
    </section>

    <section class="surface-panel">
      <div class="surface-panel__header">
        <div>
          <h3 class="surface-panel__title">月度新增趋势</h3>
          <p class="surface-panel__caption">观察你的文献收集是否稳定，是否存在明显的阶段性输入高峰。</p>
        </div>
      </div>
      <div ref="trendChartRef" class="chart-surface chart-surface--lg"></div>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useLiteratureStore } from '@/stores/literature'
import echarts from '@/lib/echarts'

const literatureStore = useLiteratureStore()
const stats = ref({})

const statusChartRef = ref(null)
const languageChartRef = ref(null)
const trendChartRef = ref(null)

let statusChart = null
let languageChart = null
let trendChart = null

const completedCount = computed(() => stats.value.by_status?.['已读完'] || 0)
const zhCount = computed(() => stats.value.by_language?.zh || 0)
const enCount = computed(() => stats.value.by_language?.en || 0)
const latestMonthCount = computed(() => {
  const monthly = stats.value.monthly || []
  return monthly.length ? monthly[monthly.length - 1].count : 0
})

const buildChart = (target, option) => {
  if (!target) return null
  const chart = echarts.init(target)
  chart.setOption(option)
  return chart
}

const initStatusChart = () => {
  const data = Object.entries(stats.value.by_status || {}).map(([name, value]) => ({ name, value }))
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
        radius: ['46%', '72%'],
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
        data
      }
    ]
  })
}

const initLanguageChart = () => {
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
        data: [
          { name: '中文', value: zhCount.value },
          { name: '英文', value: enCount.value }
        ].filter(item => item.value > 0)
      }
    ]
  })
}

const initTrendChart = () => {
  const monthlyData = stats.value.monthly || []
  trendChart?.dispose()
  trendChart = buildChart(trendChartRef.value, {
    tooltip: { trigger: 'axis' },
    grid: {
      left: 36,
      right: 18,
      top: 30,
      bottom: 36
    },
    xAxis: {
      type: 'category',
      data: monthlyData.map(item => item.month),
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#cbd5e1' } },
      axisLabel: { color: '#64748b' }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(226, 232, 240, 0.8)' } },
      axisLabel: { color: '#64748b' }
    },
    series: [
      {
        data: monthlyData.map(item => item.count),
        type: 'line',
        smooth: true,
        symbolSize: 8,
        lineStyle: {
          width: 3,
          color: '#0f172a'
        },
        itemStyle: {
          color: '#0f172a',
          borderColor: '#e2e8f0',
          borderWidth: 2
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(15, 23, 42, 0.24)' },
            { offset: 1, color: 'rgba(15, 23, 42, 0.03)' }
          ])
        }
      }
    ]
  })
}

const handleResize = () => {
  statusChart?.resize()
  languageChart?.resize()
  trendChart?.resize()
}

onMounted(async () => {
  stats.value = await literatureStore.fetchStatistics()
  await nextTick()
  initStatusChart()
  initLanguageChart()
  initTrendChart()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  statusChart?.dispose()
  languageChart?.dispose()
  trendChart?.dispose()
})
</script>
