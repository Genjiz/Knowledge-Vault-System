<template>
  <section v-loading="crawlerStore.loading" class="space-y-6">
    <el-alert
      v-if="loadError"
      type="error"
      show-icon
      :closable="false"
      :title="loadError"
      class="rounded-2xl"
    />

    <header class="relative overflow-hidden rounded-[30px] border border-slate-200/80 bg-[linear-gradient(135deg,rgba(255,255,255,0.98),rgba(241,245,249,0.9))] px-8 py-8 shadow-[0_30px_80px_-40px_rgba(15,23,42,0.38)]">
      <div class="pointer-events-none absolute -right-12 -top-12 h-36 w-36 rounded-full bg-sky-100/80 blur-2xl" />
      <div class="pointer-events-none absolute -left-16 bottom-0 h-32 w-32 rounded-full bg-emerald-100/70 blur-2xl" />
      <div class="relative flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div class="space-y-2">
          <p class="text-xs uppercase tracking-[0.35em] text-slate-500">Issue Workspace</p>
          <h2 class="text-3xl font-black tracking-tight text-slate-950">{{ issue?.journal_name || '-' }}</h2>
          <p class="text-sm text-slate-600">
            {{ issue?.year }} / 第{{ issue?.issue }}期{{ issue?.volume ? ` · Vol.${issue.volume}` : '' }}
          </p>
        </div>
        <div class="flex justify-start lg:justify-end">
          <el-button
            class="rounded-2xl border-slate-300 bg-white/90 px-5 text-slate-700 shadow-[0_14px_32px_-24px_rgba(15,23,42,0.6)] hover:border-slate-400"
            @click="$router.push('/crawler/issues')"
          >
            返回采集期号库
          </el-button>
        </div>
      </div>
    </header>

    <el-card class="rounded-[28px] border border-slate-200/80 !shadow-[0_24px_64px_-36px_rgba(15,23,42,0.28)]">
      <div class="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-center">
        <div class="flex flex-wrap gap-3">
          <div v-if="issue?.source_type" class="inline-flex items-center gap-2 rounded-full bg-slate-100 px-4 py-2 text-sm text-slate-700">
            <span class="text-slate-400">采集源</span>
            <span class="font-semibold text-slate-900">{{ issue.source_type }}</span>
          </div>
          <div class="inline-flex items-center gap-2 rounded-full bg-slate-100 px-4 py-2 text-sm text-slate-700">
            <span class="text-slate-400">论文数</span>
            <span class="font-semibold text-slate-900">{{ issue?.paper_count ?? 0 }}</span>
          </div>
          <div v-if="!isDomestic" class="inline-flex items-center gap-2 rounded-full bg-slate-100 px-4 py-2 text-sm text-slate-700">
            <span class="text-slate-400">卷号</span>
            <span class="font-semibold text-slate-900">{{ issue?.volume || '-' }}</span>
          </div>
          <div v-if="!isDomestic" class="inline-flex items-center gap-2 rounded-full bg-emerald-50 px-4 py-2 text-sm text-emerald-700">
            <span class="text-emerald-500">翻译</span>
            <span class="font-semibold">{{ issueTranslationStatusLabel }}</span>
          </div>
          <div class="inline-flex items-center gap-2 rounded-full bg-sky-50 px-4 py-2 text-sm text-sky-700">
            <span class="text-sky-500">分析</span>
            <span class="font-semibold">{{ issueAnalysisStatusLabel }}</span>
          </div>
        </div>
        <a
          v-if="issue?.source_url"
          :href="issue.source_url"
          target="_blank"
          class="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm text-slate-700 transition hover:-translate-y-0.5 hover:border-slate-400"
        >
          打开来源页面
        </a>
      </div>
    </el-card>

    <el-card class="rounded-[28px] border border-slate-200/80 !shadow-[0_24px_64px_-36px_rgba(15,23,42,0.28)]">
      <el-tabs v-model="activeTab" class="issue-detail-tabs">
        <el-tab-pane label="论文" name="papers">
          <div class="space-y-4">
            <div class="flex items-center justify-between gap-4">
              <div>
                <div class="text-xs uppercase tracking-[0.3em] text-slate-400">Paper Ledger</div>
                <div class="mt-1 text-xl font-bold text-slate-900">论文详情</div>
              </div>
              <div class="flex flex-wrap items-center justify-end gap-3">
                <el-button
                  v-if="!isDomestic"
                  type="primary"
                  class="rounded-xl border-0 bg-slate-950 shadow-[0_14px_32px_-22px_rgba(15,23,42,0.7)]"
                  :loading="translating"
                  :disabled="translating"
                  @click="translateIssue"
                >
                  翻译本期
                </el-button>
                <el-radio-group v-if="!isDomestic" v-model="displayLang" size="small">
                  <el-radio-button label="zh">中文</el-radio-button>
                  <el-radio-button label="en">English</el-radio-button>
                </el-radio-group>
                <div class="text-sm text-slate-500">共 {{ issue?.papers?.length || 0 }} 篇</div>
              </div>
            </div>

            <div class="max-h-[calc(100vh-250px)] overflow-y-auto pr-1">
              <el-collapse v-model="activePanels">
                <el-collapse-item
                  v-for="(paper, paperIndex) in issue?.papers || []"
                  :key="paper.id"
                  :name="String(paper.id)"
                  class="mb-3 overflow-hidden rounded-2xl border border-slate-200 bg-white px-2 shadow-[0_14px_30px_-24px_rgba(15,23,42,0.42)]"
                >
                  <template #title>
                    <div class="mr-3 min-w-0 py-3">
                      <div class="flex items-center gap-3">
                        <span class="inline-flex h-6 items-center rounded-full bg-slate-100 px-2 text-[11px] font-semibold text-slate-500">
                          #{{ paperIndex + 1 }}
                        </span>
                        <div class="truncate text-sm font-semibold text-slate-900">
                          {{ paperTitle(paper) }}
                        </div>
                      </div>
                      <div class="mt-1 truncate text-xs text-slate-500">{{ paper.authors || '作者信息缺失' }}</div>
                    </div>
                  </template>

                  <div class="space-y-3 pb-4 text-sm text-slate-700">
                    <p class="rounded-lg border border-slate-200 bg-white p-3 leading-7">
                      <span class="font-semibold text-slate-900">{{ abstractLabel }}</span>
                      {{ paperAbstract(paper) }}
                    </p>
                    <div class="flex flex-wrap items-center gap-3 text-xs text-slate-500">
                      <el-tag v-if="!isDomestic" :type="paper.translation_status === 'completed' ? 'success' : 'warning'" round>
                        {{ paper.translation_status === 'completed' ? '已翻译' : '待翻译' }}
                      </el-tag>
                      <a v-if="paper.detail_url" :href="paper.detail_url" target="_blank" class="text-slate-700 underline underline-offset-4">
                        论文原文链接
                      </a>
                    </div>
                  </div>
                </el-collapse-item>
              </el-collapse>
              <el-empty v-if="!(issue?.papers?.length > 0)" description="当前期号暂无论文记录" />
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="分析" name="analysis">
          <div class="space-y-4">
            <div class="flex items-center justify-between gap-4">
              <div>
                <div class="text-xs uppercase tracking-[0.3em] text-slate-400">Analysis Brief</div>
                <div class="mt-1 text-xl font-bold text-slate-900">期号分析</div>
              </div>
              <div class="flex flex-wrap items-center justify-end gap-3">
                <el-tag v-if="analysis" type="success" round>{{ analysis.status }}</el-tag>
                <el-button
                  type="primary"
                  class="rounded-xl border-0 bg-slate-950 shadow-[0_14px_32px_-22px_rgba(15,23,42,0.7)]"
                  :loading="analyzing"
                  :disabled="analyzing"
                  @click="generateAnalysis"
                >
                  {{ analysis ? '重新生成分析' : '生成分析' }}
                </el-button>
              </div>
            </div>

            <el-empty v-if="!analysis" description="还没有分析结果，请点击“生成分析”" />
            <div v-else class="max-h-[calc(100vh-250px)] overflow-y-auto pr-1">
              <article
                class="analysis-markdown max-w-none text-sm leading-8 text-slate-700"
                v-html="renderedMarkdown"
              />
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useCrawlerStore } from '@/stores/crawler'

