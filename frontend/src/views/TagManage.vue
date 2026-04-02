<template>
  <div class="page-shell">
    <section class="page-hero">
      <div class="page-hero__body lg:grid-cols-[1.45fr_0.95fr]">
        <div>
          <div class="page-eyebrow">
            <span>Vocabulary Layer</span>
            <span class="h-1 w-1 rounded-full bg-slate-400"></span>
            <span>Taxonomy</span>
          </div>
          <h2 class="page-title">标签管理</h2>
          <p class="page-subtitle">
            用颜色和命名规则维护你的主题词表。标签不是装饰，而是后续检索、筛选和统计的结构层。
          </p>
        </div>

        <div class="hero-meta-grid self-start">
          <div class="hero-meta-tile">
            <div class="hero-meta-label">Tag Count</div>
            <div class="hero-meta-value">{{ tags.length }}</div>
          </div>
          <div class="hero-meta-tile">
            <div class="hero-meta-label">In Use</div>
            <div class="hero-meta-value">{{ usedTagCount }}</div>
          </div>
          <div class="hero-meta-tile">
            <div class="hero-meta-label">Unused</div>
            <div class="hero-meta-value">{{ unusedTagCount }}</div>
          </div>
          <div class="hero-meta-tile">
            <div class="hero-meta-label">Coverage</div>
            <div class="hero-meta-value">{{ totalLinkedLiterature }}</div>
          </div>
        </div>
      </div>
    </section>

    <section class="surface-panel">
      <div class="surface-panel__header">
        <div>
          <h3 class="surface-panel__title">标签工作区</h3>
          <p class="surface-panel__caption">保持标签命名简洁、可复用，避免一个主题对应多个近义标签。</p>
        </div>
        <el-button type="primary" size="large" @click="showDialog()">
          添加标签
        </el-button>
      </div>

      <div class="insight-strip">
        <div class="insight-chip">
          <span>已关联文献的标签 <strong>{{ usedTagCount }}</strong> 个</span>
        </div>
        <div class="insight-chip">
          <span>待清理标签 <strong>{{ unusedTagCount }}</strong> 个</span>
        </div>
      </div>
    </section>

    <section class="surface-panel table-shell">
      <div class="surface-panel__header">
        <div>
          <h3 class="surface-panel__title">标签清单</h3>
          <p class="surface-panel__caption">查看颜色、关联数量并直接编辑或删除。</p>
        </div>
      </div>

      <el-table :data="tags" v-loading="loading" style="width: 100%">
        <el-table-column prop="tag.name" label="标签名称" min-width="220">
          <template #default="{ row }">
            <el-tag
              :color="row.tag.color"
              effect="dark"
              round
              style="border: 0; color: #fff;"
            >
              {{ row.tag.name }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="tag.color" label="颜色" min-width="180">
          <template #default="{ row }">
            <div class="flex items-center gap-3">
              <span class="h-6 w-6 rounded-full border border-slate-200" :style="{ backgroundColor: row.tag.color }"></span>
              <span class="font-mono text-sm text-slate-500">{{ row.tag.color }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="literature_count" label="文献数量" width="120" align="center">
          <template #default="{ row }">
            <span class="rounded-full bg-slate-100 px-3 py-1 text-sm font-semibold text-slate-700">
              {{ row.literature_count }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="180" align="right">
          <template #default="{ row }">
            <div class="flex items-center justify-end gap-2">
              <el-button plain @click="showDialog(row.tag)">编辑</el-button>
              <el-button plain type="danger" @click="handleDelete(row.tag)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog v-model="dialogVisible" :title="editingTag ? '编辑标签' : '添加标签'" width="420px">
      <el-form :model="tagForm" label-position="top">
        <el-form-item label="名称">
          <el-input v-model="tagForm.name" placeholder="请输入标签名称" />
        </el-form-item>
        <el-form-item label="颜色">
          <div class="flex items-center gap-4">
            <el-color-picker v-model="tagForm.color" />
            <span class="font-mono text-sm text-slate-500">{{ tagForm.color }}</span>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveTag">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useTagStore } from '@/stores/tag'
import { ElMessage, ElMessageBox } from 'element-plus'

const tagStore = useTagStore()
const tags = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const editingTag = ref(null)

const tagForm = reactive({
  name: '',
  color: '#0f172a'
})

const usedTagCount = computed(() => tags.value.filter(item => item.literature_count > 0).length)
const unusedTagCount = computed(() => tags.value.filter(item => item.literature_count === 0).length)
const totalLinkedLiterature = computed(() => tags.value.reduce((sum, item) => sum + item.literature_count, 0))

const fetchTags = async () => {
  loading.value = true
  try {
    tags.value = await tagStore.fetchTags()
  } finally {
    loading.value = false
  }
}

const showDialog = (tag = null) => {
  editingTag.value = tag
  if (tag) {
    tagForm.name = tag.name
    tagForm.color = tag.color
  } else {
    tagForm.name = ''
    tagForm.color = '#0f172a'
  }
  dialogVisible.value = true
}

const saveTag = async () => {
  if (!tagForm.name.trim()) {
    ElMessage.warning('请输入标签名称')
    return
  }

  try {
    if (editingTag.value) {
      await tagStore.updateTag(editingTag.value.id, tagForm)
      ElMessage.success('标签已更新')
    } else {
      await tagStore.createTag(tagForm)
      ElMessage.success('标签已创建')
    }
    dialogVisible.value = false
    fetchTags()
  } catch {
    ElMessage.error('操作失败')
  }
}

const handleDelete = async (tag) => {
  try {
    await ElMessageBox.confirm('确定要删除这个标签吗？', '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await tagStore.deleteTag(tag.id)
    ElMessage.success('标签已删除')
    fetchTags()
  } catch {}
}

onMounted(() => {
  fetchTags()
})
</script>
