<template>
  <section class="space-y-6" v-loading="crawlerStore.loading">
    <header class="rounded-[28px] border border-slate-200/70 bg-[linear-gradient(135deg,rgba(15,23,42,0.98),rgba(30,41,59,0.94))] px-8 py-8 text-white shadow-[0_30px_80px_-36px_rgba(15,23,42,0.65)]">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p class="text-xs uppercase tracking-[0.35em] text-slate-400">Research Brief</p>
          <h2 class="mt-2 text-3xl font-black tracking-tight">{{ issue?.journal_name }}</h2>
          <p class="mt-2 text-sm text-slate-300">{{ issue?.year }} / 第 {{ issue?.issue }} 期分析结果</p>
        </div>
        <div class="flex gap-3">
          <el-button class="rounded-2xl border-white/20 bg-white/10 text-white hover:bg-white/20" @click="$router.push(`/crawler/issues/${route.params.id}`)">
            返回期号
          </el-button>
          <el-button
            type="primary"
            class="rounded-2xl border-0 bg-white text-slate-950 hover:bg-slate-100"
            :loading="analyzing"
            :disabled="analyzing"
            @click="generateAnalysis"
          >
            {{ analysis ? '重新生成分析' : '生成分析' }}
          </el-button>
        </div>
      </div>
    </header>

    <el-card class="rounded-[28px] border border-slate-200/70 !shadow-[0_24px_64px_-36px_rgba(15,23,42,0.28)]">
      <template #header>
        <div class="flex items-center justify-between">
          <div>
            <div class="text-xs uppercase tracking-[0.3em] text-slate-400">Markdown Output</div>
            <div class="mt-1 text-xl font-bold text-slate-900">分析摘要</div>
          </div>
          <el-tag v-if="analysis" type="success" round>{{ analysis.status }}</el-tag>
        </div>
      </template>

      <el-empty v-if="!analysis" description="还没有分析结果" />
      <article
        v-else
        class="analysis-markdown max-w-none text-sm leading-8 text-slate-700"
        v-html="renderedMarkdown"
      />
    </el-card>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useCrawlerStore } from '@/stores/crawler'

const route = useRoute()
const crawlerStore = useCrawlerStore()
const issue = computed(() => crawlerStore.currentIssue)
const analysis = computed(() => crawlerStore.currentAnalysis)
const analyzing = ref(false)
const renderedMarkdown = computed(() => renderMarkdownToHtml(analysis.value?.content_markdown || ''))

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
    ElMessage.error(error?.message || '分析生成失败，请重试')
  } finally {
    analyzing.value = false
  }
}

onMounted(async () => {
  await crawlerStore.fetchRawIssue(route.params.id)
  try {
    await crawlerStore.fetchAnalysis(route.params.id)
  } catch (error) {
    if (error?.response?.status === 404) {
      crawlerStore.currentAnalysis = null
      return
    }
    throw error
  }
})
</script>

<style scoped>
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