const route = useRoute()
const router = useRouter()
const crawlerStore = useCrawlerStore()
const issue = computed(() => crawlerStore.currentIssue)
const analysis = computed(() => crawlerStore.currentAnalysis)
const activePanels = ref([])
const loadError = ref('')
const displayLang = ref('en')
const activeTab = ref(route.query.tab === 'analysis' ? 'analysis' : 'papers')
const translating = ref(false)
const analyzing = ref(false)

// 区域决定翻译相关 UI 的显隐：国内期刊题录本就是中文，无需翻译
const isDomestic = computed(() => issue.value?.region === 'domestic')
const issueTranslationStatusLabel = computed(() => {
  if (isDomestic.value) return '不需要'
  return issue.value?.translation_status === 'completed' ? '已完成' : '未完成'
})
const issueAnalysisStatusLabel = computed(() => (
  issue.value?.analysis_status === 'completed' ? '已生成' : '未生成'
))
const abstractLabel = computed(() => (displayLang.value === 'zh' ? '摘要：' : 'Abstract: '))
const renderedMarkdown = computed(() => renderMarkdownToHtml(analysis.value?.content_markdown || ''))

watch(
  () => route.query.tab,
  tab => {
    const nextTab = tab === 'analysis' ? 'analysis' : 'papers'
    if (nextTab !== activeTab.value) activeTab.value = nextTab
  }
)

