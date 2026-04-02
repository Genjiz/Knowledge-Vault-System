<template>
  <div class="page-shell">
    <section class="page-hero">
      <div class="page-hero__body lg:grid-cols-[1.45fr_0.95fr]">
        <div>
          <div class="page-eyebrow">
            <span>Preservation</span>
            <span class="h-1 w-1 rounded-full bg-slate-400"></span>
            <span>Backup</span>
          </div>
          <h2 class="page-title">备份与恢复</h2>
          <p class="page-subtitle">
            导出当前文献数据库快照，或从既有备份恢复。恢复支持合并模式和覆盖模式，适合迁移或回滚。
          </p>
        </div>

        <div class="hero-meta-grid self-start">
          <div class="hero-meta-tile">
            <div class="hero-meta-label">Export</div>
            <div class="hero-meta-value">{{ exporting ? '进行中' : 'Ready' }}</div>
          </div>
          <div class="hero-meta-tile">
            <div class="hero-meta-label">Restore</div>
            <div class="hero-meta-value">{{ restoring ? '进行中' : 'Idle' }}</div>
          </div>
          <div class="hero-meta-tile">
            <div class="hero-meta-label">Mode</div>
            <div class="hero-meta-value">{{ restoreModeLabel }}</div>
          </div>
        </div>
      </div>
    </section>

    <section class="content-grid-2">
      <article class="surface-panel">
        <div class="surface-panel__header">
          <div>
            <h3 class="surface-panel__title">数据备份</h3>
            <p class="surface-panel__caption">导出所有正式文献数据为 JSON，不包含 PDF 文件本体。</p>
          </div>
        </div>
        <p class="text-sm leading-7 text-slate-600">
          适合做阶段快照、数据迁移或本地留档。文件会按日期自动命名。
        </p>
        <el-button type="primary" class="mt-5" :loading="exporting" @click="exportData">
          导出数据
        </el-button>
      </article>

      <article class="surface-panel">
        <div class="surface-panel__header">
          <div>
            <h3 class="surface-panel__title">数据恢复</h3>
            <p class="surface-panel__caption">从 JSON 备份恢复数据库内容，请先确认恢复模式。</p>
          </div>
        </div>

        <el-upload
          ref="restoreUpload"
          :auto-upload="false"
          :show-file-list="true"
          accept=".json"
          :on-change="handleRestoreFile"
          :limit="1"
        >
          <el-button>选择备份文件</el-button>
        </el-upload>

        <div class="mt-5">
          <el-radio-group v-model="restoreMode">
            <el-radio value="merge">合并模式</el-radio>
            <el-radio value="overwrite">覆盖模式</el-radio>
          </el-radio-group>
        </div>

        <el-button type="primary" class="mt-5" :loading="restoring" @click="restoreData">
          开始恢复
        </el-button>
      </article>
    </section>

    <section class="surface-panel">
      <div class="surface-panel__header">
        <div>
          <h3 class="surface-panel__title">存储位置说明</h3>
          <p class="surface-panel__caption">当前项目的核心数据与文件存放位置。</p>
        </div>
      </div>

      <el-descriptions :column="1" border>
        <el-descriptions-item label="数据库文件">backend/app.db</el-descriptions-item>
        <el-descriptions-item label="PDF 文件">backend/uploads/pdfs/</el-descriptions-item>
        <el-descriptions-item label="采集 JSON 产物">backend/artifacts/raw-json/</el-descriptions-item>
        <el-descriptions-item label="分析 Markdown 产物">backend/artifacts/analysis-md/</el-descriptions-item>
      </el-descriptions>
    </section>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const exporting = ref(false)
const restoring = ref(false)
const restoreFile = ref(null)
const restoreMode = ref('merge')

const restoreModeLabel = computed(() => (restoreMode.value === 'merge' ? 'Merge' : 'Overwrite'))

const exportData = async () => {
  exporting.value = true
  try {
    const response = await fetch('/api/backup/export')
    const data = await response.json()

    if (data.code !== 200) {
      throw new Error(data.message)
    }

    const blob = new Blob([JSON.stringify(data.data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `literature-backup-${new Date().toISOString().split('T')[0]}.json`
    a.click()
    URL.revokeObjectURL(url)

    ElMessage.success('数据导出成功')
  } catch (error) {
    ElMessage.error(`导出失败：${error.message}`)
  } finally {
    exporting.value = false
  }
}

const handleRestoreFile = (file) => {
  restoreFile.value = file.raw
}

const restoreData = async () => {
  if (!restoreFile.value) {
    ElMessage.warning('请先选择备份文件')
    return
  }

  try {
    await ElMessageBox.confirm(
      restoreMode.value === 'overwrite'
        ? '覆盖模式会清空现有数据，确定继续吗？'
        : '合并模式会保留现有数据并追加备份内容，确定继续吗？',
      '确认恢复',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
  } catch {
    return
  }

  restoring.value = true
  try {
    const content = await restoreFile.value.text()
    const data = JSON.parse(content)

    const response = await fetch('/api/backup/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ data, mode: restoreMode.value })
    })

    const result = await response.json()
    if (result.code !== 200) {
      throw new Error(result.message)
    }

    ElMessage.success(`数据恢复成功：导入 ${result.data.imported} 条文献`)
  } catch (error) {
    ElMessage.error(`恢复失败：${error.message}`)
  } finally {
    restoring.value = false
  }
}
</script>
