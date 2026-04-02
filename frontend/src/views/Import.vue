<template>
  <div class="page-shell">
    <section class="page-hero">
      <div class="page-hero__body lg:grid-cols-[1.45fr_0.95fr]">
        <div>
          <div class="page-eyebrow">
            <span>Intake Pipeline</span>
            <span class="h-1 w-1 rounded-full bg-slate-400"></span>
            <span>Import</span>
          </div>
          <h2 class="page-title">导入文献</h2>
          <p class="page-subtitle">
            支持手动录入，也支持从 EndNote / NoteExpress 导出的文本格式批量导入。导入结果会即时显示成功与失败明细。
          </p>
        </div>

        <div class="hero-meta-grid self-start">
          <div class="hero-meta-tile">
            <div class="hero-meta-label">Current Mode</div>
            <div class="hero-meta-value">{{ activeTabLabel }}</div>
          </div>
          <div class="hero-meta-tile">
            <div class="hero-meta-label">Imported</div>
            <div class="hero-meta-value">{{ importResult?.success || 0 }}</div>
          </div>
          <div class="hero-meta-tile">
            <div class="hero-meta-label">Failed</div>
            <div class="hero-meta-value">{{ importResult?.failed || 0 }}</div>
          </div>
        </div>
      </div>
    </section>

    <section class="surface-panel">
      <div class="surface-panel__header">
        <div>
          <h3 class="surface-panel__title">导入入口</h3>
          <p class="surface-panel__caption">选择一种输入方式，把外部来源的文献安全导入正式文献库。</p>
        </div>
      </div>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="手动录入" name="manual">
          <div class="rounded-3xl border border-slate-200/80 bg-slate-50/60 p-6">
            <p class="text-sm leading-7 text-slate-600">
              适合录入少量文献或需要逐条补充字段的场景。点击下面按钮进入正式新增页面。
            </p>
            <el-button type="primary" class="mt-4" @click="$router.push('/literatures/new')">
              前往添加文献
            </el-button>
          </div>
        </el-tab-pane>

        <el-tab-pane label="EndNote 格式导入" name="endnote">
          <div class="rounded-3xl border border-slate-200/80 bg-slate-50/60 p-6">
            <p class="text-sm leading-7 text-slate-600">
              支持从知网、万方等数据库导出的 EndNote 文本格式文件，请选择 `.txt` 或 `.enw`。
            </p>
            <div class="mt-5 flex flex-wrap items-center gap-3">
              <el-upload
                ref="endnoteUpload"
                :auto-upload="false"
                :show-file-list="true"
                accept=".txt,.enw"
                :on-change="handleEndnoteFile"
                :limit="1"
              >
                <el-button>选择文件</el-button>
              </el-upload>
              <el-button type="primary" :loading="importing" @click="importEndnote">开始导入</el-button>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="NoteExpress 格式导入" name="noteexpress">
          <div class="rounded-3xl border border-slate-200/80 bg-slate-50/60 p-6">
            <p class="text-sm leading-7 text-slate-600">
              支持从知网导出的 NoteExpress 文本格式文件，请选择 `.txt` 或 `.nel`。
            </p>
            <div class="mt-5 flex flex-wrap items-center gap-3">
              <el-upload
                ref="noteexpressUpload"
                :auto-upload="false"
                :show-file-list="true"
                accept=".txt,.nel"
                :on-change="handleNoteexpressFile"
                :limit="1"
              >
                <el-button>选择文件</el-button>
              </el-upload>
              <el-button type="primary" :loading="importing" @click="importNoteexpress">开始导入</el-button>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </section>

    <section v-if="importResult" class="surface-panel table-shell">
      <div class="surface-panel__header">
        <div>
          <h3 class="surface-panel__title">导入结果</h3>
          <p class="surface-panel__caption">逐条检查导入状态，确认失败原因后可以继续修正原文件重试。</p>
        </div>
      </div>

      <el-alert
        :title="`成功导入 ${importResult.success} 条，失败 ${importResult.failed} 条`"
        :type="importResult.failed > 0 ? 'warning' : 'success'"
        show-icon
        class="mb-5"
      />

      <el-table :data="importResult.items" style="width: 100%">
        <el-table-column prop="title" label="标题" min-width="320" />
        <el-table-column prop="authors" label="作者" min-width="220" />
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.success ? 'success' : 'danger'" round>
              {{ row.success ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="说明" min-width="220" />
      </el-table>
    </section>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useLiteratureStore } from '@/stores/literature'
import { ElMessage } from 'element-plus'

const literatureStore = useLiteratureStore()
const activeTab = ref('manual')
const importing = ref(false)
const importResult = ref(null)
const endnoteFile = ref(null)
const noteexpressFile = ref(null)

const activeTabLabel = computed(() => {
  const labels = {
    manual: 'Manual',
    endnote: 'EndNote',
    noteexpress: 'NoteExpress'
  }
  return labels[activeTab.value]
})

const handleEndnoteFile = (file) => {
  endnoteFile.value = file.raw
}

const handleNoteexpressFile = (file) => {
  noteexpressFile.value = file.raw
}

const parseEndnote = (content) => {
  const records = []
  const recordPattern = /%0 (.+?)(?=%0 |$)/gs
  const matches = content.match(recordPattern) || []

  for (const match of matches) {
    const record = {
      title: '',
      authors: '',
      journal: '',
      year: null,
      volume: '',
      issue: '',
      pages: '',
      doi: '',
      abstract: '',
      keywords: '',
      language: 'zh'
    }

    const lines = match.split('\n')
    for (const line of lines) {
      if (line.startsWith('%T')) record.title = line.substring(2).trim()
      else if (line.startsWith('%A')) record.authors += (record.authors ? ', ' : '') + line.substring(2).trim()
      else if (line.startsWith('%J')) record.journal = line.substring(2).trim()
      else if (line.startsWith('%D')) record.year = parseInt(line.substring(2).trim(), 10)
      else if (line.startsWith('%V')) record.volume = line.substring(2).trim()
      else if (line.startsWith('%N')) record.issue = line.substring(2).trim()
      else if (line.startsWith('%P')) record.pages = line.substring(2).trim()
      else if (line.startsWith('%R')) record.doi = line.substring(2).trim()
      else if (line.startsWith('%X')) record.abstract += line.substring(2).trim()
      else if (line.startsWith('%K')) record.keywords = line.substring(2).trim()
    }

    if (record.title) records.push(record)
  }

  return records
}

const importRecords = async (records) => {
  const result = {
    success: 0,
    failed: 0,
    items: []
  }

  for (const record of records) {
    try {
      await literatureStore.createLiterature(record)
      result.success++
      result.items.push({ ...record, success: true, message: '导入成功' })
    } catch (error) {
      result.failed++
      result.items.push({
        ...record,
        success: false,
        message: error.message || '导入失败'
      })
    }
  }

  importResult.value = result
  ElMessage.success(`导入完成：成功 ${result.success} 条`)
}

const importEndnote = async () => {
  if (!endnoteFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }

  importing.value = true
  importResult.value = null
  try {
    const content = await endnoteFile.value.text()
    await importRecords(parseEndnote(content))
  } catch {
    ElMessage.error('文件解析失败')
  } finally {
    importing.value = false
  }
}

const importNoteexpress = async () => {
  if (!noteexpressFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }

  importing.value = true
  importResult.value = null
  try {
    const content = await noteexpressFile.value.text()
    await importRecords(parseEndnote(content))
  } catch {
    ElMessage.error('文件解析失败')
  } finally {
    importing.value = false
  }
}
</script>