watch(activeTab, async tab => {
  const currentTab = route.query.tab === 'analysis' ? 'analysis' : 'papers'
  if (currentTab !== tab) {
    const nextQuery = { ...route.query }
    if (tab === 'analysis') nextQuery.tab = 'analysis'
    else delete nextQuery.tab
    router.replace({ query: nextQuery }).catch(() => {})
  }
  if (tab === 'analysis') {
    try {
      await ensureAnalysisLoaded()
    } catch (error) {
      ElMessage.error(error?.message || '分析数据加载失败，请稍后重试')
    }
  }
})

watch(
  () => issue.value?.papers,
  () => {
    activePanels.value = []
  },
  { immediate: true }
)

watch(isDomestic, value => {
  if (value) {
    displayLang.value = 'zh'
    return
  }
  displayLang.value = issue.value?.translation_status === 'completed' ? 'zh' : 'en'
})

function paperTitle(paper) {
  if (isDomestic.value) return paper?.title || '暂无标题'
  if (displayLang.value === 'zh') return paper?.title_zh || '暂无中文标题'
  return paper?.title || 'No title'
}

function paperAbstract(paper) {
  if (isDomestic.value) return paper?.abstract || '暂无摘要'
  if (displayLang.value === 'zh') return paper?.abstract_zh || '暂无中文摘要'
  return paper?.abstract || 'No abstract'
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function sanitizeHref(url) {
  const trimmed = String(url || '').trim()
  if (/^(https?:\/\/|mailto:)/i.test(trimmed)) {
    return trimmed.replace(/"/g, '%22')
  }
  return ''
}

function renderInlineMarkdown(text) {
  let html = escapeHtml(text)
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>')
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, label, rawUrl) => {
    const href = sanitizeHref(rawUrl)
    if (!href) return label
    return `<a href="${href}" target="_blank" rel="noopener noreferrer">${label}</a>`
  })
  return html
}

function parseTableCells(row) {
  const normalized = String(row || '')
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
  if (!normalized) return []
  return normalized.split('|').map(cell => cell.trim())
}

function isMarkdownTableRow(row) {
  const trimmed = String(row || '').trim()
  if (!trimmed.includes('|')) return false
  return parseTableCells(trimmed).length > 1
}

function isMarkdownTableDivider(row) {
  const cells = parseTableCells(row)
  return cells.length > 0 && cells.every(cell => /^:?-{3,}:?$/.test(cell))
}

function renderMarkdownToHtml(markdown) {
  const lines = String(markdown || '').replace(/\r\n/g, '\n').split('\n')
  const html = []
  let listType = null
  let codeBlock = null
  let tableBuffer = []

  const closeList = () => {
    if (!listType) return
    html.push(listType === 'ol' ? '</ol>' : '</ul>')
    listType = null
  }

  const flushCodeBlock = () => {
    if (!codeBlock) return
    html.push(`<pre><code>${escapeHtml(codeBlock.join('\n'))}</code></pre>`)
    codeBlock = null
  }

  const flushTable = () => {
    if (!tableBuffer.length) return

    const headerCells = parseTableCells(tableBuffer[0])
    if (!headerCells.length) {
      tableBuffer = []
      return
    }

    let bodyStartIndex = 1
    if (tableBuffer.length > 1 && isMarkdownTableDivider(tableBuffer[1])) {
      bodyStartIndex = 2
    }

    const thead = `<thead><tr>${headerCells
      .map(cell => `<th>${renderInlineMarkdown(cell)}</th>`)
      .join('')}</tr></thead>`

    const tbodyRows = tableBuffer.slice(bodyStartIndex).map(row => {
      const cells = parseTableCells(row)
      const normalizedCells = headerCells.map((_, index) => cells[index] || '')
      return `<tr>${normalizedCells
        .map(cell => `<td>${renderInlineMarkdown(cell)}</td>`)
        .join('')}</tr>`
    })
    const tbody = `<tbody>${tbodyRows.join('')}</tbody>`

    html.push(`<div class="md-table-wrap"><table>${thead}${tbody}</table></div>`)
    tableBuffer = []
  }

  for (const rawLine of lines) {
    const line = rawLine ?? ''
    const trimmed = line.trim()

    if (trimmed.startsWith('```')) {
      if (codeBlock) {
        flushCodeBlock()
      } else {
        flushTable()
        closeList()
        codeBlock = []
      }
      continue
    }

    if (codeBlock) {
      codeBlock.push(line)
      continue
    }

    if (isMarkdownTableRow(trimmed)) {
      closeList()
      tableBuffer.push(trimmed)
      continue
    }

    flushTable()

    if (!trimmed) {
      closeList()
      continue
    }

    const headingMatch = trimmed.match(/^(#{1,6})\s+(.+)$/)
    if (headingMatch) {
      closeList()
      const level = headingMatch[1].length
      html.push(`<h${level}>${renderInlineMarkdown(headingMatch[2])}</h${level}>`)
      continue
    }

    if (/^---+$/.test(trimmed)) {
      closeList()
      html.push('<hr />')
      continue
    }

    const unorderedMatch = trimmed.match(/^[-*+]\s+(.+)$/)
    if (unorderedMatch) {
      if (listType !== 'ul') {
        closeList()
        html.push('<ul>')
        listType = 'ul'
      }
      html.push(`<li>${renderInlineMarkdown(unorderedMatch[1])}</li>`)
      continue
    }

    const orderedMatch = trimmed.match(/^\d+\.\s+(.+)$/)
    if (orderedMatch) {
      if (listType !== 'ol') {
        closeList()
        html.push('<ol>')
        listType = 'ol'
      }
      html.push(`<li>${renderInlineMarkdown(orderedMatch[1])}</li>`)
      continue
    }

    const quoteMatch = trimmed.match(/^>\s?(.+)$/)
    if (quoteMatch) {
      closeList()
      html.push(`<blockquote>${renderInlineMarkdown(quoteMatch[1])}</blockquote>`)
      continue
    }

    closeList()
    html.push(`<p>${renderInlineMarkdown(trimmed)}</p>`)
  }

  flushTable()
  flushCodeBlock()
  closeList()
  return html.join('\n')
}

async function translateIssue() {
  translating.value = true
  ElMessage.info('正在翻译本期论文，请稍候...')
  try {
    const result = await crawlerStore.translateIssue(route.params.id)
    if (result?.backgroundRunning) {
      ElMessage.warning('翻译请求已发出，后台仍在执行。请稍后刷新查看结果。')
      return
    }
    ElMessage.success('翻译完成')
  } catch (error) {
    ElMessage.error(error?.message || '翻译失败，请稍后重试')
  } finally {
    translating.value = false
  }
}

async function ensureAnalysisLoaded() {
  try {
    await crawlerStore.fetchAnalysis(route.params.id)
  } catch (error) {
    if (error?.response?.status === 404) {
      crawlerStore.currentAnalysis = null
      return
    }
    throw error
  }
}

async function generateAnalysis() {
  analyzing.value = true
  ElMessage.info('正在生成分析，请稍候...')
  try {
    const result = await crawlerStore.analyzeIssue(route.params.id)
    if (result?.backgroundRunning) {
      ElMessage.warning('分析请求已发出，后台仍在执行。请稍后刷新查看结果。')
      return
    }
    ElMessage.success('分析结果已生成')
  } catch (error) {
    ElMessage.error(error?.message || '分析生成失败，请稍后重试')
  } finally {
    analyzing.value = false
  }
}

onMounted(async () => {
  try {
    loadError.value = ''
    crawlerStore.currentAnalysis = null
    await crawlerStore.fetchRawIssue(route.params.id)
    if (isDomestic.value) {
      displayLang.value = 'zh'
    } else {
      displayLang.value = issue.value?.translation_status === 'completed' ? 'zh' : 'en'
    }
    if (activeTab.value === 'analysis') {
      await ensureAnalysisLoaded()
    }
  } catch (error) {
    loadError.value = error?.message || '期号详情加载失败，请稍后重试。'
  }
})
</script>

<style scoped>
.issue-detail-tabs :deep(.el-tabs__header) {
  margin-bottom: 1.25rem;
}

.issue-detail-tabs :deep(.el-tabs__item) {
  padding: 0 1.1rem;
  font-weight: 600;
}

.analysis-markdown :deep(h1),
.analysis-markdown :deep(h2),
.analysis-markdown :deep(h3),
.analysis-markdown :deep(h4) {
  margin: 1.25rem 0 0.75rem;
  font-weight: 700;
  color: rgb(15 23 42);
  line-height: 1.35;
}

.analysis-markdown :deep(h1) {
  font-size: 1.5rem;
}

.analysis-markdown :deep(h2) {
  font-size: 1.25rem;
}

.analysis-markdown :deep(h3) {
  font-size: 1.1rem;
}

.analysis-markdown :deep(p) {
  margin: 0.75rem 0;
}

.analysis-markdown :deep(ul),
.analysis-markdown :deep(ol) {
  margin: 0.75rem 0;
  padding-left: 1.25rem;
}

.analysis-markdown :deep(li) {
  margin: 0.3rem 0;
}

.analysis-markdown :deep(code) {
  border-radius: 0.5rem;
  background: rgba(15, 23, 42, 0.08);
  padding: 0.12rem 0.4rem;
  font-family: Consolas, Monaco, monospace;
  font-size: 0.85em;
}

.analysis-markdown :deep(pre) {
  margin: 0.9rem 0;
  overflow-x: auto;
  border-radius: 0.85rem;
  border: 1px solid rgba(148, 163, 184, 0.3);
  background: rgba(15, 23, 42, 0.9);
  padding: 0.85rem 1rem;
}

.analysis-markdown :deep(pre code) {
  background: transparent;
  color: #e2e8f0;
  padding: 0;
}

.analysis-markdown :deep(blockquote) {
  margin: 0.9rem 0;
  border-left: 3px solid rgba(15, 23, 42, 0.22);
  background: rgba(148, 163, 184, 0.12);
  padding: 0.6rem 0.9rem;
  color: rgb(51 65 85);
}

.analysis-markdown :deep(a) {
  color: rgb(14 116 144);
  text-decoration: underline;
}

.analysis-markdown :deep(hr) {
  margin: 1.1rem 0;
  border: none;
  border-top: 1px solid rgba(148, 163, 184, 0.35);
}

.analysis-markdown :deep(.md-table-wrap) {
  margin: 1rem 0;
  overflow-x: auto;
  border-radius: 0.9rem;
  border: 1px solid rgba(148, 163, 184, 0.3);
  background: #fff;
}

.analysis-markdown :deep(table) {
  width: 100%;
  border-collapse: collapse;
  min-width: 680px;
}

.analysis-markdown :deep(th),
.analysis-markdown :deep(td) {
  border-bottom: 1px solid rgba(226, 232, 240, 0.9);
  padding: 0.65rem 0.75rem;
  text-align: left;
  vertical-align: top;
}

.analysis-markdown :deep(th) {
  background: rgba(248, 250, 252, 0.95);
  font-weight: 700;
  color: rgb(15 23 42);
}

.analysis-markdown :deep(tbody tr:last-child td) {
  border-bottom: none;
}
</style>
